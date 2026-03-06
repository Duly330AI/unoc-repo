from fastapi.testclient import TestClient

from backend.main import app


def test_list_devices_with_interfaces():
    client = TestClient(app)
    r = client.post(
        "/api/devices",
        json={"id": "d1", "name": "d1", "type": "CORE_ROUTER", "status": "UP"},
    )
    assert r.status_code == 201
    r = client.get("/api/devices?include_interfaces=true")
    assert r.status_code == 200
    data = r.json()
    d = next(d for d in data if d["id"] == "d1")
    assert isinstance(d.get("interfaces"), list)
    assert any(i["id"] == "d1-if0" for i in d["interfaces"])
