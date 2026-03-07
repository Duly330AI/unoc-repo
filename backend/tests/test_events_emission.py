from fastapi.testclient import TestClient

from backend.events import Event, set_broadcaster
from backend.main import app
from backend.services.job_dispatcher import QUEUE, handle_batch
from backend.services.worker import Worker


class CaptureBroadcaster:
    def __init__(self):
        self.events: list[Event] = []

    def publish(self, event: Event) -> None:  # pragma: no cover
        self.events.append(event)


client = TestClient(app)


def _mk_device(dev_id: str, dev_type: str):
    r = client.post(
        "/api/devices",
        json={"id": dev_id, "name": dev_id, "type": dev_type, "status": "UP"},
    )
    assert r.status_code == 201, r.text


def test_device_provision_emits_event():
    cap = CaptureBroadcaster()
    set_broadcaster(cap)
    _mk_device("coreX", "CORE_ROUTER")
    r = client.post("/api/devices/coreX/provision")
    assert r.status_code == 200, r.text
    # Expect a device.provisioned event
    assert any(e.type == "device.provisioned" and e.payload["id"] == "coreX" for e in cap.events)


def test_link_create_delete_emits_events():
    cap = CaptureBroadcaster()
    set_broadcaster(cap)
    _mk_device("gw1", "BACKBONE_GATEWAY")
    _mk_device("core1", "CORE_ROUTER")
    r = client.post(
        "/api/links",
        json={
            "id": "gw1__core1",
            "a_interface_id": "gw1-if0",
            "b_interface_id": "core1-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r.status_code == 201, r.text
    assert any(e.type == "link.created" and e.payload["id"] == "gw1__core1" for e in cap.events)
    r2 = client.delete("/api/links/gw1__core1")
    assert r2.status_code == 202
    # Drain async queue
    if QUEUE.size() > 0:
        Worker().run_once(QUEUE, handle_batch, max_items=256)
    assert any(e.type == "link.deleted" and e.payload["id"] == "gw1__core1" for e in cap.events)


def test_device_status_change_emits_event():
    cap = CaptureBroadcaster()
    set_broadcaster(cap)
    _mk_device("coreZ", "CORE_ROUTER")
    # update with admin override down
    r = client.put(
        "/api/devices/coreZ",
        json={"admin_override_status": "DOWN"},
    )
    assert r.status_code == 200, r.text
    assert any(e.type == "device.status.changed" and e.payload["id"] == "coreZ" for e in cap.events)
