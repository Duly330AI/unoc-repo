from fastapi.testclient import TestClient

from backend import events
from backend.db import init_db
from backend.main import app

client = TestClient(app)


def _create_device(dev_id: str, dev_type: str, parent: str | None = None, provision: bool = True):
    payload = {"id": dev_id, "name": dev_id, "type": dev_type, "status": "DOWN"}
    if parent:
        payload["parent_container_id"] = parent
    r = client.post("/api/devices", json=payload)
    assert r.status_code == 201, r.text
    if provision and dev_type in {
        "CORE_ROUTER",
        "OLT",
        "ONT",
        "BUSINESS_ONT",
        "AON_SWITCH",
        "EDGE_ROUTER",
        "AON_CPE",
    }:
        pr = client.post(f"/api/devices/{dev_id}/provision")
        assert pr.status_code == 200, pr.text


def test_optical_event_emitted_on_link_create_and_delete():
    init_db()
    events.reset_events()
    # Core + POP + OLT + ODF + ONT via ODF (no direct OLT↔ONT)
    _create_device("coreX", "CORE_ROUTER")
    _create_device("popX", "POP")
    # Create OLT device but defer provisioning until link exists
    _create_device("oltX", "OLT", parent="popX", provision=False)
    _create_device("odfX", "ODF")
    # Ensure logical adjacency core<->olt for strict path validation
    client.post(
        "/api/links",
        json={
            "id": "coreX__oltX",
            "a_interface_id": "coreX-if0",
            "b_interface_id": "oltX-if0",
            "status": "UP",
            "kind": "FIBER",
        },
    )
    # Now provision OLT
    pr = client.post("/api/devices/oltX/provision")
    assert pr.status_code == 200, pr.text
    _create_device("ontX", "ONT", provision=False)
    # Create OLT↔ODF link
    link_id_olt_odf = "odfX__oltX" if "odfX" < "oltX" else "oltX__odfX"
    lr1 = client.post(
        "/api/links",
        json={
            "id": link_id_olt_odf,
            "a_interface_id": "oltX-if0",
            "b_interface_id": "odfX-if0",
            "status": "UP",
            "kind": "FIBER",
        },
    )
    assert lr1.status_code == 201, lr1.text
    # Create ODF↔ONT link
    link_id_odf_ont = "odfX__ontX" if "odfX" < "ontX" else "ontX__odfX"
    lr2 = client.post(
        "/api/links",
        json={
            "id": link_id_odf_ont,
            "a_interface_id": "odfX-if0",
            "b_interface_id": "ontX-if0",
            "status": "UP",
            "kind": "FIBER",
        },
    )
    assert lr2.status_code == 201, lr2.text
    # Provision ONT only after optical link exists to satisfy strict path validation
    pr2 = client.post("/api/devices/ontX/provision")
    assert pr2.status_code == 200, pr2.text
    hist = events.get_event_history()
    assert any(
        e.type == "device.optical.updated" and e.payload.get("reason") == "link_created"
        for e in hist
    )
    # Delete link (now async)
    dr = client.delete(f"/api/links/{link_id_odf_ont}")
    assert dr.status_code == 202, dr.text
    # Drain async deletion to ensure events are published before checking history
    from backend.services.job_dispatcher import QUEUE, handle_batch
    from backend.services.worker import Worker

    if QUEUE.size() > 0:
        Worker().run_once(QUEUE, handle_batch, max_items=256)
    hist2 = events.get_event_history()
    # At least one delete-triggered optical event present
    assert any(
        e.type == "device.optical.updated" and e.payload.get("reason") == "link_deleted"
        for e in hist2
    )
