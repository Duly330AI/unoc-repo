from __future__ import annotations

import logging

from fastapi import BackgroundTasks

from backend import events
from backend.models import Device, Interface, Link
from backend.services import recompute_coalescer as coalescer
from backend.services.optical_service import recompute_optical_paths_for_affected_onts
from backend.services.pathfinding import PATHFINDING_STORE
from backend.services.status_service import evaluate_device_status

log = logging.getLogger("unoc.bg")


def schedule(background: BackgroundTasks, func, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Thin wrapper to schedule a callable on FastAPI BackgroundTasks.

    Keeps a single import site for background execution to simplify testing/mocking.
    """
    background.add_task(func, *args, **kwargs)


def _recompute_after_link_create(link_id: str) -> None:
    """Heavy recompute flow to run after link creation, off the request path."""
    try:
        # Bump version here defensively if not already done, then recompute status/optical
        tv = PATHFINDING_STORE.bump_version()
        from backend.db import get_session, init_db

        init_db()
        with get_session() as s:
            link = s.get(Link, link_id)
            if not link:
                return
            a_dev: Device | None = None
            b_dev: Device | None = None
            a_if = s.get(Interface, link.a_interface_id) if link.a_interface_id else None
            b_if = s.get(Interface, link.b_interface_id) if link.b_interface_id else None
            if a_if:
                a_dev = s.get(Device, a_if.device_id)
            if b_if:
                b_dev = s.get(Device, b_if.device_id)

            baseline = {}
            for dev in (a_dev, b_dev):
                if dev:
                    baseline[dev.id] = evaluate_device_status(dev)

            # No 'link.created' emission here; emitted on request path to avoid duplicates.

            # Schedule consolidated status recompute instead of direct call
            try:
                coalescer.schedule(scope="links", key=link.id)
            except Exception:
                log.exception("Failed to schedule status recompute for link %s", link_id)

            try:
                recompute_optical_paths_for_affected_onts(link_ids={link.id})
                events.publish(
                    events.Event(
                        type="device.optical.updated",
                        payload={"affected_link_ids": [link.id], "reason": "link_created"},
                        topo_version=tv,
                    )
                )
            except Exception:
                log.exception("Optical recompute failed in background for link %s", link_id)
    except Exception:
        log.exception("Background task _recompute_after_link_create crashed for %s", link_id)


def _recompute_after_device_provision(device_id: str) -> None:
    """Heavy recompute flow to run after device provisioning, off the request path."""
    try:
        tv = PATHFINDING_STORE.bump_version()
        from backend.db import get_session, init_db

        init_db()
        with get_session() as s:
            d = s.get(Device, device_id)
            if not d:
                return
            # Status changes and provisioned event already emitted on request path.

            try:
                recompute_optical_paths_for_affected_onts(device_ids={device_id})
                events.publish(
                    events.Event(
                        type="device.optical.updated",
                        payload={"id": device_id, "reason": "provision"},
                        topo_version=tv,
                    )
                )
            except Exception:
                log.exception("Optical recompute failed in background for device %s", device_id)
    except Exception:
        log.exception("Background task _recompute_after_device_provision crashed for %s", device_id)


__all__ = [
    "schedule",
    "_recompute_after_link_create",
    "_recompute_after_device_provision",
]
