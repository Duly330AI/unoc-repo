"""Phase utilities for Traffic V2 engine.

Small, focused helpers extracted from v2_engine to keep it under the 400-line
budget without changing public behavior or timing.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

import backend.events as events


def schedule_status_recompute_if_needed() -> None:
    """Schedule reachability recompute in the background unless disabled.

    Mirrors the original inline logic in v2_engine.run_tick: skip under pytest
    or when UNOC_DISABLE_ASYNC_STATUS is set. Failures are swallowed.
    """
    if not os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get(
        "UNOC_DISABLE_ASYNC_STATUS"
    ):
        try:
            from backend.services import recompute_coalescer as _coalescer

            _coalescer.schedule(scope="status", key=None)
        except Exception:
            # Never allow scheduling issues to break a tick
            pass


def emit_zero_metrics(
    engine, device_changes: Iterable[dict], link_changes: Iterable[dict], tick: int
):
    """Emit zeroed metrics for devices/links that went inactive since last tick.

    - Publishes deviceMetricsUpdated/linkMetricsUpdated events with zero bps.
    - Updates engine._prev_active_{devices,links} and pre-fills engine._last_* maps
      with zeros so snapshots remain coherent.

    Returns: (zero_events, link_zero_events)
    """
    # Devices
    current_active = {item["id"] for item in device_changes}
    zero_events: list[dict] = []
    for did in sorted(engine._prev_active_devices - current_active):
        zero_events.append(
            {
                "id": did,
                "bps": 0.0,
                "utilization": 0.0,
                "upstream_bps": 0.0,
                "downstream_bps": 0.0,
            }
        )
        engine._last_devices[did] = {
            "bps": 0.0,
            "utilization": 0.0,
            "version": 0,
            "upstream_bps": 0.0,
            "downstream_bps": 0.0,
        }
    if zero_events:
        events.publish(
            events.Event(
                type="deviceMetricsUpdated", payload={"devices": zero_events, "tick": tick}
            )
        )
    engine._prev_active_devices = set(current_active)

    # Links
    current_active_links = {item["id"] for item in link_changes}
    link_zero_events: list[dict] = []
    for lid in sorted(engine._prev_active_links - current_active_links):
        link_zero_events.append({"id": lid, "bps": 0.0, "utilization": 0.0})
        engine._last_links[lid] = {"bps": 0.0, "utilization": 0.0, "version": 0}
    if link_zero_events:
        events.publish(
            events.Event(
                type="linkMetricsUpdated", payload={"links": link_zero_events, "tick": tick}
            )
        )
    engine._prev_active_links = set(current_active_links)

    return zero_events, link_zero_events
