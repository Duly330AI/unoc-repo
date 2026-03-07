from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import VRF, Device, Interface, Link, Route
from backend.services.forwarding_service import Flow, resolve_flow_path


def _ensure_vrf(name: str = "default") -> int:
    with get_session() as s:
        v = s.exec(select(VRF).where(VRF.name == name)).first()
        if not v:
            v = VRF(name=name)
            s.add(v)
            s.commit()
            s.refresh(v)
        assert v.id is not None
        return v.id


def _mk_link(a_if: str, b_if: str) -> None:
    with get_session() as s:
        if not s.get(Link, f"{a_if.split('-')[0]}__{b_if.split('-')[0]}"):
            # canonical id for tests uses device ids (utils.canonical_link_id), but here minimal unique id is fine
            s.add(Link(id=f"{a_if}__{b_if}", a_interface_id=a_if, b_interface_id=b_if))
            s.commit()


def test_multihop_success_router_to_router():
    init_db()
    client = TestClient(app)

    # Devices: r1 -- r2
    for rid in ("r1", "r2"):
        rr = client.post("/api/devices", json={"id": rid, "name": rid, "type": "EDGE_ROUTER"})
        assert rr.status_code in (200, 201)
    vrf_id = _ensure_vrf()
    with get_session() as s:
        for rid in ("r1", "r2"):
            d = s.get(Device, rid)
            assert d
            d.vrf_id = vrf_id
            s.add(d)
        s.commit()
        # Interfaces
        i1 = Interface(id="r1-eth1", device_id="r1", name="eth1")
        i2 = Interface(id="r2-eth1", device_id="r2", name="eth1")
        s.add(i1)
        s.add(i2)
        s.commit()
    _mk_link("r1-eth1", "r2-eth1")

    # Routes
    with get_session() as s:
        # r1 forwards to r2 as next-hop over r1-eth1
        s.add(
            Route(
                vrf_id=vrf_id,
                prefix="172.16.0.0/16",
                interface_id="r1-eth1",
                next_hop="10.0.0.2",
            )
        )
        from backend.models import Neighbor

        s.add(
            Neighbor(interface_id="r1-eth1", ip_address="10.0.0.2", mac_address="aa:bb:cc:dd:ee:f0")
        )
        # r2 has directly connected 172.16.1.0/24 on eth1 (simulate host behind r2)
        s.add(Route(vrf_id=vrf_id, prefix="172.16.1.0/24", interface_id="r2-eth1"))
        s.commit()

    flow = Flow(source_ip="10.0.0.10", destination_ip="172.16.1.5", current_device_id="r1")
    out = resolve_flow_path(flow)
    assert out["outcome"] == "delivered", out
    # Path should reach r2 then deliver out r2-eth1 (directly connected)
    assert len(out["hops"]) >= 3, out
    assert out["final_device_id"] == "r2", out
    assert out["final_interface_id"] == "r2-eth1", out


def test_multihop_drop_midpath_no_route():
    init_db()
    client = TestClient(app)

    # Devices: r3 -- r4
    for rid in ("r3", "r4"):
        rr = client.post("/api/devices", json={"id": rid, "name": rid, "type": "EDGE_ROUTER"})
        assert rr.status_code in (200, 201)
    vrf_id = _ensure_vrf()
    with get_session() as s:
        for rid in ("r3", "r4"):
            d = s.get(Device, rid)
            assert d
            d.vrf_id = vrf_id
            s.add(d)
        s.commit()
        # Interfaces
        s.add(Interface(id="r3-eth1", device_id="r3", name="eth1"))
        s.add(Interface(id="r4-eth1", device_id="r4", name="eth1"))
        s.commit()
    _mk_link("r3-eth1", "r4-eth1")

    # Only r3 has a route via r4 as next-hop; r4 lacks a route to destination
    with get_session() as s:
        # Configure next-hop towards r4
        s.add(
            Route(
                vrf_id=vrf_id,
                prefix="10.200.0.0/16",
                interface_id="r3-eth1",
                next_hop="10.0.0.2",
            )
        )
        # Resolve next-hop at r3 so first hop forwards across the link
        from backend.models import Neighbor

        s.add(
            Neighbor(interface_id="r3-eth1", ip_address="10.0.0.2", mac_address="aa:bb:cc:dd:ee:01")
        )
        s.commit()

    flow = Flow(source_ip="1.1.1.1", destination_ip="10.200.1.2", current_device_id="r3")
    out = resolve_flow_path(flow, ttl=4)
    assert out["outcome"] == "drop", out
    assert out["reason"] in {"no_route_found", "l3_drop"}, out


def test_multihop_ttl_exceeded():
    init_db()
    client = TestClient(app)

    # Single router with a route pointing to itself via interface but no link (will deliver); use tiny ttl to force drop earlier
    rr = client.post("/api/devices", json={"id": "r5", "name": "r5", "type": "EDGE_ROUTER"})
    assert rr.status_code in (200, 201)
    vrf_id = _ensure_vrf()
    with get_session() as s:
        d = s.get(Device, "r5")
        assert d
        d.vrf_id = vrf_id
        s.add(d)
        s.commit()
        s.add(Interface(id="r5-eth1", device_id="r5", name="eth1"))
        s.commit()
        s.add(Route(vrf_id=vrf_id, prefix="192.0.2.0/24", interface_id="r5-eth1"))
        s.commit()

    flow = Flow(source_ip="9.9.9.9", destination_ip="192.0.2.10", current_device_id="r5")
    out = resolve_flow_path(flow, ttl=0)
    assert out["outcome"] == "drop"
    assert out["reason"] == "ttl_exceeded"


