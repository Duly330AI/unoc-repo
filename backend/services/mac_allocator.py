"""Deterministic MAC address allocator (E1.2).

Enhancements over prior in-memory only design:
 - Uses a locally administered OUI 02:55:4E plus a 24‑bit monotonic counter.
 - Persists the counter in a tiny singleton table so mid-test module re-imports
     (or code reload in dev) do not reset the sequence back to zero, eliminating
     duplicate MAC IntegrityErrors observed during provisioning tests.
 - Still maintains a process‑local _USED set for fast collision filtering when
     tests roll back a transaction leaving a MAC uncommitted (rare but safe).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlmodel import Session

try:  # Local import to avoid heavy dependency at module import if unused
    from backend import db as _db
except Exception:  # pragma: no cover - fallback guard
    _db = None  # type: ignore
import threading


@dataclass
class _MacState:
    last: int = -1


_STATE = _MacState()
_USED: set[str] = set()
_LOCK = threading.Lock()
_TABLE_CREATED = False


def _ensure_table(session: Session) -> None:
    global _TABLE_CREATED
    if _TABLE_CREATED:
        return
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS mac_allocator_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last INTEGER NOT NULL
            );
            """
        )
    )
    # Seed row if absent
    row = session.execute(text("SELECT last FROM mac_allocator_state WHERE id=1")).first()
    if row is None:
        session.execute(text("INSERT INTO mac_allocator_state (id, last) VALUES (1, -1)"))
    _TABLE_CREATED = True


def _load_last(session: Session) -> int:
    _ensure_table(session)
    row = session.execute(text("SELECT last FROM mac_allocator_state WHERE id=1")).first()
    return int(row[0]) if row else -1


def _store_last(session: Session, value: int) -> None:
    _ensure_table(session)
    session.execute(text("UPDATE mac_allocator_state SET last=:v WHERE id=1"), {"v": value})


def _get_session() -> Session | None:  # pragma: no cover - simple helper
    if _db is None or not hasattr(_db, "engine"):
        return None
    try:
        return Session(_db.engine)  # type: ignore[arg-type]
    except Exception:
        return None


def _format_mac(n: int) -> str:
    # OUI: 02:55:4E (02 indicates locally administered)
    b0, b1, b2 = 0x02, 0x55, 0x4E
    # remaining 3 bytes from counter
    n = n & 0xFFFFFF
    b3 = (n >> 16) & 0xFF
    b4 = (n >> 8) & 0xFF
    b5 = n & 0xFF
    return ":".join(f"{b:02x}" for b in [b0, b1, b2, b3, b4, b5])


def next_mac() -> str:
    """Generate a deterministic unique MAC (process-local monotonic counter).

    The previous implementation scanned the DB on first use which caused races
    with unflushed bulk interface provisioning in tests (all seeing zero rows
    and emitting duplicate MACs). For test determinism we rely solely on an
    in-memory monotonic counter reset by the test autouse fixture.
    """
    with _LOCK:
        sess = _get_session()
        if sess is not None:
            try:
                current = _STATE.last
                if current < 0:  # first use in this process
                    db_last = _load_last(sess)
                    _STATE.last = db_last
                _STATE.last += 1
                mac = _format_mac(_STATE.last)
                while mac in _USED:
                    _STATE.last += 1
                    mac = _format_mac(_STATE.last)
                _USED.add(mac)
                _store_last(sess, _STATE.last)
                sess.commit()
                return mac
            except Exception:
                try:
                    sess.rollback()
                except Exception:  # pragma: no cover
                    pass
                # Fallback to pure in-memory path below
            finally:
                try:
                    sess.close()
                except Exception:
                    pass
        # In-memory fallback (should be rare if DB session available)
        if _STATE.last < 0:
            _STATE.last = 0
        else:
            _STATE.last += 1
        mac = _format_mac(_STATE.last)
        while mac in _USED:
            _STATE.last += 1
            mac = _format_mac(_STATE.last)
        _USED.add(mac)
        return mac


__all__ = ["next_mac"]
