from fastapi.testclient import TestClient

from backend.db import init_db
from backend.main import app


def test_health():
    client = TestClient(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_metadata():
    client = TestClient(app)
    r = client.get("/api/metadata")
    assert r.status_code == 200
    data = r.json()
    assert data["app"] == "UNOC"
    assert data["specRevision"] == "r4"
    assert "timestamp" in data


def test_layout_positions_patch():
    client = TestClient(app)
    r = client.patch(
        "/api/layout/positions",
        json={
            "version": None,
            "positions": [{"id": "n1", "x": 10.5, "y": -2.0, "userPinned": True}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["version"] >= 1
    assert body["applied"] == 1


def test_ports_summary_smoke_for_empty_device():
    # Use health client and create a dummy device via API, then query ports summary
    init_db()  # Initialize in-memory database
    client = TestClient(app)
    # Create a non-OLT device without hardware to avoid PON specifics
    r = client.post(
        "/api/devices",
        json={"id": "devx", "name": "devx", "type": "EDGE_ROUTER", "status": "UP"},
    )
    assert r.status_code in (200, 201)
    r2 = client.get("/api/ports/summary/devx")
    assert r2.status_code == 200
    data = r2.json()
    assert isinstance(data, list)
    # For an empty device with no hardware model, there may be zero interfaces
    # but shape must be a list of InterfaceSummaryOut when present.
    for item in data:
        assert set(item.keys()) >= {
            "id",
            "name",
            "port_role",
            "effective_status",
            "occupancy",
            "capacity",
        }
