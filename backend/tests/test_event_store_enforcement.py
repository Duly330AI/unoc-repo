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
from backend.models import (
    Device,
    DeviceType,
    EventStoreRecord,
    Interface,
    Link,
    ProvisioningRecord,
    Status,
)
from backend.services.event_store_runtime import projection_write_context
from backend.services.job_dispatcher import QUEUE, handle_batch
from backend.services.worker import Worker

client = TestClient(app)

TEMP_DEVICE_IDS = {
    "bypass_dev",
    "ctx_dev",
    "enf_core",
    "enf_gw",
    "enf_rtr",
}
TEMP_LINK_IDS = {"enf_gw__enf_rtr", "enf_rtr__enf_gw"}


@pytest.fixture()
def enforcement_enabled(monkeypatch):
    monkeypatch.setenv("UNOC_EVENTSTORE_ENFORCE", "1")
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    yield


@pytest.fixture(autouse=True)
def cleanup_temp_entities():
    _cleanup_temp_entities()
    yield
    _drain_jobs()
    _cleanup_temp_entities()


def _cleanup_temp_entities() -> None:
    with projection_write_context(), db.get_session() as s:
        interface_ids: set[str] = set()
        for device_id in TEMP_DEVICE_IDS:
            interface_ids.update(
                iface.id
                for iface in s.exec(select(Interface).where(Interface.device_id == device_id))
            )

        for link in s.exec(select(Link)).all():
            if (
                link.id in TEMP_LINK_IDS
                or link.a_interface_id in interface_ids
                or link.b_interface_id in interface_ids
            ):
                s.delete(link)

        for provision in s.exec(select(ProvisioningRecord)).all():
            if provision.device_id in TEMP_DEVICE_IDS or provision.interface_id in interface_ids:
                s.delete(provision)

        for interface_id in sorted(interface_ids):
            interface = s.get(Interface, interface_id)
            if interface is not None:
                s.delete(interface)

        for device_id in sorted(TEMP_DEVICE_IDS):
            device = s.get(Device, device_id)
            if device is not None:
                s.delete(device)

        s.commit()


def _drain_jobs() -> None:
    while QUEUE.size() > 0:
        Worker().run_once(QUEUE, handle_batch, max_items=256)


def _last_event_sequence() -> int:
    with db.get_session() as s:
        sequence = s.exec(
            select(EventStoreRecord.sequence).order_by(EventStoreRecord.sequence.desc()).limit(1)
        ).first()
    return int(-1 if sequence is None else sequence)


def _has_write_path_event(event_type: str, entity_id: str, *, after_sequence: int) -> bool:
    with db.get_session() as s:
        records = s.exec(
            select(EventStoreRecord)
            .where(EventStoreRecord.source == "WRITE_PATH")
            .where(EventStoreRecord.event_type == event_type)
            .where(EventStoreRecord.sequence > after_sequence)
        ).all()
    return any((record.payload or {}).get("entity_id") == entity_id for record in records)


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
    before = _last_event_sequence()
    r = client.post(
        "/api/devices",
        json={"id": "enf_core", "name": "enf_core", "type": "CORE_ROUTER", "status": "UP"},
    )
    assert r.status_code == 201, r.text
    assert _has_write_path_event("DEVICE_CREATED", "enf_core", after_sequence=before)
    with db.get_session() as s:
        assert s.get(Device, "enf_core") is not None

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
    assert _has_write_path_event("DEVICE_DELETED", "enf_core", after_sequence=before)
    with db.get_session() as s:
        assert s.get(Device, "enf_core") is None


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
    assert _has_write_path_event("LINK_CREATED", "enf_gw__enf_rtr", after_sequence=-1)
    with db.get_session() as s:
        assert s.get(Link, "enf_gw__enf_rtr") is not None

    before_delete = _last_event_sequence()
    r = client.delete("/api/links/enf_gw__enf_rtr")
    assert r.status_code == 202, r.text
    _drain_jobs()
    assert _has_write_path_event("LINK_DELETED", "enf_gw__enf_rtr", after_sequence=before_delete)
    with db.get_session() as s:
        assert s.get(Link, "enf_gw__enf_rtr") is None


def test_event_store_health_reports_python_authoritative_status(enforcement_enabled):
    r = client.get("/api/debug/event-store-health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enforcement_enabled"] is True
    assert body["guarded_entities"] == ["Device", "Interface", "Link", "ProvisioningRecord"]
    assert body["go_guarded_write_status"]["status"] == "no_active_guarded_go_writes"
    assert (
        body["consistency_status"]
        == "authoritative_for_python_guarded_paths_go_not_guarded_but_no_guarded_go_writes"
    )
    assert body["projection_lag"] == 0
    assert "covered_write_paths" in body
    assert "excluded_internal_paths" in body
    assert "remaining_blockers" in body
