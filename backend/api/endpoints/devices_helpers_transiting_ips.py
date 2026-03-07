"""Helper for transiting IPs endpoint - computes IPs flowing through passive devices."""

from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from backend.models import Device, DeviceType, Interface, InterfaceAddress, Link


def get_device_transiting_ips_impl(session: Session, device_id: str) -> dict:
    """Compute IPs transiting through a passive device (OLT, Splitter, etc.).

    Passive devices don't have L3 routing but IPs flow through them at L2.
    We find all downstream devices and aggregate their IPs.

    Returns:
        {
            "device_id": str,
            "device_name": str,
            "device_type": str,
            "is_passive": bool,
            "transiting_ips": [
                {
                    "ip": str,  # e.g., "10.0.1.10/32"
                    "source_device_id": str,
                    "source_device_name": str,
                    "via_interface": str,  # Interface on THIS device where traffic enters/exits
                }
            ],
            "ip_pools": [
                {
                    "subnet": str,  # e.g., "10.0.1.0/24"
                    "active_count": int,
                    "interfaces": [str],  # Interfaces carrying this subnet
                }
            ]
        }
    """
    # Get device
    device = session.get(Device, device_id)
    if not device:
        raise LookupError(f"Device {device_id} not found")

    # Determine if device is passive (no L3 routing, no electronics)
    # Only optical splitters are truly passive (L1 only)
    # OLT is ACTIVE (has OLT-Card, management IP, routing)
    passive_types = {DeviceType.SPLITTER}
    is_passive = device.type in passive_types

    # Get all interfaces of this device
    device_interfaces = session.exec(
        select(Interface).where(Interface.device_id == device_id)
    ).all()

    interface_ids = {iface.id for iface in device_interfaces}

    # Find all links connected to this device
    links = session.exec(
        select(Link).where(
            (Link.a_interface_id.in_(interface_ids)) | (Link.b_interface_id.in_(interface_ids))
        )
    ).all()

    # Collect transiting IPs from downstream devices
    transiting_ips: list[dict] = []
    ip_by_subnet: dict[str, set[str]] = defaultdict(set)
    interface_by_subnet: dict[str, set[str]] = defaultdict(set)

    for link in links:
        # Find peer interface (the one NOT on this device)
        if link.a_interface_id in interface_ids:
            peer_interface_id = link.b_interface_id
            local_interface_id = link.a_interface_id
        else:
            peer_interface_id = link.a_interface_id
            local_interface_id = link.b_interface_id

        # Get local interface name
        local_iface = session.get(Interface, local_interface_id)
        local_iface_name = local_iface.name if local_iface else "unknown"

        # Get peer interface
        peer_interface = session.get(Interface, peer_interface_id)
        if not peer_interface:
            continue

        # Get peer device
        peer_device = (
            session.get(Device, peer_interface.device_id) if peer_interface.device_id else None
        )
        if not peer_device:
            continue

        # Get all IPs on peer device (recursively if needed)
        peer_ips = session.exec(
            select(InterfaceAddress)
            .join(Interface, InterfaceAddress.interface_id == Interface.id)
            .where(Interface.device_id == peer_device.id)
        ).all()

        for ip_addr in peer_ips:
            ip_with_prefix = f"{ip_addr.ip}/{ip_addr.prefix_len}"

            transiting_ips.append(
                {
                    "ip": ip_with_prefix,
                    "source_device_id": peer_device.id,
                    "source_device_name": peer_device.name,
                    "via_interface": local_iface_name,
                }
            )

            # Extract subnet for aggregation (e.g., "10.0.1.0/24" from "10.0.1.10/32")
            # Simplified: use prefix_len to group
            subnet_key = f"{ip_addr.ip.rsplit('.', 1)[0]}.0/{ip_addr.prefix_len}"
            ip_by_subnet[subnet_key].add(ip_addr.ip)
            interface_by_subnet[subnet_key].add(local_iface_name)

    # Build IP pools summary
    ip_pools = [
        {
            "subnet": subnet,
            "active_count": len(ips),
            "interfaces": sorted(interface_by_subnet[subnet]),
        }
        for subnet, ips in ip_by_subnet.items()
    ]

    return {
        "device_id": device.id,
        "device_name": device.name,
        "device_type": str(device.type.value) if device.type else None,
        "is_passive": is_passive,
        "transiting_ips": transiting_ips,
        "ip_pools": ip_pools,
    }
