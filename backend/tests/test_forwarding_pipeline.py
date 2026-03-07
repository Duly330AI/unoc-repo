from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import VRF, Device, Interface, Route
from backend.services.forwarding_service import Flow, forward_flow


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


def test_forward_flow_router_updates_egress_interface():
    init_db()
    client = TestClient(app)

    # Create router device
    r = client.post("/api/devices", json={"id": "r10", "name": "r10", "type": "EDGE_ROUTER"})
    assert r.status_code in (200, 201)
    vrf_id = _ensure_default_vrf()

    with get_session() as s:
        d = s.get(Device, "r10")
        assert d
        d.vrf_id = vrf_id
        s.add(d)
        s.commit()
    # Create egress interface and route
    iface = Interface(id="r10-eth9", device_id="r10", name="eth9")
    s.add(iface)
    s.commit()
    s.refresh(iface)
    s.add(Route(vrf_id=vrf_id, prefix="172.20.0.0/16", interface_id="r10-eth9"))
    s.commit()

    flow = Flow(source_ip="10.0.0.5", destination_ip="172.20.1.2", current_device_id="r10")
    out = forward_flow(flow)
    assert out.current_interface_id == "r10-eth9"
