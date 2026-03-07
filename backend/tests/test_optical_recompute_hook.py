import logging

from fastapi.testclient import TestClient

from backend.db import init_db
from backend.main import app

client = TestClient(app)


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):  # type: ignore
        self.records.append(record)


def _provision(device_type: str, dev_id: str, do_provision: bool = True):
    payload = {"id": dev_id, "name": dev_id, "type": device_type, "status": "DOWN"}
    # Provide required parent for OLT (POP container)
    if device_type == "OLT":
        # Create POP if not exists
        if client.get("/api/devices/pop1").status_code == 404:
            pr = client.post(
                "/api/devices",
                json={
                    "id": "pop1",
                    "name": "pop1",
                    "type": "POP",
                    "status": "DOWN",
                },
            )
            assert pr.status_code == 201, pr.text
        payload["parent_container_id"] = "pop1"
    r = client.post("/api/devices", json=payload)
    assert r.status_code == 201, r.text
    provisionable = {
        "CORE_ROUTER",
        "EDGE_ROUTER",
        "OLT",
        "AON_SWITCH",
        "ONT",
        "BUSINESS_ONT",
        "AON_CPE",
    }
    if do_provision and device_type in provisionable:
        pr = client.post(f"/api/devices/{dev_id}/provision")
        assert pr.status_code == 200, pr.text


def test_optical_hook_triggers_for_optical_device_types(monkeypatch):
    init_db()
    # Attach log handler to capture optical service log
    handler = ListHandler()
    logger = logging.getLogger("unoc.optical")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        # Provision core router prerequisite
        _provision("CORE_ROUTER", "core1")
        # POP container for OLT (non-provisioned passive/container)
        _provision("POP", "pop1")
        # Create OLT device first (no provision), then ensure logical adjacency core<->olt for strict path validation and provision
        _provision("OLT", "d_olt", do_provision=False)
        client.post(
            "/api/links",
            json={
                "id": "core1__d_olt",
                "a_interface_id": "core1-if0",
                "b_interface_id": "d_olt-if0",
                "status": "UP",
                "kind": "FIBER",
            },
        )
        pr = client.post("/api/devices/d_olt/provision")
        assert pr.status_code == 200, pr.text
        # Create ONT device first (no provision); then create optical links via ODF and provision ONT
        _provision("ONT", "d_ont", do_provision=False)
        # Insert ODF per Phase 1 rules
        _provision("ODF", "d_odf", do_provision=False)
        # Create OLT<->ODF and ODF<->ONT fiber links
        client.post(
            "/api/links",
            json={
                "id": "d_olt__d_odf",
                "a_interface_id": "d_olt-if0",
                "b_interface_id": "d_odf-if0",
                "status": "UP",
                "kind": "FIBER",
                "length_km": 5.0,
            },
        )
        client.post(
            "/api/links",
            json={
                "id": "d_odf__d_ont",
                "a_interface_id": "d_ont-if0",
                "b_interface_id": "d_odf-if0",
                "status": "UP",
                "kind": "FIBER",
                "length_km": 0.0,
            },
        )
        pr2 = client.post("/api/devices/d_ont/provision")
        assert pr2.status_code == 200, pr2.text
        msgs = "\n".join(r.getMessage() for r in handler.records)
        assert "Optical recomputation triggered" in msgs
        for suffix in ["olt", "ont"]:
            assert f"d_{suffix}" in msgs
    finally:
        logger.removeHandler(handler)
