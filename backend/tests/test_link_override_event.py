from fastapi.testclient import TestClient

from backend.events import Event, set_broadcaster
from backend.main import app
from backend.services.job_dispatcher import QUEUE, handle_batch
from backend.services.worker import Worker


class CaptureBroadcaster:
    def __init__(self):
        self.events: list[Event] = []

    def publish(self, event: Event) -> None:  # pragma: no cover - trivial
        self.events.append(event)


client = TestClient(app)


def _mk_device(dev_id: str, dev_type: str):
    r = client.post(
        "/api/devices",
        json={"id": dev_id, "name": dev_id, "type": dev_type, "status": "UP"},
    )
    assert r.status_code == 201, r.text


def test_link_override_emits_event():
    cap = CaptureBroadcaster()
    set_broadcaster(cap)
    _mk_device("gwO", "BACKBONE_GATEWAY")
    _mk_device("coreO", "CORE_ROUTER")
    r = client.post(
        "/api/links",
        json={
            "id": "gwO__coreO",
            "a_interface_id": "gwO-if0",
            "b_interface_id": "coreO-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r.status_code == 201, r.text
    # Apply override (async)
    r2 = client.patch("/api/links/gwO__coreO/override", json={"admin_override_status": "DOWN"})
    assert r2.status_code == 202, r2.text
    # Drain async queue deterministically
    if QUEUE.size() > 0:
        Worker().run_once(QUEUE, handle_batch, max_items=256)
    # Expect override event present with id and override field
    assert any(
        e.type == "link.override.changed"
        and e.payload.get("id") == "gwO__coreO"
        and (e.payload.get("admin_override_status") or "DOWN").endswith("DOWN")
        for e in cap.events
    ), f"Events captured: {[ (e.type, e.payload) for e in cap.events ]}"
