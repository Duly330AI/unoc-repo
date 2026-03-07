from fastapi.testclient import TestClient

from backend.main import app
from backend.services.job_dispatcher import QUEUE, handle_batch
from backend.services.worker import Worker

client = TestClient(app)


def _mk_device(dev_id: str, dev_type: str):
    r = client.post(
        "/api/devices",
        json={"id": dev_id, "name": dev_id, "type": dev_type, "status": "UP"},
    )
    assert r.status_code == 201, r.text


def _mk_link(link_id: str, a_if: str, b_if: str):
    r = client.post(
        "/api/links",
        json={
            "id": link_id,
            "a_interface_id": a_if,
            "b_interface_id": b_if,
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r.status_code == 201, r.text


def test_async_link_override_enqueue_and_202():
    # Async writes are permanently enabled; no flag monkeypatch required

    # Create minimal topology
    _mk_device("gwA", "BACKBONE_GATEWAY")
    _mk_device("coreA", "CORE_ROUTER")
    _mk_link("gwA__coreA", "gwA-if0", "coreA-if0")

    # Clear queue in case of prior state
    while QUEUE.size() > 0:
        Worker().run_once(QUEUE, handle_batch, max_items=1024)

    # Issue async override (202 accepted + job queued)
    r = client.patch(
        "/api/links/gwA__coreA/override",
        json={"admin_override_status": "DOWN"},
    )
    assert r.status_code == 202, r.text
    payload = r.json()
    assert payload.get("accepted") is True
    assert isinstance(payload.get("job_id"), str)

    # Ensure a job is queued and can be processed
    assert QUEUE.size() >= 1
    processed = Worker().run_once(QUEUE, handle_batch, max_items=256)
    assert processed >= 1

    # After processing, the override should be persisted and visible via GET
    r2 = client.get("/api/links/gwA__coreA")
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data.get("admin_override_status") == "DOWN"
    # Effective status should reflect the override (DOWN or compatible classification)
    assert data.get("effective_status") in ("DOWN", "DEGRADED")
