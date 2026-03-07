from __future__ import annotations

from typing import Any

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import BridgeDomain, Interface, MacAddressEntry


class Frame(dict):
    """Simple frame container: expects at least source_mac and destination_mac keys."""

    required_keys = {"source_mac", "destination_mac"}

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        missing = self.required_keys - set(self.keys())
        if missing:
            raise ValueError(f"Missing frame fields: {', '.join(sorted(missing))}")


BROADCAST_MACS = {"ff:ff:ff:ff:ff:ff", "FF:FF:FF:FF:FF:FF"}


def _get_device_default_bd_id(device_id: str) -> int | None:
    with get_session() as s:
        bd = s.exec(
            select(BridgeDomain).where(
                (BridgeDomain.device_id == device_id) & (BridgeDomain.name == "default")
            )
        ).first()
        return bd.id if bd else None


def _interfaces_in_bd(bd_id: int) -> list[Interface]:
    with get_session() as s:
        res = s.exec(select(Interface).where(Interface.bridge_domain_id == bd_id)).all()
        return list(res)


def process_frame(device_id: str, ingress_interface_id: str, frame: dict | Frame) -> dict:
    """Process a simulated Ethernet frame for a switch.

    Returns one of:
      - { action: "forward", egress_interface_id: str }
      - { action: "flood", egress_interface_ids: list[str] }

    Side effect: learns source_mac -> ingress_interface_id mapping in device's bridge domain.
    """
    init_db()
    if not isinstance(frame, Frame):
        frame = Frame(frame)  # type: ignore[arg-type]

    src = str(frame["source_mac"]).lower()
    dst = str(frame["destination_mac"]).lower()

    bd_id = _get_device_default_bd_id(device_id)
    if bd_id is None:
        # No BD, nothing to do
        return {"action": "drop", "reason": "no_bridge_domain"}

    with get_session() as s:
        # 1) Learn source MAC on ingress interface within this BD
        existing = s.exec(
            select(MacAddressEntry).where(
                (MacAddressEntry.bridge_domain_id == bd_id) & (MacAddressEntry.mac_address == src)
            )
        ).first()
        if existing:
            if existing.interface_id != ingress_interface_id:
                existing.interface_id = ingress_interface_id
                s.add(existing)
                s.commit()
        else:
            s.add(
                MacAddressEntry(
                    mac_address=src, interface_id=ingress_interface_id, bridge_domain_id=bd_id
                )
            )
            s.commit()

        # 2) Forwarding decision
        # Broadcast or unknown destination → flood
        if dst in {m.lower() for m in BROADCAST_MACS}:
            # all other interfaces in BD except ingress
            ifs = s.exec(select(Interface).where(Interface.bridge_domain_id == bd_id)).all()
            egress_ids = [i.id for i in ifs if i.id != ingress_interface_id]
            return {"action": "flood", "egress_interface_ids": egress_ids}

        dst_entry = s.exec(
            select(MacAddressEntry).where(
                (MacAddressEntry.bridge_domain_id == bd_id) & (MacAddressEntry.mac_address == dst)
            )
        ).first()
        if dst_entry:
            return {"action": "forward", "egress_interface_id": dst_entry.interface_id}
        else:
            # Unknown unicast → flood to all others
            ifs = s.exec(select(Interface).where(Interface.bridge_domain_id == bd_id)).all()
            egress_ids = [i.id for i in ifs if i.id != ingress_interface_id]
            return {"action": "flood", "egress_interface_ids": egress_ids}
