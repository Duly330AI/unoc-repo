from __future__ import annotations

import ipaddress

from pydantic import BaseModel

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Neighbor, Route
from backend.services.l2_service import Frame, process_frame
from backend.services.l3_service import get_forwarding_decision


class Flow(BaseModel):
    source_ip: str
    destination_ip: str
    current_device_id: str
    current_interface_id: str | None = None


def forward_flow(flow: Flow) -> Flow:
    """Advance the flow by one hop based on the current device type.

    - Router: use L3 decision to select egress interface (and next-hop MAC optionally)
    - Switch: use L2 frame processing to select a single egress interface if known

    Note: This is a minimal orchestrator; multi-egress/flood cases are not expanded here.
    """
    init_db()
    with get_session() as s:
        dev = s.get(Device, flow.current_device_id)
        if not dev:
            return flow

        if dev.type in {
            DeviceType.CORE_ROUTER,
            DeviceType.EDGE_ROUTER,
            DeviceType.BACKBONE_GATEWAY,
        }:
            decision = get_forwarding_decision(
                flow.current_device_id, {"destination_ip": flow.destination_ip}
            )
            if decision.get("action") != "forward":
                return flow
            egress_if = decision.get("egress_interface_id")
            if not egress_if:
                return flow
            flow.current_interface_id = egress_if
            # Determine next device by link traversal is outside this scope; we stop after setting egress interface
            return flow

        # Treat AON_SWITCH as switch-like for L2 path
        if dev.type in {DeviceType.AON_SWITCH}:
            # For L2 decision we need a frame; we assume flow carries MACs upstream in future; use placeholder broadcast
            ingress_if = flow.current_interface_id or ""
            frame = Frame(
                {"source_mac": "00:00:00:00:00:00", "destination_mac": "ff:ff:ff:ff:ff:ff"}
            )
            res = process_frame(dev.id, ingress_if, frame)
            if res.get("action") == "forward":
                flow.current_interface_id = res.get("egress_interface_id")  # type: ignore[assignment]
            # For flood or drop, leave flow as-is for now
            return flow

        # Default: no change
        return flow


def _find_peer_interface(
    egress_interface_id: str,
) -> tuple[str | None, str | None, str | None]:
    """Given an egress interface, find the peer interface and its device via Link.

    Returns (peer_interface_id, peer_device_id, link_id) or (None, None, None) if no active link.
    """
    from sqlmodel import select

    from backend.models import Interface, Link, Status

    with get_session() as s:
        ln = s.exec(
            select(Link).where(
                (Link.a_interface_id == egress_interface_id)
                | (Link.b_interface_id == egress_interface_id)
            )
        ).first()
        if not ln or ln.status != Status.UP:
            return None, None, None
        peer_if = (
            ln.b_interface_id if ln.a_interface_id == egress_interface_id else ln.a_interface_id
        )
        peer_iface = s.get(Interface, peer_if)
        if not peer_iface:
            return None, None, None
    return peer_iface.id, peer_iface.device_id, ln.id


