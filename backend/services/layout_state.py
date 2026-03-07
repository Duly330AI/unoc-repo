"""Layout position persistence and API helpers.

Contains in-memory versioned store used by tests and WS fanout, plus
DB-backed helpers to persist and load positions. The API endpoints use
the DB helpers while keeping the in-memory snapshot in sync.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from threading import RLock

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import LayoutPositionRecord


@dataclass
class LayoutPosition:
    id: str
    x: float
    y: float
    userPinned: bool | None = None
    systemPinned: bool | None = None


class LayoutStateStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._version: int = 0
        self._positions: dict[str, LayoutPosition] = {}

    def patch(self, positions: list[LayoutPosition]) -> int:
        with self._lock:
            for p in positions:
                existing = self._positions.get(p.id)
                if existing:
                    # Merge (only overwrite provided fields)
                    existing.x = p.x
                    existing.y = p.y
                    if p.userPinned is not None:
                        existing.userPinned = p.userPinned
                    if p.systemPinned is not None:
                        existing.systemPinned = p.systemPinned
                else:
                    self._positions[p.id] = p
            self._version += 1
            return self._version

    def snapshot(self) -> tuple[int, list[LayoutPosition]]:
        with self._lock:
            return self._version, list(self._positions.values())


LAYOUT_STORE = LayoutStateStore()


# ---- DB helpers ----


def db_snapshot() -> tuple[int, list[LayoutPosition]]:
    """Load positions from DB and return a pseudo-version and items.

    Version is derived from the in-memory store to keep compatibility with
    existing clients/tests; positions are read from DB.
    """
    init_db()
    with get_session() as s:
        rows = s.exec(select(LayoutPositionRecord)).all()
    items: list[LayoutPosition] = []
    for r in rows:
        items.append(
            LayoutPosition(
                id=r.id,
                x=r.x,
                y=r.y,
                userPinned=r.user_pinned,
                systemPinned=r.system_pinned,
            )
        )
    # version reflects in-memory counter
    v, _ = LAYOUT_STORE.snapshot()
    return v, items


def db_patch(positions: Iterable[LayoutPosition]) -> int:
    """Upsert positions into DB and sync in-memory store; return new version."""
    init_db()
    with get_session() as s:
        for p in positions:
            rec = s.get(LayoutPositionRecord, p.id)
            if rec is None:
                rec = LayoutPositionRecord(
                    id=p.id,
                    x=p.x,
                    y=p.y,
                    user_pinned=p.userPinned,
                    system_pinned=p.systemPinned,
                )
                s.add(rec)
            else:
                rec.x = p.x
                rec.y = p.y
                if p.userPinned is not None:
                    rec.user_pinned = p.userPinned
                if p.systemPinned is not None:
                    rec.system_pinned = p.systemPinned
            s.add(rec)
        s.commit()
    # Mirror into in-memory store and bump version once
    return LAYOUT_STORE.patch(list(positions))
