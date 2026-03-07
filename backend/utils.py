"""Backend helper utilities (link/interface helpers).

Separated to keep route handlers lean.
"""

from __future__ import annotations

from sqlmodel import Session

from .models import Device, DeviceType, Interface
from .services.mac_allocator import next_mac


def ensure_default_interface(session: Session, interface_id: str):
    """Return Interface if exists; auto-create if pattern '<device>-if0' and device exists.

    Returns None if not resolvable.
    """
    iface = session.get(Interface, interface_id)
    if iface:
        return iface
    if interface_id.endswith("-if0"):
        dev_id = interface_id[:-4]
        dev = session.get(Device, dev_id)
        if dev:
            new_iface = Interface(
                id=interface_id,
                device_id=dev.id,
                name="if0",
                mac_address=next_mac(),
            )
            session.add(new_iface)
            return new_iface
    return None


def canonical_link_id(a_interface_id: str, b_interface_id: str) -> str:
    def derive_dev(iface_id: str) -> str:
        return iface_id[:-4] if iface_id.endswith("-if0") else iface_id

    a_id, b_id = a_interface_id, b_interface_id
    if a_id > b_id:
        a_id, b_id = b_id, a_id
    return f"{derive_dev(a_id)}__{derive_dev(b_id)}"


def validate_parent_child(session: Session, dev_type: DeviceType, parent_id: str | None):
    """TASK-009 parent/role validation.

    Rules (initial subset for provisioning prep):
    - POP: must have no parent
    - BACKBONE_GATEWAY: must have no parent
    - OLT / AON_SWITCH must have parent POP (if parent provided must exist & be POP)
    - EDGE_ROUTER: standalone (no parent required; parent ignored if provided and must be rejected to keep model clean)
    - CORE_ROUTER: optional parent not allowed (enforce root placement)
    - Passive inline elements (SPLITTER, HOP, NVT, ODF): must have a parent POP or active aggregation (optional for now -> allow none, future path placement rules)
    - ONT / BUSINESS_ONT: parent optional for now (will rely on link path), but if parent given must not be POP (keep ONT outside container for simplicity MVP)
    """
    # Containers must not have a parent
    if dev_type in {DeviceType.POP, DeviceType.CORE_SITE}:
        if parent_id is not None:
            return False, f"{dev_type} must not have a parent"
        return True, None
    # Backbone/core devices may optionally be parented by CORE_SITE only
    if dev_type in {DeviceType.BACKBONE_GATEWAY, DeviceType.CORE_ROUTER}:
        if parent_id:
            parent = session.get(Device, parent_id)
            if not parent:
                return False, "Parent device not found"
            if parent.type != DeviceType.CORE_SITE:
                return False, f"{dev_type} parent must be CORE_SITE"
        return True, None
    if dev_type in {DeviceType.OLT, DeviceType.AON_SWITCH}:
        # Parent is OPTIONAL; if provided, it must exist and be a POP container
        if parent_id:
            parent = session.get(Device, parent_id)
            if not parent:
                return False, "Parent device not found"
            if parent.type != DeviceType.POP:
                return False, f"{dev_type} parent must be POP"
        return True, None
    if dev_type == DeviceType.EDGE_ROUTER:
        # Optional parent; if provided, must be POP or CORE_SITE
        if parent_id:
            parent = session.get(Device, parent_id)
            if not parent:
                return False, "Parent device not found"
            if parent.type not in {DeviceType.POP, DeviceType.CORE_SITE}:
                return False, "EDGE_ROUTER parent must be POP or CORE_SITE"
        return True, None
    if dev_type in {
        DeviceType.SPLITTER,
        DeviceType.HOP,
        DeviceType.NVT,
        DeviceType.ODF,
    }:
        # Parent optional for now; if provided must exist
        if parent_id:
            if not session.get(Device, parent_id):
                return False, "Parent container not found"
        return True, None
    if dev_type in {DeviceType.ONT, DeviceType.BUSINESS_ONT, DeviceType.AON_CPE}:
        if parent_id:
            parent = session.get(Device, parent_id)
            if not parent:
                return False, "Parent device not found"
            if parent.type in {DeviceType.POP, DeviceType.CORE_SITE}:
                return (
                    False,
                    f"{dev_type} must not be directly parented by container (POP/CORE_SITE)",
                )
        return True, None
    return True, None
