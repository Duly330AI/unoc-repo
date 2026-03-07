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


def _mk_device(client: TestClient, dev_id: str, dev_type: str):
    r = client.post(
        "/api/devices",
        json={"id": dev_id, "name": dev_id, "type": dev_type, "status": "UP"},
    )
    assert r.status_code == 201, r.text


def test_link_crud_status_recompute_does_not_emit_status_change_in_phase1():
    client = TestClient(app)
    cap = CaptureBroadcaster()
    set_broadcaster(cap)

    # Create devices (gw always_online -> UP, core active -> DOWN until provisioned)
    _mk_device(client, "gwX", "BACKBONE_GATEWAY")
    _mk_device(client, "coreX", "CORE_ROUTER")

    # Create link between them
    r = client.post(
        "/api/links",
        json={
            "id": "gwX__coreX",
            "a_interface_id": "gwX-if0",
            "b_interface_id": "coreX-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r.status_code == 201, r.text

    # Delete link
    r2 = client.delete("/api/links/gwX__coreX")
    assert r2.status_code == 202
    if QUEUE.size() > 0:
        Worker().run_once(QUEUE, handle_batch, max_items=256)

    # In Phase 1, device dynamic status does not depend on links,
    # so no device.status.changed should be emitted by link CRUD hooks.
    kinds = [e.type for e in cap.events]
    assert kinds.count("link.created") == 1
    assert kinds.count("link.deleted") == 1
    assert kinds.count("device.status.changed") == 0
