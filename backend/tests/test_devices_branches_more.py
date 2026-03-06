from fastapi.testclient import TestClient

from backend.db import get_session
from backend.main import app
from backend.models import Interface


def test_create_device_conflict_409():
    client = TestClient(app)
    payload = {"id": "d1", "name": "d1", "type": "CORE_ROUTER", "status": "UP"}
    r = client.post("/api/devices", json=payload)
    assert r.status_code == 201
    r2 = client.post("/api/devices", json=payload)
    assert r2.status_code == 409


def test_single_backbone_enforcement_and_mgmt_ip_allocation(monkeypatch):
    client = TestClient(app)
    # Enforce single backbone mode and enable mgmt IP allocation
    monkeypatch.setenv("ENSURE_SINGLE_BACKBONE_GATEWAY", "1")
    monkeypatch.setenv("ALLOW_BACKBONE_MGMT_IP", "1")

    # First BB should succeed and auto-create mgmt interface with IP
    r = client.post(
        "/api/devices",
        json={
            "id": "bb1",
            "name": "bb1",
            "type": "BACKBONE_GATEWAY",
            "status": "UP",
        },
    )
    assert r.status_code == 201
    # Check mgmt interface existence
    with get_session() as s:
        mgmt = s.get(Interface, "bb1-mgmt0")
        assert mgmt is None or mgmt.role == "management"

    # Second BB should be rejected with 409 due to single mode
    r2 = client.post(
        "/api/devices",
        json={
            "id": "bb2",
            "name": "bb2",
            "type": "BACKBONE_GATEWAY",
            "status": "UP",
        },
    )
    assert r2.status_code == 409


def test_get_and_delete_device_404s():
    client = TestClient(app)
    # 404 on non-existing get
    r = client.get("/api/devices/na")
    assert r.status_code == 404
    # 404 on non-existing delete
    r = client.delete("/api/devices/na")
    assert r.status_code == 404
