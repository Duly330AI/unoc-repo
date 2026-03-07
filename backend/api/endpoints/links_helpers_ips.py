"""Helper for link IPs endpoint - shows IPs on both link endpoints."""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import Interface, InterfaceAddress, Link


def get_link_ips_impl(session: Session, link_id: str) -> dict:
    """Get IP addresses on both endpoints of a link.

    Returns:
        {
            "link_id": str,
            "a_interface": {
                "interface_id": str,
                "interface_name": str,
                "device_id": str,
                "device_name": str,
                "ips": [
                    {
                        "ip": str,  # e.g., "10.0.1.1"
                        "prefix_len": int,  # e.g., 24
                        "full": str,  # e.g., "10.0.1.1/24"
                    }
                ]
            },
            "b_interface": {
                "interface_id": str,
                "interface_name": str,
                "device_id": str,
                "device_name": str,
                "ips": [...]
            },
            "common_subnet": str | None,  # e.g., "10.0.1.0/24" if both are in same subnet
        }
    """
    # Get link
    link = session.get(Link, link_id)
    if not link:
        raise LookupError(f"Link {link_id} not found")

    # Get interface A
    interface_a = session.get(Interface, link.a_interface_id)
    if not interface_a:
        raise LookupError(f"Interface A ({link.a_interface_id}) not found")

    # Get interface B
    interface_b = session.get(Interface, link.b_interface_id)
    if not interface_b:
        raise LookupError(f"Interface B ({link.b_interface_id}) not found")

    # Get device A
    from backend.models import Device

    device_a = session.get(Device, interface_a.device_id) if interface_a.device_id else None
    device_a_name = device_a.name if device_a else "unknown"

    # Get device B
    device_b = session.get(Device, interface_b.device_id) if interface_b.device_id else None
    device_b_name = device_b.name if device_b else "unknown"

    # Get IPs for interface A
    ips_a = session.exec(
        select(InterfaceAddress).where(InterfaceAddress.interface_id == interface_a.id)
    ).all()

    a_ips = [
        {
            "ip": addr.ip,
            "prefix_len": addr.prefix_len,
            "full": f"{addr.ip}/{addr.prefix_len}",
        }
        for addr in ips_a
    ]

    # Get IPs for interface B
    ips_b = session.exec(
        select(InterfaceAddress).where(InterfaceAddress.interface_id == interface_b.id)
    ).all()

    b_ips = [
        {
            "ip": addr.ip,
            "prefix_len": addr.prefix_len,
            "full": f"{addr.ip}/{addr.prefix_len}",
        }
        for addr in ips_b
    ]

    # Detect common subnet (simplified: check if IPs share prefix)
    common_subnet = None
    if a_ips and b_ips:
        # Simple heuristic: if both have IPs with same prefix_len,
        # check if first 3 octets match (e.g., 10.0.1.x/24)
        for a_ip in a_ips:
            for b_ip in b_ips:
                if a_ip["prefix_len"] == b_ip["prefix_len"]:
                    # Extract network prefix (e.g., "10.0.1" from "10.0.1.10")
                    a_prefix = ".".join(a_ip["ip"].split(".")[:3])
                    b_prefix = ".".join(b_ip["ip"].split(".")[:3])
                    if a_prefix == b_prefix:
                        common_subnet = f"{a_prefix}.0/{a_ip['prefix_len']}"
                        break
            if common_subnet:
                break

    return {
        "link_id": link.id,
        "a_interface": {
            "interface_id": interface_a.id,
            "interface_name": interface_a.name,
            "device_id": interface_a.device_id or "unknown",
            "device_name": device_a_name,
            "ips": a_ips,
        },
        "b_interface": {
            "interface_id": interface_b.id,
            "interface_name": interface_b.name,
            "device_id": interface_b.device_id or "unknown",
            "device_name": device_b_name,
            "ips": b_ips,
        },
        "common_subnet": common_subnet,
    }