def test_mixed_l2_l3_end_switch_router_destination():
    """End Device -> Switch -> Router -> Destination network.

    - End Device connects to AON_SWITCH on iface s1-eth1.
    - Router r1 connects to AON_SWITCH on iface r1-eth1.
    - Router has a directly-connected route to 192.0.2.0/24 out r1-eth2 (no peer -> delivered).
    - Flow from End Device to 192.0.2.10 should:
        1) be L2 forwarded by switch from s1-eth1 to r1-eth1
        2) at router, L3 route to r1-eth2 and be delivered (direct connect)
    """
    init_db()
    client = TestClient(app)

    # Create POP container to satisfy AON_SWITCH parent validation
    r = client.post("/api/devices", json={"id": "pop1", "name": "pop1", "type": "POP"})
    assert r.status_code in (200, 201)
    # Create AON_SWITCH with POP parent via API to trigger auto BD creation
    r = client.post(
        "/api/devices",
        json={"id": "s1", "name": "s1", "type": "AON_SWITCH", "parent_container_id": "pop1"},
    )
    assert r.status_code in (200, 201)
    r = client.post("/api/devices", json={"id": "r1", "name": "r1", "type": "EDGE_ROUTER"})
    assert r.status_code in (200, 201)
    r = client.post("/api/devices", json={"id": "ed1", "name": "ed1", "type": "AON_CPE"})
    assert r.status_code in (200, 201)

    vrf_id = _ensure_vrf()
    with get_session() as s:
        # assign vrf to router
        d = s.get(Device, "r1")
        assert d
        d.vrf_id = vrf_id
        s.add(d)
        s.commit()
        # interfaces
        s.add(Interface(id="s1-eth1", device_id="s1", name="eth1"))
        s.add(Interface(id="s1-eth2", device_id="s1", name="eth2"))
        s.add(Interface(id="r1-eth1", device_id="r1", name="eth1"))
        s.add(Interface(id="r1-eth2", device_id="r1", name="eth2"))
        s.add(Interface(id="ed1-eth0", device_id="ed1", name="eth0"))
        s.commit()
        # Default bridge domain should exist automatically for s1 (switch device)
        from backend.models import BridgeDomain

        bd = s.exec(
            select(BridgeDomain).where(
                (BridgeDomain.device_id == "s1") & (BridgeDomain.name == "default")
            )
        ).first()
        assert bd is not None
        i1 = s.get(Interface, "s1-eth1")
        i2 = s.get(Interface, "s1-eth2")
        assert i1 and i2
        i1.bridge_domain_id = bd.id
        i2.bridge_domain_id = bd.id
        s.add(i1)
        s.add(i2)
        s.commit()

    # Wiring: ed1-eth0 <-> s1-eth1 and s1-eth2 <-> r1-eth1
    _mk_link("ed1-eth0", "s1-eth1")
    _mk_link("s1-eth2", "r1-eth1")

    # Route on router: directly connected net out r1-eth2
    with get_session() as s:
        s.add(Route(vrf_id=vrf_id, prefix="192.0.2.0/24", interface_id="r1-eth2"))
        s.commit()

    # Simulate that switch has learned MAC for ed1 ingress and would forward towards r1
    # Our L2 engine will flood if unknown; allow flood-single path by ensuring only one egress
    # We emulate ingress on s1-eth1 so egress must be s1-eth2

    flow = Flow(
        source_ip="10.1.1.1",
        destination_ip="192.0.2.10",
        current_device_id="ed1",
        current_interface_id="ed1-eth0",
    )

    # First hop: ed1 is not a switch or router (unsupported), so we expect an immediate drop.
    # To start from the switch as ingress, set current_device to s1 with ingress at s1-eth1
    flow = Flow(
        source_ip="10.1.1.1",
        destination_ip="192.0.2.10",
        current_device_id="s1",
        current_interface_id="s1-eth1",
    )
    out = resolve_flow_path(flow)
    assert out["outcome"] == "delivered", out
    # Final delivery at router out r1-eth2 (no peer)
    assert out["final_device_id"] == "r1", out
    assert out["final_interface_id"] == "r1-eth2", out
    # Check hop metadata exists and sequence of actions: first L2, then L3
    meta = out.get("hop_metadata") or []
    assert len(meta) >= 2, meta
    assert meta[0]["device_id"] == "s1"
    assert meta[0]["device_type"] == "AON_SWITCH"
    assert meta[0]["action"] in {"l2_forward", "l2_flood_single"}
    assert meta[1]["device_id"] == "r1"
    assert meta[1]["device_type"] in {"EDGE_ROUTER", "CORE_ROUTER", "BACKBONE_GATEWAY"}
    assert meta[1]["action"] == "l3_route"
