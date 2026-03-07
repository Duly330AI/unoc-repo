"""Helper for IP trace endpoint - computes L3 path with IP details."""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import Device, Interface, InterfaceAddress
from backend.services.dependency_resolver_trace import trace_l3_path_to_anchor


def get_device_ip_trace_impl(session: Session, device_id: str) -> dict:
    """Compute IP communication path from device to backbone_gateway.

    Returns:
        {
            "device_id": str,
            "device_name": str,
            "device_type": str,
            "own_ips": [{"interface": str, "ip": str, "gateway": str | None}],
            "path_to_gateway": [
                {"hop": int, "device_id": str, "device_name": str, "ip": str | None, "interface": str | None}
            ],
            "reachable": bool,
            "reason": str | None  # If unreachable: "no_default_route", "peer_unresolved", etc.
        }
    """
    # Get device
    device = session.get(Device, device_id)
    if not device:
        raise LookupError(f"Device {device_id} not found")

    # Get own IPs
    own_ips: list[dict] = []
    interfaces = session.exec(select(Interface).where(Interface.device_id == device_id)).all()

    for iface in interfaces:
        addrs = session.exec(
            select(InterfaceAddress).where(InterfaceAddress.interface_id == iface.id)
        ).all()

        for addr in addrs:
            # Format IP with prefix length
            ip_with_prefix = f"{addr.ip}/{addr.prefix_len}"
            own_ips.append(
                {
                    "interface": iface.name,
                    "ip": ip_with_prefix,
                }
            )

    # Trace L3 path
    trace_result = trace_l3_path_to_anchor(session, device)

    # Handle None chain case
    if trace_result.chain is None:
        trace_result.chain = [device_id]

    # Build path with IP details
    path_to_gateway: list[dict] = []

    for hop_idx, dev_id in enumerate(trace_result.chain, start=1):
        hop_device = session.get(Device, dev_id)
        if not hop_device:
            continue

        # Try to find the egress interface used in this hop
        # For simplicity, we'll show the first IP found on the device
        # (More sophisticated: trace which interface was used for routing)
        hop_interfaces = session.exec(select(Interface).where(Interface.device_id == dev_id)).all()

        hop_ip: str | None = None
        hop_interface: str | None = None

        for iface in hop_interfaces:
            addr = session.exec(
                select(InterfaceAddress).where(InterfaceAddress.interface_id == iface.id)
            ).first()

            if addr:
                hop_ip = addr.ip
                hop_interface = iface.name
                break  # Use first IP found

        path_to_gateway.append(
            {
                "hop": hop_idx,
                "device_id": hop_device.id,
                "device_name": hop_device.name,
                "device_type": str(hop_device.type.value) if hop_device.type else None,
                "ip": hop_ip,
                "interface": hop_interface,
            }
        )

    return {
        "device_id": device.id,
        "device_name": device.name,
        "device_type": str(device.type.value) if device.type else None,
        "own_ips": own_ips,
        "path_to_gateway": path_to_gateway,
        "reachable": trace_result.ok,
        "reason": trace_result.reason if not trace_result.ok else None,
    }
