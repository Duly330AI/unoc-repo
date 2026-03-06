"""Helper for devices MAC table endpoint.

Read-only; no side-effects. Returns minimal entries with fields:
- mac_address, interface_id, bridge_domain_id, type
"""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import BridgeDomain, Device, MacAddressEntry


def get_device_mac_table_impl(s: Session, device_id: str) -> list[dict]:
    """Return MAC table entries for a device or raise LookupError if missing."""
    d = s.get(Device, device_id)
    if not d:
        raise LookupError("Not found")
    bds = s.exec(select(BridgeDomain).where(BridgeDomain.device_id == d.id)).all()
    entries: list[MacAddressEntry] = []
    for bd in bds:
        entries.extend(
            s.exec(select(MacAddressEntry).where(MacAddressEntry.bridge_domain_id == bd.id)).all()
        )
    return [
        {
            "mac_address": e.mac_address,
            "interface_id": e.interface_id,
            "bridge_domain_id": e.bridge_domain_id,
            "type": e.type,
        }
        for e in entries
    ]
