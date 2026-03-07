from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_device_crud_cycle():
    # create
    r = client.post(
        "/api/devices",
        json={"id": "d1", "name": "POP-1", "type": "POP", "status": "UP"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] == "d1"
    # list
    r = client.get("/api/devices")
    assert r.status_code == 200
    devices = r.json()
    assert any(d["id"] == "d1" for d in devices)
    # get
    r = client.get("/api/devices/d1")
    assert r.status_code == 200
    # update
    r = client.put("/api/devices/d1", json={"name": "POP-1A"})
    assert r.status_code == 200
    assert r.json()["name"] == "POP-1A"
    # delete
    r = client.delete("/api/devices/d1")
    assert r.status_code == 204
    # confirm gone
    r = client.get("/api/devices/d1")
    assert r.status_code == 404
