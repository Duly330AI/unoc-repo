import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from backend.main import app
from backend.models import Device, Interface, InterfaceAddress


@pytest.fixture
def client():
    # Create TestClient after per-test engine fixture has patched backend.db
    return TestClient(app)


def test_single_backbone_creation_guard(monkeypatch, client):
    monkeypatch.setenv("ENSURE_SINGLE_BACKBONE_GATEWAY", "true")
    # Create initial backbone via API
    first = client.post(
        "/api/devices",
        json={
            "id": "backbone_gateway",
            "name": "Backbone Gateway",
            "type": "BACKBONE_GATEWAY",
            "status": "UP",
        },
    )
    assert first.status_code in {200, 201}, first.text
    # Attempt to create second backbone
    resp = client.post(
        "/api/devices",
        json={"id": "bb2", "name": "BB2", "type": "BACKBONE_GATEWAY", "status": "UP"},
    )
    assert resp.status_code == 409, resp.text
    assert "already exists" in resp.text


def test_optional_backbone_mgmt_ip_flag(monkeypatch, client):
    monkeypatch.setenv("ENSURE_SINGLE_BACKBONE_GATEWAY", "true")
    monkeypatch.setenv("ALLOW_BACKBONE_MGMT_IP", "true")
    resp = client.post(
        "/api/devices",
        json={
            "id": "backbone_gateway",
            "name": "Backbone Gateway",
            "type": "BACKBONE_GATEWAY",
            "status": "UP",
        },
    )
    assert resp.status_code in {200, 201}, resp.text
    from backend.db import get_session

    with get_session() as session:
        bb = session.get(Device, "backbone_gateway")
        assert bb is not None
        mgmt_iface = session.get(Interface, "backbone_gateway-mgmt0")
        assert mgmt_iface is not None
        addrs = session.exec(
            select(InterfaceAddress).where(InterfaceAddress.interface_id == mgmt_iface.id)
        ).all()
        assert len(addrs) >= 1


def test_backbone_without_mgmt_ip(monkeypatch, client):
    monkeypatch.setenv("ENSURE_SINGLE_BACKBONE_GATEWAY", "true")
    monkeypatch.setenv("ALLOW_BACKBONE_MGMT_IP", "false")
    resp = client.post(
        "/api/devices",
        json={
            "id": "backbone_gateway",
            "name": "Backbone Gateway",
            "type": "BACKBONE_GATEWAY",
            "status": "UP",
        },
    )
    assert resp.status_code in {200, 201}, resp.text
    from backend.db import get_session

    with get_session() as session:
        mgmt_iface = session.get(Interface, "backbone_gateway-mgmt0")
        assert mgmt_iface is None
