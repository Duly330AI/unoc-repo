from fastapi.testclient import TestClient

from backend.main import app
from backend.services.job_dispatcher import QUEUE, handle_batch
from backend.services.worker import Worker


def _mk_device(client: TestClient, id: str, type: str):
    r = client.post(
        "/api/devices",
        json={"id": id, "name": id, "type": type, "status": "UP"},
    )
    assert r.status_code == 201, r.text


def test_link_endpoints_must_differ_and_interface_missing():
    client = TestClient(app)
    _mk_device(client, "x1", "CORE_ROUTER")
    # endpoints must differ
    r = client.post(
        "/api/links",
        json={
            "id": "x1__x1",
            "a_interface_id": "x1-if0",
            "b_interface_id": "x1-if0",
            "status": "UP",
        },
    )
    assert r.status_code == 400

    # interface not found and not auto-creatable (no -if0 suffix)
    r2 = client.post(
        "/api/links",
        json={
            "id": "foo__bar",
            "a_interface_id": "foo-eth1",
            "b_interface_id": "bar-eth2",
            "status": "UP",
        },
    )
    assert r2.status_code == 400
    assert "Interface not found" in r2.text


def test_link_duplicate_create_and_list_and_delete():
    client = TestClient(app)
    _mk_device(client, "y1", "CORE_ROUTER")
    _mk_device(client, "y2", "EDGE_ROUTER")
    payload = {
        "id": "y1__y2",
        "a_interface_id": "y1-if0",
        "b_interface_id": "y2-if0",
        "status": "UP",
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 201
    # duplicate
    r2 = client.post("/api/links", json=payload)
    assert r2.status_code == 409

    # list should include the link
    r3 = client.get("/api/links")
    assert r3.status_code == 200
    arr = r3.json()
    assert any(item["id"] == "y1__y2" for item in arr)

    # delete
    r4 = client.delete("/api/links/y1__y2")
    assert r4.status_code == 202
    if QUEUE.size() > 0:
        Worker().run_once(QUEUE, handle_batch, max_items=256)
