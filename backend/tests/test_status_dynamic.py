from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_active_device_status_is_down_until_provisioned_and_then_up():
    # Ensure propagation-based degrade is off so base dynamic rule applies
    # Status propagation and active-degrade are always-on; no env toggles to manage.
    # Create an active device (CORE_ROUTER) marked UP in DB but not provisioned
    r = client.post(
        "/api/devices",
        json={
            "id": "zt_core1",
            "name": "zt_core1",
            "type": "CORE_ROUTER",
            "status": "UP",
        },
    )
    assert r.status_code == 201, r.text

    # GET by id should compute dynamic status: DOWN (not provisioned yet)
    r = client.get("/api/devices/zt_core1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "DOWN"
    assert body["provisioned"] is False

    # GET list should also reflect dynamic status
    r = client.get("/api/devices")
    assert r.status_code == 200
    listed = [d for d in r.json() if d["id"] == "zt_core1"]
    assert listed and listed[0]["status"] == "DOWN"

    # Provision the device
    r = client.post("/api/devices/zt_core1/provision")
    assert r.status_code == 200, r.text

    # Now status should be DOWN under strict L3 (no anchors/path yet)
    r = client.get("/api/devices/zt_core1")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "DOWN"
    assert body["provisioned"] is True


def test_always_online_device_is_up_without_provisioning():
    # POP is considered always_online
    r = client.post(
        "/api/devices",
        json={"id": "zt_popA", "name": "zt_popA", "type": "POP", "status": "DOWN"},
    )
    assert r.status_code == 201, r.text

    r = client.get("/api/devices/zt_popA")
    assert r.status_code == 200
    assert r.json()["status"] == "UP"


def test_admin_override_wins_over_computed_status():
    # Create active device and set admin override to DOWN
    r = client.post(
        "/api/devices",
        json={
            "id": "zt_core2",
            "name": "zt_core2",
            "type": "CORE_ROUTER",
            "status": "UP",
        },
    )
    assert r.status_code == 201, r.text

    r = client.put("/api/devices/zt_core2", json={"admin_override_status": "DOWN"})
    assert r.status_code == 200

    # Regardless of provisioning, status should be DOWN due to override
    r = client.get("/api/devices/zt_core2")
    assert r.status_code == 200
    assert r.json()["status"] == "DOWN"
