from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.tests.helpers_l3 import assign_device_vrf, ensure_vrf, l3_pair


def _mk_device(dev_id: str, dev_type: str):
    client = TestClient(app)
    r = client.post(
        "/api/devices",
        json={"id": dev_id, "name": dev_id, "type": dev_type, "status": "UP"},
    )
    assert r.status_code == 201, r.text


def test_l3_pair_establishes_reachability(monkeypatch):
    # Enable strict L3 so device status reflects reachability
    monkeypatch.setenv("UNOC_L3_STATUS_STRICT", "1")
    client = TestClient(app)

    _mk_device("coreP", "BACKBONE_GATEWAY")
    _mk_device("edgeP", "EDGE_ROUTER")

    # Build a simple L3 adjacency and a default route from edgeP via coreP
    with l3_pair(
        a_device="edgeP",
        b_device="coreP",
        a_iface="edgeP-if0",
        b_iface="coreP-if0",
        vrf_name="mgmt",
        ptp_cidr="172.18.0.0/31",
    ):
        # Provision edgeP (active device) and verify status becomes UP under strict L3
        r = client.post("/api/devices/edgeP/provision")
        assert r.status_code == 200, r.text
        r = client.get("/api/devices/edgeP")
        assert r.status_code == 200
        assert r.json()["status"] == "UP"


def test_default_route_requires_next_hop_and_interface():
    client = TestClient(app)
    _mk_device("coreN", "CORE_ROUTER")
    _mk_device("edgeN", "EDGE_ROUTER")

    vrf_id = ensure_vrf("mgmt")
    assign_device_vrf("edgeN", vrf_id)

    # Missing both next_hop and interface_id should be rejected by endpoint validation
    payload = {
        "vrf_id": vrf_id,
        "prefix": "0.0.0.0/0",
        # next_hop omitted
        # interface_id omitted
    }
    r = client.post(f"/api/devices/edgeN/routing/vrfs/{vrf_id}/routes", json=payload)
    # Our handler currently validates and returns 400; accept either error code presence
    assert r.status_code == 400
    assert (
        "DEFAULT_ROUTE_REQUIRES_INTERFACE" in r.text or "DEFAULT_ROUTE_REQUIRES_NEXT_HOP" in r.text
    )

    # Missing interface_id
    payload2 = {
        "vrf_id": vrf_id,
        "prefix": "0.0.0.0/0",
        "next_hop": "172.19.0.2",
    }
    r2 = client.post(f"/api/devices/edgeN/routing/vrfs/{vrf_id}/routes", json=payload2)
    # Our handler enforces DEFAULT_ROUTE_REQUIRES_INTERFACE → 400
    assert r2.status_code == 400
    assert "DEFAULT_ROUTE_REQUIRES_INTERFACE" in r2.text

    # Missing next_hop
    payload3 = {
        "vrf_id": vrf_id,
        "prefix": "0.0.0.0/0",
        "interface_id": "edgeN-if0",
    }
    r3 = client.post(f"/api/devices/edgeN/routing/vrfs/{vrf_id}/routes", json=payload3)
    # Our handler enforces DEFAULT_ROUTE_REQUIRES_NEXT_HOP → 400
    assert r3.status_code == 400
    assert "DEFAULT_ROUTE_REQUIRES_NEXT_HOP" in r3.text
