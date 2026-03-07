"""Re-computation coalescer (debounce scheduler).

Consolidates many recompute triggers that happen within a short window into a single
execution to avoid N recomputes per burst.

Environment:
- UNOC_RECOMPUTE_DEBOUNCE_MS: debounce window in milliseconds (default 75). Preferred.
- UNOC_RECOMPUTE_COALESCE_MS: legacy name for debounce window (used if the new var is unset).
- UNOC_RECOMPUTE_ENABLED: set to '0' to disable any recompute execution (still counts metrics).

API:
- schedule(scope: str = "global", key: str | None = None) -> None
    Request a recompute; execution is debounced.
- flush_now() -> None
    Execute pending recompute immediately (resets timer).
- start() / stop(): lifecycle hooks (idempotent).

Thread-safety:
- Uses a threading.Timer and Lock; safe to call from request threads.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field

from sqlmodel import Session

from backend.db import get_session, init_db
from backend.services.pathfinding import PATHFINDING_STORE
from backend.services.status_recompute import recompute_devices_status
from backend.services.status_service import recompute_dirty as _recompute_dirty

log = logging.getLogger("unoc.recompute")


def _env_ms(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


@dataclass
class _State:
    enabled: bool = True
    debounce_ms: int = 150
    timer: threading.Timer | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    pending_scopes: set[str] = field(default_factory=set)
    pending_keys: set[str] = field(default_factory=set)
    executing: bool = False
    metrics_scheduled: int = 0
    metrics_coalesced_runs: int = 0
    metrics_executed: int = 0


_STATE = _State()


def start() -> None:
    """Initialize state from environment; idempotent."""
    _STATE.enabled = os.getenv("UNOC_RECOMPUTE_ENABLED", "1") not in {"0", "false", "False"}
    # Prefer new var; fall back to legacy if not provided; default to 75ms
    new_ms = os.getenv("UNOC_RECOMPUTE_DEBOUNCE_MS")
    if new_ms is not None and new_ms != "":
        _STATE.debounce_ms = _env_ms("UNOC_RECOMPUTE_DEBOUNCE_MS", 75)
    else:
        _STATE.debounce_ms = _env_ms("UNOC_RECOMPUTE_COALESCE_MS", 75)
    log.info(
        "Recompute coalescer started enabled=%s window_ms=%d",
        _STATE.enabled,
        _STATE.debounce_ms,
    )


def stop() -> None:
    with _STATE.lock:
        if _STATE.timer:
            try:
                _STATE.timer.cancel()
            except Exception:
                pass
            _STATE.timer = None
        _STATE.pending_scopes.clear()
        _STATE.pending_keys.clear()


def _execute_now() -> None:
    """Run a consolidated recompute covering pending keys/scopes."""
    # Reset timer reference under lock
    with _STATE.lock:
        _STATE.timer = None
        scopes = set(_STATE.pending_scopes)
        keys = set(_STATE.pending_keys)
        _STATE.pending_scopes.clear()
        _STATE.pending_keys.clear()
    if not _STATE.enabled:
        log.debug("Coalescer disabled; skipping execution (scopes=%s keys=%s)", scopes, keys)
        return
    t0 = time.perf_counter()
    try:
        with _STATE.lock:
            _STATE.executing = True
        init_db()
        with get_session() as s:
            # Use current topology version so emitted device.status.changed events are versioned
            topo_v = None
            try:
                topo_v = PATHFINDING_STORE.version()
            except Exception:  # pragma: no cover
                topo_v = None
            _run_consolidated_recompute(s, topo_version=topo_v, keys=keys, scopes=scopes)
        _STATE.metrics_executed += 1
        dt = (time.perf_counter() - t0) * 1000.0
        log.info(
            "recompute.coalesced executed=1 scopes=%d keys=%d dur_ms=%.2f",
            len(scopes),
            len(keys),
            dt,
        )
    except Exception:
        log.exception("Coalesced recompute failed")
    finally:
        with _STATE.lock:
            _STATE.executing = False


def _run_consolidated_recompute(
    session: Session,
    *,
    topo_version: int | None = None,
    keys: set[str] | None = None,
    scopes: set[str] | None = None,
) -> None:
    """Perform a consolidated recompute using incremental seeds when possible.

    Behavior:
    - If we can resolve any of the aggregated ``keys`` to known devices/links,
      run incremental recompute via ``recompute_dirty`` to update only the
      affected component deterministically.
    - If no valid seeds are present (or an error occurs), fall back to a full
      recompute to preserve strict semantics.
    """
    # Try to resolve pending keys to device/link seeds.
    dirty_devices: list[str] = []
    dirty_links: list[str] = []
    try:
        if keys:
            # Resolve using lightweight existence checks; duplicates removed downstream
            from backend.models import Device as _D
            from backend.models import Link as _L

            for k in sorted(keys):
                if session.get(_D, k) is not None:
                    dirty_devices.append(k)
                elif session.get(_L, k) is not None:
                    dirty_links.append(k)
    except Exception:
        # Resolution failure – ignore and take full recompute path below
        dirty_devices = []
        dirty_links = []

    # Run incremental when we have any seeds; otherwise full recompute
    if dirty_devices or dirty_links:
        try:
            from types import SimpleNamespace as _NS

            _cfg = _NS(enable_incremental=True, topo_version=topo_version, baseline_status=None)

            _recompute_dirty(
                session,
                dirty={"devices": dirty_devices, "links": dirty_links},
                cfg=_cfg,
            )
            return
        except Exception:
            # Fall back to full recompute on any error to keep system consistent
            pass

    # Pathfinding store version bump happens at the specific mutation sites; we only recompute status.
    recompute_devices_status(session, topo_version=topo_version)


def schedule(scope: str = "global", key: str | None = None) -> None:
    """Request a recompute; debounced into one execution per window.

    Args:
        scope: Logical category (e.g., 'links', 'devices'); for metrics only.
        key: Optional identifier to record (e.g., link_id or device_id); metrics only.
    """
    _STATE.metrics_scheduled += 1
    with _STATE.lock:
        if scope:
            _STATE.pending_scopes.add(scope)
        if key:
            _STATE.pending_keys.add(key)
        if _STATE.timer is None:
            # First trigger in the window – schedule execution
            delay = max(_STATE.debounce_ms, 0) / 1000.0
            _STATE.timer = threading.Timer(delay, _execute_now)
            try:
                _STATE.timer.daemon = True
                _STATE.timer.start()
            except Exception:
                # Fallback: run inline if timer cannot start (rare)
                _STATE.timer = None
                _execute_now()
        else:
            # Already scheduled within debounce window → coalesced
            _STATE.metrics_coalesced_runs += 1


def flush_now() -> None:
    """Force immediate execution of any pending recompute."""
    with _STATE.lock:
        if _STATE.timer is None:
            # Nothing pending
            return
        try:
            _STATE.timer.cancel()
        except Exception:
            pass
        _STATE.timer = None
    _execute_now()


def get_metrics() -> dict[str, int]:
    return {
        "scheduled": _STATE.metrics_scheduled,
        "coalesced": _STATE.metrics_coalesced_runs,
        "executed": _STATE.metrics_executed,
    }


def is_idle() -> bool:
    """Return True when there is no pending timer, no queued work, and not executing."""
    with _STATE.lock:
        return (
            (_STATE.timer is None)
            and (not _STATE.pending_scopes)
            and (not _STATE.pending_keys)
            and (not _STATE.executing)
        )


__all__ = [
    "start",
    "stop",
    "schedule",
    "flush_now",
    "get_metrics",
    "is_idle",
]
