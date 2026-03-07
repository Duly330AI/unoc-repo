from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import VRF, Device, Interface, Neighbor, Route
from backend.services.l3_service import get_forwarding_decision


def _ensure_default_vrf() -> int:
    with get_session() as s:
        vrf = s.exec(select(VRF).where(VRF.name == "default")).first()
        if not vrf:
            vrf = VRF(name="default")
            s.add(vrf)
            s.commit()
            s.refresh(vrf)
        assert vrf.id is not None
        return vrf.id


def test_lpm_picks_most_specific_prefix_and_connected_forward():
    init_db()
    client = TestClient(app)

    # Create router device and interfaces
    r = client.post("/api/devices", json={"id": "r1", "name": "r1", "type": "EDGE_ROUTER"})
    assert r.status_code in (200, 201)
    vrf_id = _ensure_default_vrf()
    # bind device default vrf
    with get_session() as s:
        d = s.get(Device, "r1")
        assert d
        d.vrf_id = vrf_id
        s.add(d)
        s.commit()
        # create egress interface
        iface = Interface(id="r1-eth1", device_id="r1", name="eth1")
        s.add(iface)
        s.commit()
        s.refresh(iface)
        # two routes: broader and more specific
        s.add(Route(vrf_id=vrf_id, prefix="10.0.0.0/8", interface_id="r1-eth1"))
        s.add(Route(vrf_id=vrf_id, prefix="10.1.0.0/16", interface_id="r1-eth1"))
        s.commit()

    decision = get_forwarding_decision("r1", {"destination_ip": "10.1.2.3"})
    assert decision.get("action") == "forward"
    assert decision.get("egress_interface_id") == "r1-eth1"


def test_next_hop_resolution_success():
    init_db()
    client = TestClient(app)

    # Create router and interface
    r = client.post("/api/devices", json={"id": "r2", "name": "r2", "type": "EDGE_ROUTER"})
    assert r.status_code in (200, 201)
    vrf_id = _ensure_default_vrf()
    with get_session() as s:
        d = s.get(Device, "r2")
        assert d
        d.vrf_id = vrf_id
        s.add(d)
        s.commit()
        iface = Interface(id="r2-eth1", device_id="r2", name="eth1")
        s.add(iface)
        s.commit()
        s.refresh(iface)
        # static route via next hop
        s.add(
            Route(
                vrf_id=vrf_id, prefix="192.168.0.0/16", interface_id="r2-eth1", next_hop="10.0.0.2"
            )
        )
        # neighbor entry to resolve next hop
        s.add(
            Neighbor(interface_id="r2-eth1", ip_address="10.0.0.2", mac_address="aa:bb:cc:dd:ee:ff")
        )
        s.commit()

    decision = get_forwarding_decision("r2", {"destination_ip": "192.168.1.100"})
    assert decision.get("action") == "forward"
    assert decision.get("egress_interface_id") == "r2-eth1"
    assert decision.get("next_hop_mac") == "aa:bb:cc:dd:ee:ff"


def test_no_route_results_in_drop():
    init_db()
    client = TestClient(app)

    r = client.post("/api/devices", json={"id": "r3", "name": "r3", "type": "EDGE_ROUTER"})
    assert r.status_code in (200, 201)
    vrf_id = _ensure_default_vrf()
    with get_session() as s:
        d = s.get(Device, "r3")
        assert d
        d.vrf_id = vrf_id
        s.add(d)
        s.commit()

    decision = get_forwarding_decision("r3", {"destination_ip": "172.16.1.1"})
    assert decision.get("action") == "drop"
    assert decision.get("reason") == "no_route_found"
