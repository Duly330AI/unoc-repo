from fastapi.testclient import TestClient

from backend.events import get_event_history, reset_events
from backend.main import app
from backend.models import Status


def test_list_devices_without_interfaces_and_get_404_delete_404():
    client = TestClient(app)
    # Create one device
    r = client.post(
        "/api/devices",
        json={
            "id": "d1",
            "name": "d1",
            "type": "CORE_ROUTER",
            "status": "UP",
            "parent_container_id": None,
        },
    )
    assert r.status_code == 201
    # List without interfaces param -> no 'interfaces' field present
    r = client.get("/api/devices")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) == 1
    # When not requested, interfaces should be absent or null
    assert items[0].get("interfaces") is None
    # Get unknown
    r = client.get("/api/devices/does-not-exist")
    assert r.status_code == 404
    # Delete unknown
    r = client.delete("/api/devices/does-not-exist")
    assert r.status_code == 404


def test_update_device_emits_status_changed_on_admin_override():
    client = TestClient(app)
    reset_events()
    # Create device
    r = client.post(
        "/api/devices",
        json={
            "id": "d2",
            "name": "d2",
            "type": "EDGE_ROUTER",
            "status": "UP",
            "parent_container_id": None,
        },
    )
    assert r.status_code == 201
    # Update with admin override -> should emit device.status.changed event
    r = client.put(
        "/api/devices/d2",
        json={
            "admin_override_status": Status.DOWN.value,
        },
    )
    assert r.status_code == 200
    events = get_event_history()
    assert any(e.type == "device.status.changed" and e.payload.get("id") == "d2" for e in events)