def resolve_flow_path(initial_flow: Flow, ttl: int = 16) -> dict:
    """Resolve a multi-hop path for a flow across routers and switches.

    Contract:
    - Input: initial Flow (device_id set, interface optional as ingress), ttl max hops
    - Output dict:
        {
          'outcome': 'delivered'|'drop',
          'reason': <str|None>,
          'hops': [Flow, ...],
          'final_device_id': str,
          'final_interface_id': str|None,
        }
    Behavior:
    - Router hop: use L3 decision (get_forwarding_decision). If not forward -> drop.
    - Switch hop (AON_SWITCH): use L2 process_frame; accept 'forward'; if 'flood' with single egress -> treat as forward; else drop.
    - After selecting egress_interface_id, traverse link to the peer device. If no link -> delivered.
    - Stop when ttl is exhausted -> drop: ttl_exceeded.
    """
    init_db()

    def _step(flow: Flow) -> tuple[str, str | None, str | None, bool, str]:
        """Return (action, egress_if, reason, deliver_here, meta_action) for the current device.

        deliver_here=True indicates the packet should be considered delivered out of
        the current device (e.g., directly connected network); do not traverse links.
        """
        with get_session() as s:
            dev = s.get(Device, flow.current_device_id)
        if not dev:
            return "drop", None, "device_not_found", False, "error"
        if dev.type in {
            DeviceType.CORE_ROUTER,
            DeviceType.EDGE_ROUTER,
            DeviceType.BACKBONE_GATEWAY,
        }:
            decision = get_forwarding_decision(
                flow.current_device_id, {"destination_ip": flow.destination_ip}
            )
            if decision.get("action") != "forward":
                return "drop", None, str(decision.get("reason") or "l3_drop"), False, "l3_drop"
            egress_if = decision.get("egress_interface_id")
            if not egress_if:
                return "drop", None, "no_egress_interface", False, "l3_drop"
            # Validate interface belongs to this device to avoid cross-device leakage
            with get_session() as s:
                from sqlmodel import select

                iface = s.get(Interface, str(egress_if))
                if not iface or iface.device_id != dev.id:
                    # Fall back to device-local route search (VRF is global in current model)
                    # Gather this device's interfaces
                    if_ids = [
                        i.id
                        for i in s.exec(
                            select(Interface).where(Interface.device_id == dev.id)
                        ).all()
                    ]
                    routes = s.exec(select(Route).where(Route.vrf_id == (dev.vrf_id or -1))).all()
                    # Filter to routes whose interface_id is on this device
                    local_routes = [r for r in routes if (r.interface_id or "") in if_ids]
                    # Longest prefix match among local routes
                    try:
                        dst_ip = ipaddress.ip_address(flow.destination_ip)
                    except ValueError:
                        return "drop", None, "invalid_packet", False, "l3_drop"
                    best: tuple[int, Route] | None = None
                    for r in local_routes:
                        try:
                            net = ipaddress.ip_network(r.prefix, strict=False)
                        except Exception:
                            continue
                        if dst_ip in net:
                            plen = net.prefixlen
                            if best is None or plen > best[0]:
                                best = (plen, r)
                    if not best:
                        return "drop", None, "no_route_found", False, "l3_drop"
                    local = best[1]
                    if not local.interface_id:
                        return "drop", None, "egress_interface_unknown", False, "l3_drop"
                    # Next-hop resolution if needed
                    if local.next_hop:
                        nh = s.exec(
                            select(Neighbor).where(
                                (Neighbor.interface_id == local.interface_id)
                                & (Neighbor.ip_address == local.next_hop)
                            )
                        ).first()
                        if not nh:
                            return "drop", None, "next_hop_unresolved", False, "l3_drop"
                        return "forward", str(local.interface_id), None, False, "l3_route"
                    # Directly connected
                    return "forward", str(local.interface_id), None, True, "l3_route"
            # Directly connected: no next-hop mac in decision
            deliver_here = decision.get("next_hop_mac") is None
            return "forward", str(egress_if), None, deliver_here, "l3_route"
        if dev.type in {DeviceType.AON_SWITCH}:
            ingress_if = flow.current_interface_id or ""
            frame = Frame(
                {"source_mac": "00:00:00:00:00:00", "destination_mac": "ff:ff:ff:ff:ff:ff"}
            )
            res = process_frame(dev.id, ingress_if, frame)
            act = str(res.get("action")) if res.get("action") else "drop"
            if act == "forward":
                eg = res.get("egress_interface_id")
                return (
                    ("forward", str(eg), None, False, "l2_forward")
                    if eg
                    else ("drop", None, "l2_no_egress", False, "l2_drop")
                )
            if act == "flood":
                egs = res.get("egress_interface_ids") or []
                if isinstance(egs, list) and len(egs) == 1:
                    return "forward", str(egs[0]), None, False, "l2_flood_single"
                return "drop", None, "l2_ambiguous_flood", False, "l2_drop"
            return "drop", None, str(res.get("reason") or "l2_drop"), False, "l2_drop"
        # Other devices: treat as transparent (no forwarding logic)
        return "drop", None, "unsupported_device_type", False, "error"

    hops: list[Flow] = [initial_flow.model_copy()]
    hop_metadata: list[dict] = []
    remaining = max(0, int(ttl))
    while remaining > 0:
        current = hops[-1]
        # fetch device type for metadata
        with get_session() as s:
            dev = s.get(Device, current.current_device_id)
        dev_type = str(dev.type.name) if dev else "UNKNOWN"
        action, egress_if, reason, deliver_here, meta_action = _step(current)
        if action != "forward" or not egress_if:
            hop_metadata.append(
                {
                    "device_id": current.current_device_id,
                    "device_type": dev_type,
                    "action": meta_action,
                    "egress_interface_id": egress_if,
                    "deliver_here": deliver_here,
                    "reason": reason or "unknown",
                    "link_id_to_next": None,
                }
            )
            return {
                "outcome": "drop",
                "reason": reason or "unknown",
                "hops": hops,
                "hop_metadata": hop_metadata,
                "final_device_id": current.current_device_id,
                "final_interface_id": current.current_interface_id,
            }
        # If directly connected, consider delivered at current device out this port
        if deliver_here:
            delivered = current.model_copy()
            delivered.current_interface_id = egress_if
            hop_metadata.append(
                {
                    "device_id": current.current_device_id,
                    "device_type": dev_type,
                    "action": meta_action,
                    "egress_interface_id": egress_if,
                    "deliver_here": True,
                    "reason": None,
                    "link_id_to_next": None,
                }
            )
            return {
                "outcome": "delivered",
                "reason": None,
                "hops": hops + [delivered],
                "hop_metadata": hop_metadata,
                "final_device_id": current.current_device_id,
                "final_interface_id": egress_if,
            }

        # Otherwise, move across the link if any; if no peer, delivered
        peer_if, peer_dev, link_id = _find_peer_interface(egress_if)
        if not peer_if or not peer_dev:
            # Delivered to directly connected network/host
            delivered = current.model_copy()
            delivered.current_interface_id = egress_if
            hop_metadata.append(
                {
                    "device_id": current.current_device_id,
                    "device_type": dev_type,
                    "action": meta_action,
                    "egress_interface_id": egress_if,
                    "deliver_here": True,
                    "reason": None,
                    "link_id_to_next": None,
                }
            )
            return {
                "outcome": "delivered",
                "reason": None,
                "hops": hops + [delivered],
                "hop_metadata": hop_metadata,
                "final_device_id": current.current_device_id,
                "final_interface_id": egress_if,
            }
        # Advance to next device
        hop_metadata.append(
            {
                "device_id": current.current_device_id,
                "device_type": dev_type,
                "action": meta_action,
                "egress_interface_id": egress_if,
                "deliver_here": False,
                "reason": None,
                "link_id_to_next": link_id,
            }
        )
        nxt = Flow(
            source_ip=initial_flow.source_ip,
            destination_ip=initial_flow.destination_ip,
            current_device_id=peer_dev,
            current_interface_id=peer_if,
        )
        hops.append(nxt)
        remaining -= 1

    # TTL exhausted
    final = hops[-1]
    return {
        "outcome": "drop",
        "reason": "ttl_exceeded",
        "hops": hops,
        "hop_metadata": hop_metadata,
        "final_device_id": final.current_device_id,
        "final_interface_id": final.current_interface_id,
    }
