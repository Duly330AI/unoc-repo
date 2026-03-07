"""Trace-focused utilities for upstream L3 path resolution (split from dependency_resolver).

Contains trace_l3_path_to_anchor and has_l3_reachability_to_anchor. Behavior preserved.
"""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import Device, DeviceType, Interface, InterfaceAddress, Link, Route

# Import dataclass for typed return
from .dependency_resolver_core import DependencyCheckResult


def trace_l3_path_to_anchor(session: Session, device: Device) -> DependencyCheckResult:
    """Trace the deterministic L3 path to a BACKBONE anchor, returning chain and reason.

    Administrative overrides are respected at every hop, including the starting device and
    the terminal BACKBONE anchor. A forced-DOWN device will not be considered reachable.
    """
    try:
        # Local helper: a link is traversable only if administratively passable and
        # neither endpoint device is forced DOWN. Mirrors original inlined semantics.
        def _link_passable(ln: Link) -> bool:
            try:
                lov = getattr(ln, "admin_override_status", None)
                if lov is not None:
                    if getattr(lov, "value", str(lov)) != "UP":
                        return False
                else:
                    st = getattr(ln, "status", None)
                    if st is None or getattr(st, "value", str(st)) != "UP":
                        return False
                a_if = session.get(Interface, ln.a_interface_id)
                b_if = session.get(Interface, ln.b_interface_id)
                if not a_if or not b_if:
                    return False
                a_dev = session.get(Device, a_if.device_id) if a_if.device_id else None
                b_dev = session.get(Device, b_if.device_id) if b_if.device_id else None
                for dv in (a_dev, b_dev):
                    if dv is None:
                        return False
                    dov = getattr(dv, "admin_override_status", None)
                    if dov is not None and getattr(dov, "value", str(dov)) == "DOWN":
                        return False
                return True
            except Exception:
                return False

        # Starting device administrative override gating
        dov = getattr(device, "admin_override_status", None)
        if (dov is not None and str(dov) == "DOWN") or (
            dov is not None and hasattr(dov, "value") and dov.value == "DOWN"
        ):
            return DependencyCheckResult(False, reason="self_forced_down", chain=[device.id])

        # Only L3 routers (CORE_ROUTER, EDGE_ROUTER) require VRF context.
        # Access devices (OLT, ONT, AON_SWITCH, AON_CPE) use management IPs without VRF.
        # BACKBONE_GATEWAY is the anchor and doesn't need VRF.
        router_types = {DeviceType.CORE_ROUTER, DeviceType.EDGE_ROUTER}
        if device.type in router_types and device.vrf_id is None:
            return DependencyCheckResult(False, reason="no_vrf", chain=[device.id])

        visited: set[str] = set()
        chain: list[str] = [device.id]

        def _resolve_peer_via_if(if_id: str, expect_ip: str | None) -> Device | None:
            links = session.exec(
                select(Link).where((Link.a_interface_id == if_id) | (Link.b_interface_id == if_id))
            ).all()
            links = [lnk for lnk in links if _link_passable(lnk)]
            if not links:
                return None
            chosen_link: Link | None = None
            if expect_ip is not None:
                matching: list[Link] = []
                for lnk in links:
                    peer_if_id = (
                        lnk.b_interface_id if lnk.a_interface_id == if_id else lnk.a_interface_id
                    )
                    if not peer_if_id:
                        continue
                    has_ip = session.exec(
                        select(InterfaceAddress).where(
                            (InterfaceAddress.interface_id == peer_if_id)
                            & (InterfaceAddress.ip == expect_ip)
                        )
                    ).first()
                    if has_ip:
                        matching.append(lnk)
                if matching:
                    chosen_link = sorted(matching, key=lambda x: (x.id or ""))[0]
            if chosen_link is None:
                chosen_link = sorted(links, key=lambda x: (x.id or ""))[0]
            peer_if_id = (
                chosen_link.b_interface_id
                if chosen_link.a_interface_id == if_id
                else chosen_link.a_interface_id
            )
            peer_if = session.get(Interface, peer_if_id)
            if not peer_if:
                return None
            return session.get(Device, peer_if.device_id) if peer_if.device_id else None

        def _step(dev: Device) -> DependencyCheckResult:
            if dev.id in visited:
                return DependencyCheckResult(False, reason="loop", chain=chain.copy())
            visited.add(dev.id)
            # Administrative override on the current device blocks traversal
            _dov = getattr(dev, "admin_override_status", None)
            if (_dov is not None and str(_dov) == "DOWN") or (
                _dov is not None and hasattr(_dov, "value") and _dov.value == "DOWN"
            ):
                return DependencyCheckResult(False, reason="forced_down", chain=chain.copy())
            if dev.type == DeviceType.BACKBONE_GATEWAY:
                return DependencyCheckResult(True, reason=None, chain=chain.copy())
            # Only L3 routers require VRF for routing. Access devices skip this check.
            if dev.type in {DeviceType.CORE_ROUTER, DeviceType.EDGE_ROUTER} and dev.vrf_id is None:
                return DependencyCheckResult(False, reason="no_vrf", chain=chain.copy())

            # Access devices (OLT, ONT, switches, etc.) don't have routing tables.
            # For these devices, we find their uplink to the next router via physical topology.
            is_access_device = dev.type not in {
                DeviceType.CORE_ROUTER,
                DeviceType.EDGE_ROUTER,
                DeviceType.BACKBONE_GATEWAY,
            }

            if is_access_device:
                # Find all interfaces on this device
                dev_interfaces = session.exec(
                    select(Interface).where(Interface.device_id == dev.id)
                ).all()
                if not dev_interfaces:
                    return DependencyCheckResult(False, reason="no_interfaces", chain=chain.copy())

                # Find any passable link that connects to upstream device
                # Priority: router/gateway first, then other access devices (for hierarchical access)
                upstream_candidates: list[tuple[int, Device]] = []  # (priority, device)

                for iface in dev_interfaces:
                    links = session.exec(
                        select(Link).where(
                            (Link.a_interface_id == iface.id) | (Link.b_interface_id == iface.id)
                        )
                    ).all()
                    passable_links = [lnk for lnk in links if _link_passable(lnk)]

                    for link in passable_links:
                        peer_if_id = (
                            link.b_interface_id
                            if link.a_interface_id == iface.id
                            else link.a_interface_id
                        )
                        if not peer_if_id:
                            continue
                        peer_if = session.get(Interface, peer_if_id)
                        if not peer_if or not peer_if.device_id:
                            continue
                        peer_dev = session.get(Device, peer_if.device_id)
                        if not peer_dev:
                            continue

                        # Check if peer is a router or backbone gateway (highest priority)
                        if peer_dev.type in {
                            DeviceType.CORE_ROUTER,
                            DeviceType.EDGE_ROUTER,
                            DeviceType.BACKBONE_GATEWAY,
                        }:
                            upstream_candidates.append((1, peer_dev))
                        # Otherwise, if peer is another access device (lower priority for hierarchical access)
                        elif peer_dev.type not in {DeviceType.CORE_ROUTER, DeviceType.EDGE_ROUTER}:
                            upstream_candidates.append((2, peer_dev))

                if not upstream_candidates:
                    return DependencyCheckResult(
                        False, reason="no_upstream_router", chain=chain.copy()
                    )

                # Pick the highest priority upstream (routers first, then access devices)
                upstream_candidates.sort(key=lambda x: x[0])
                peer_dev = upstream_candidates[0][1]

                # Continue trace from upstream device
                pov = getattr(peer_dev, "admin_override_status", None)
                if (pov is not None and str(pov) == "DOWN") or (
                    pov is not None and hasattr(pov, "value") and pov.value == "DOWN"
                ):
                    return DependencyCheckResult(
                        False, reason="peer_forced_down", chain=chain.copy()
                    )
                chain.append(peer_dev.id)
                return _step(peer_dev)

            # For L3 routers, use routing table
            routes = session.exec(
                select(Route).where((Route.vrf_id == dev.vrf_id) & (Route.prefix == "0.0.0.0/0"))
            ).all()
            if not routes:
                return DependencyCheckResult(False, reason="no_default_route", chain=chain.copy())

            cand: list[tuple[int, int, int | None, Route]] = []
            for r in routes:
                if r.interface_id is None:
                    continue
                eg_if = session.get(Interface, r.interface_id)
                if not eg_if or eg_if.device_id != dev.id:
                    continue
                if eg_if.admin_status.value != "up":
                    return DependencyCheckResult(
                        False, reason="egress_admin_down", chain=chain.copy()
                    )
                if not r.next_hop:
                    return DependencyCheckResult(False, reason="no_next_hop", chain=chain.copy())
                cand.append((r.admin_distance, r.metric, r.id, r))

            if not cand:
                return DependencyCheckResult(False, reason="no_eligible_route", chain=chain.copy())

            cand_sorted = sorted(cand, key=lambda t: (t[0], t[1], t[2] if t[2] is not None else -1))
            chosen = cand_sorted[0][3]
            eg_if = session.get(Interface, chosen.interface_id)  # type: ignore[arg-type]
            if not eg_if:
                return DependencyCheckResult(False, reason="egress_missing", chain=chain.copy())

            # Always resolve the peer deterministically through a passable link to an interface
            # bearing the expected next-hop IP, regardless of whether a Neighbor row exists.
            peer_dev = _resolve_peer_via_if(eg_if.id, chosen.next_hop)
            if peer_dev is None:
                # If a Neighbor exists but the link is not passable or IP doesn't match, treat as unresolved
                return DependencyCheckResult(False, reason="peer_unresolved", chain=chain.copy())
            pov = getattr(peer_dev, "admin_override_status", None)
            if (pov is not None and str(pov) == "DOWN") or (
                pov is not None and hasattr(pov, "value") and pov.value == "DOWN"
            ):
                return DependencyCheckResult(False, reason="peer_forced_down", chain=chain.copy())
            chain.append(peer_dev.id)
            return _step(peer_dev)

        return _step(device)
    except Exception:
        return DependencyCheckResult(False, reason="exception", chain=[device.id])


def has_l3_reachability_to_anchor(session: Session, device: Device) -> bool:
    """Return True if the device has L3 reachability to a backbone anchor while recording metrics."""
    import time

    t0 = time.perf_counter()
    res = trace_l3_path_to_anchor(session, device)
    dt = time.perf_counter() - t0
    # Lazy import metrics primitives to avoid import cycles
    try:
        from backend.api.endpoints.metrics import (
            L3_RESOLVER_CALLS,
            L3_RESOLVER_DURATION,
            L3_RESOLVER_HOPS,
        )

        outcome = "ok" if res.ok else "fail"
        reason = "none" if res.ok else (res.reason or "unknown")
        try:
            L3_RESOLVER_DURATION.observe(dt)
        except Exception:
            pass
        try:
            L3_RESOLVER_CALLS.labels(outcome=outcome, reason=reason).inc()
        except Exception:
            pass
        try:
            hops = max(0, (len(res.chain) - 1) if res.chain else 0)
            L3_RESOLVER_HOPS.observe(float(hops))
        except Exception:
            pass
    except Exception:
        # Metrics must never affect behavior
        pass
    return bool(res.ok)


__all__ = [
    "trace_l3_path_to_anchor",
    "has_l3_reachability_to_anchor",
]
