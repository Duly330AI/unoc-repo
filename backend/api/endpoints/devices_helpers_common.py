"""Common helpers for devices endpoints (query layer).

Keep logic here deterministic and side-effect free; no events or writes.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlmodel import Session, select

from backend.models import AdminStatus, Interface


def resolve_vrf_name_map(s: Session, devices: Iterable) -> dict[int, str]:
    """Build a map of VRF id -> name for provided devices, avoiding N+1 queries.

    Uses simple get() calls per unique id to keep typing simple and stable.
    """
    vrf_ids = [int(d.vrf_id) for d in devices if getattr(d, "vrf_id", None) is not None]
    if not vrf_ids:
        return {}
    from backend.models import VRF  # local import to avoid circulars at import time

    out: dict[int, str] = {}
    for vid in set(vrf_ids):
        v = s.get(VRF, vid)
        if v and v.id is not None:
            out[int(v.id)] = v.name
    return out


def serialize_interfaces_for_device(s: Session, device_id: str) -> list[dict]:
    """Return interface payloads as used by list-devices include_interfaces flag."""
    ifaces = s.exec(select(Interface).where(Interface.device_id == device_id)).all()
    items: list[dict] = []
    for i in ifaces:
        pr = getattr(i, "port_role", None)
        admin_val = i.admin_status
        admin_status = (
            admin_val.value if isinstance(admin_val, AdminStatus) else (admin_val or "up")
        )
        items.append(
            {
                "id": i.id,
                "name": i.name,
                # interface logical status removed; use admin_status only
                "mac_address": getattr(i, "mac_address", None),
                "role": getattr(i, "role", None),
                "port_role": (pr.value if pr is not None else None),
                # serialize enum to raw value ("up"/"down") for frontend simplicity
                "admin_status": admin_status,
                # deprecated ip_address removed; use /interfaces/{id}/addresses API
            }
        )
    return items
