"""Hard EventStore bypass guard validation (UNOC_EVENTSTORE_ENFORCE=1).

Proves that with enforcement enabled:
- direct DB mutations of guarded models fail with EVENT_STORE_BYPASS
- writes inside projection_write_context succeed
- the covered API mutation surfaces keep working and record write-path events
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

import backend.db as db
from backend.main import app
from backend.models import Device, DeviceType, EventStoreRecord, Status
from backend.services.event_store_runtime import projection_write_context

client = TestClient(app)


@pytest.fixture()
def enforcement_enabled(monkeypatch):
    monkeypatch.setenv("UNOC_EVENTSTORE_ENFORCE", "1")
    yield


def test_direct_bypass_write_blocked(enforcement_enabled):
    with db.get_session() as s:
        s.add(
            Device(id="bypass_dev", name="bypass", type=DeviceType.CORE_ROUTER, status=Status.UP)
        )
        with pytest.raises(RuntimeError, match="EVENT_STORE_BYPASS"):
            s.commit()
        s.rollback()
    with db.get_session() as s:
        assert s.get(Device, "bypass_dev") is None


def test_projection_context_write_allowed(enforcement_enabled):
    with projection_write_context(), db.get_session() as s:
        s.add(Device(id="ctx_dev", name="ctx", type=DeviceType.CORE_ROUTER, status=Status.UP))
        s.commit()
    with db.get_session() as s:
        assert s.get(Device, "ctx_dev") is not None


def test_api_mutations_work_under_enforcement(enforcement_enabled):
    r = client.post(
        "/api/devices",
        json={"id": "enf_core", "name": "enf_core", "type": "CORE_ROUTER", "status": "UP"},
    )
    assert r.status_code == 201, r.text

    r = client.put("/api/devices/enf_core", json={"name": "enf_core_renamed"})
    assert r.status_code == 200, r.text

    r = client.post("/api/devices/enf_core/provision")
    assert r.status_code == 200, r.text

    with db.get_session() as s:
        write_path_count = len(
            s.exec(select(EventStoreRecord).where(EventStoreRecord.source == "WRITE_PATH")).all()
        )
    assert write_path_count > 0

    r = client.delete("/api/devices/enf_core")
    assert r.status_code == 204, r.text


def test_link_lifecycle_under_enforcement(enforcement_enabled):
    for dev_id, dev_type in (("enf_gw", "BACKBONE_GATEWAY"), ("enf_rtr", "CORE_ROUTER")):
        r = client.post(
            "/api/devices",
            json={"id": dev_id, "name": dev_id, "type": dev_type, "status": "UP"},
        )
        assert r.status_code == 201, r.text

    r = client.post(
        "/api/links",
        json={
            "id": "enf_gw__enf_rtr",
            "a_interface_id": "enf_gw-if0",
            "b_interface_id": "enf_rtr-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r.status_code == 201, r.text
