"""Provisioning L3 auto-configuration helpers.

Contains deterministic, idempotent routines to configure L3 adjacencies
for router uplinks post-provisioning. Extracted from provisioning_service
to keep modules under the 400-line policy without changing behavior.
"""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import (
    VRF,
    AdminStatus,
    Device,
    DeviceType,
    Interface,
    InterfaceAddress,
    Link,
    Neighbor,
    Route,
)
from backend.services.seed_service import ensure_ipam_defaults


def auto_configure_l3_uplinks(session: Session, device: Device) -> None:
    """Auto-configure L3 adjacencies on router uplinks.

    Scope (phase 1):
      - EDGE_ROUTER → CORE_ROUTER link(s): assign deterministic /31 on both ends,
        add default route on EDGE via the core-side IP, and create a Neighbor entry.
      - CORE_ROUTER → BACKBONE_GATEWAY link(s): assign deterministic /31 and add
        default route on CORE via backbone-side IP (when no default exists).

    Idempotent: existing InterfaceAddress/Neighbor/Route entries are respected and reused.
    Deterministic: /31 host pair is derived from link id using a stable hash.
    """
    # Only applies to routers
    if device.type not in {DeviceType.EDGE_ROUTER, DeviceType.CORE_ROUTER}:
        return

    # Ensure a VRF is assigned (mgmt) if none is set
    mgmt_vrf = session.exec(select(VRF).where(VRF.name == "mgmt")).first()
    if not mgmt_vrf:
        ensure_ipam_defaults(session)
        mgmt_vrf = session.exec(select(VRF).where(VRF.name == "mgmt")).first()
    if not mgmt_vrf:
        return  # cannot proceed without a VRF context
    if device.vrf_id is None:
        device.vrf_id = mgmt_vrf.id
        session.add(device)
        session.flush()

    # Collect this device's interfaces and adjacent links
    if_rows = session.exec(select(Interface).where(Interface.device_id == device.id)).all()
    my_if_ids = {i.id for i in if_rows}
    if not my_if_ids:
        return
    link_rows = session.exec(select(Link)).all()

    def _stable_ptp_pair(link_id: str) -> tuple[str, str, int]:
        """Derive a deterministic /31 host pair for a link id in 172.18.0.0/16.

        Returns (ip_low, ip_high, 31)."""
        import hashlib

        h = hashlib.sha1(link_id.encode()).digest()
        # Use 3 bytes for host: X.Y where X in [0,255], Y in [0,254] even
        x = h[0]
        y = h[1]
        # Ensure even and not 255
        y = y & 0xFE
        if y == 0xFE:
            # allow 254 (even); 255 never produced due to mask
            pass
        base = f"172.18.{x}.{y}"
        peer = f"172.18.{x}.{y + 1}"
        return base, peer, 31

    # Helper to ensure an InterfaceAddress exists
    def _ensure_addr(iid: str, ip: str, mask: int, vrf_id: int) -> None:
        ia = session.exec(
            select(InterfaceAddress).where(
                (InterfaceAddress.interface_id == iid) & (InterfaceAddress.ip == ip)
            )
        ).first()
        if ia:
            return
        # If any address already present, don't override (respect manual config)
        any_addr = session.exec(
            select(InterfaceAddress).where(InterfaceAddress.interface_id == iid)
        ).first()
        if any_addr:
            return
        session.add(InterfaceAddress(interface_id=iid, ip=ip, prefix_len=mask, vrf_id=vrf_id))

    # Helper to ensure a Neighbor exists (deterministic dummy MAC)
    def _ensure_neighbor(iid: str, ip: str, link_id: str) -> None:
        nb = session.exec(
            select(Neighbor).where((Neighbor.interface_id == iid) & (Neighbor.ip_address == ip))
        ).first()
        if nb:
            return
        import hashlib

        d = hashlib.sha1(f"{link_id}:{iid}:{ip}".encode()).digest()
        mac = f"02:{d[0]:02x}:{d[1]:02x}:{d[2]:02x}:{d[3]:02x}:{d[4]:02x}"
        session.add(Neighbor(interface_id=iid, ip_address=ip, mac_address=mac))

    # Helper to ensure a default route exists for dev via (iid -> nh)
    def _ensure_default_route(vrf_id: int, iid: str, nh: str) -> None:
        existing = session.exec(
            select(Route).where(
                (Route.vrf_id == vrf_id)
                & (Route.prefix == "0.0.0.0/0")
                & (Route.interface_id == iid)
                & (Route.next_hop == nh)
            )
        ).first()
        if existing:
            return
        # If a default already exists on THIS DEVICE (any interface), do not add another.
        # Important: do NOT suppress based on VRF-global defaults from other devices.
        # We need other interfaces for this device. Using captured my_if_ids above.
        existing_defaults = session.exec(
            select(Route).where((Route.vrf_id == vrf_id) & (Route.prefix == "0.0.0.0/0"))
        ).all()
        if any(r.interface_id in my_if_ids for r in existing_defaults):
            return
        session.add(Route(vrf_id=vrf_id, prefix="0.0.0.0/0", next_hop=nh, interface_id=iid))

    # Iterate adjacent links, applying rules per upstream peer type
    changed = False
    for ln in link_rows:
        if not (ln.a_interface_id in my_if_ids or ln.b_interface_id in my_if_ids):
            continue
        my_if = ln.a_interface_id if ln.a_interface_id in my_if_ids else ln.b_interface_id
        peer_if = ln.b_interface_id if my_if == ln.a_interface_id else ln.a_interface_id
        peer_if_row = session.get(Interface, peer_if)
        if not peer_if_row:
            continue
        peer_dev = session.get(Device, peer_if_row.device_id)
        if not peer_dev:
            continue
        # Determine upstream relation
        downstream_type = None
        upstream_ok = False
        if device.type == DeviceType.EDGE_ROUTER and peer_dev.type == DeviceType.CORE_ROUTER:
            downstream_type = DeviceType.EDGE_ROUTER
            upstream_ok = True
        elif device.type == DeviceType.CORE_ROUTER and peer_dev.type == DeviceType.BACKBONE_GATEWAY:
            downstream_type = DeviceType.CORE_ROUTER
            upstream_ok = True
        else:
            upstream_ok = False
        if not upstream_ok:
            continue

        # Admin up both interfaces (non-destructive; only if currently DOWN)
        my_if_row = session.get(Interface, my_if)
        if my_if_row and my_if_row.admin_status == AdminStatus.DOWN:
            my_if_row.admin_status = AdminStatus.UP
            session.add(my_if_row)
            changed = True
        if peer_if_row and peer_if_row.admin_status == AdminStatus.DOWN:
            peer_if_row.admin_status = AdminStatus.UP
            session.add(peer_if_row)
            changed = True

        # Assign deterministic /31 addresses to both ends if neither has an address
        a_ip, b_ip, mask = _stable_ptp_pair(ln.id or f"{my_if}--{peer_if}")
        # Ensure deterministic side assignment: lower interface id gets lower IP
        if my_if < peer_if:
            my_ip, peer_ip = a_ip, b_ip
        else:
            my_ip, peer_ip = b_ip, a_ip
        _ensure_addr(my_if, my_ip, mask, device.vrf_id)  # type: ignore[arg-type]
        _ensure_addr(peer_if, peer_ip, mask, peer_dev.vrf_id or device.vrf_id)  # type: ignore[arg-type]

        # Create neighbor entries (optional but helpful)
        _ensure_neighbor(my_if, peer_ip, ln.id or "")
        _ensure_neighbor(peer_if, my_ip, ln.id or "")

        # Default route only on downstream device (EDGE or CORE per mapping)
        if downstream_type == device.type:
            _ensure_default_route(device.vrf_id, my_if, peer_ip)  # type: ignore[arg-type]
        changed = True

    if changed:
        try:
            session.commit()
        except Exception:
            session.rollback()
            # Do not raise further; keep provisioning success regardless
            return


__all__ = ["auto_configure_l3_uplinks"]
