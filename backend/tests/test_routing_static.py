from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import VRF


def test_add_and_list_static_routes():
    init_db()
    client = TestClient(app)

    # Create a device and a VRF
    r = client.post(
        "/api/devices",
        json={"id": "r1", "name": "r1", "type": "EDGE_ROUTER"},
    )
    assert r.status_code in (200, 201)
    with get_session() as s:
        # ensure a VRF exists
        vrf = s.exec(select(VRF).where(VRF.name == "default")).first()
        if not vrf:
            vrf = VRF(name="default")
            s.add(vrf)
            s.commit()
            s.refresh(vrf)
        vrf_id = vrf.id
        assert vrf_id is not None

    # Add a static route
    payload = {
        "vrf_id": vrf_id,
        "prefix": "192.168.10.0/24",
        "next_hop": "10.0.0.1",
        "interface_id": None,
        "admin_distance": 1,
        "metric": 0,
    }
    rr = client.post(f"/api/devices/r1/routing/vrfs/{vrf_id}/routes", json=payload)
    assert rr.status_code in (200, 201)
    route = rr.json()
    assert route["prefix"] == "192.168.10.0/24"

    # List routes and check presence
    lr = client.get(f"/api/devices/r1/routing/vrfs/{vrf_id}/routes")
    assert lr.status_code == 200
    routes = lr.json()
    assert any(r["prefix"] == "192.168.10.0/24" for r in routes)
