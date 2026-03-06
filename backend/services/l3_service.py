from __future__ import annotations

import ipaddress
from typing import TypedDict

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, Neighbor, Route


class Packet(TypedDict, total=False):
    destination_ip: str
    source_ip: str


class ForwardDecision(TypedDict, total=False):
    action: str
    reason: str
    egress_interface_id: str
    next_hop_mac: str


def _longest_prefix_match(vrf_id: int, dst_ip: str) -> Route | None:
    """Return the Route with the most-specific prefix that matches dst_ip in a VRF."""
    try:
        target = ipaddress.ip_address(dst_ip)
    except ValueError:
        return None

    best: tuple[int, Route] | None = None
    with get_session() as s:
        routes = s.exec(select(Route).where(Route.vrf_id == vrf_id)).all()
        for r in routes:
            try:
                net = ipaddress.ip_network(r.prefix, strict=False)
            except Exception:
                continue
            if target in net:
                plen = net.prefixlen
                if best is None or plen > best[0]:
                    best = (plen, r)
    return best[1] if best else None


def _resolve_next_hop_mac(interface_id: str, next_hop_ip: str) -> str | None:
    with get_session() as s:
        n = s.exec(
            select(Neighbor).where(
                (Neighbor.interface_id == interface_id) & (Neighbor.ip_address == next_hop_ip)
            )
        ).first()
        return n.mac_address if n else None


def _device_default_vrf_id(device_id: str) -> int | None:
    with get_session() as s:
        d = s.get(Device, device_id)
        return d.vrf_id if d else None


def get_forwarding_decision(device_id: str, packet: dict | Packet) -> ForwardDecision:
    """Compute L3 forwarding decision for a device.

    Contract:
    - Input: device_id (router id), packet with at least destination_ip
    - Output: ForwardDecision dict with action=forward|drop and optional egress_interface_id, next_hop_mac, or reason
    - Errors: invalid packet fields → drop:invalid_packet
    """
    init_db()
    dst = packet.get("destination_ip")  # type: ignore[assignment]
    if not dst:
        return {"action": "drop", "reason": "invalid_packet"}

    vrf_id = _device_default_vrf_id(device_id)
    if vrf_id is None:
        return {"action": "drop", "reason": "no_device_vrf"}

    route = _longest_prefix_match(vrf_id, dst)
    if not route:
        return {"action": "drop", "reason": "no_route_found"}

    # Directly connected network (interface only)
    if route.interface_id and not route.next_hop:
        return {"action": "forward", "egress_interface_id": route.interface_id}

    # Next-hop case: need interface and next_hop
    if route.interface_id and route.next_hop:
        mac = _resolve_next_hop_mac(route.interface_id, route.next_hop)
        if not mac:
            return {"action": "drop", "reason": "next_hop_unresolved"}
        return {
            "action": "forward",
            "egress_interface_id": route.interface_id,
            "next_hop_mac": mac,
        }

    # If only next_hop provided but no interface, we can't decide egress reliably yet
    if route.next_hop and not route.interface_id:
        return {"action": "drop", "reason": "egress_interface_unknown"}

    return {"action": "drop", "reason": "invalid_route"}
