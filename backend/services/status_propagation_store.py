"""In-memory store for status propagation snapshot (always-on).

Holds the latest set of device IDs considered reachable/UP via propagation.
Propagation is now strict-by-default and always enabled; callers update the
snapshot on each recompute cycle.
"""

from __future__ import annotations

from collections.abc import Iterable

_reachable_up: set[str] | None = None
_seen_devices: set[str] | None = None


def set_snapshot(
    up_device_ids: Iterable[str], seen_device_ids: Iterable[str] | None = None
) -> None:
    global _reachable_up, _seen_devices
    _reachable_up = set(up_device_ids)
    _seen_devices = set(seen_device_ids) if seen_device_ids is not None else set(_reachable_up)


def is_up(device_id: str) -> bool | None:
    # Returns True if device_id is marked reachable, False if present but not reachable,
    # and None if no snapshot set (treat as unknown)
    # We treat unknown as None to allow callers to fallback.
    if _reachable_up is None:
        return None
    # If device wasn't part of the last recompute snapshot, treat as unknown
    if _seen_devices is not None and device_id not in _seen_devices:
        return None
    return device_id in _reachable_up


def clear() -> None:
    global _reachable_up, _seen_devices
    _reachable_up = None
    _seen_devices = None


__all__ = ["set_snapshot", "is_up", "clear"]
