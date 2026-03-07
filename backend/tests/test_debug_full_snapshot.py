from __future__ import annotations

from fastapi.testclient import TestClient

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, DeviceType, Status
from backend.services.seed_service import ensure_default_tariffs


def _client() -> TestClient:
    return TestClient(app)


def test_debug_snapshot_404_when_disabled(monkeypatch):
    monkeypatch.setenv("UNOC_DEV_FEATURES", "0")
    c = _client()
    r = c.get("/api/debug/full-snapshot")
    assert r.status_code == 404


def test_debug_snapshot_tariffs_and_optical_present(monkeypatch):
    # Enable dev features
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    # Ensure tariffs exist
    init_db()
    with get_session() as s:
        ensure_default_tariffs(s)
        s.commit()

    c = _client()
    r = c.get("/api/debug/full-snapshot")
    assert r.status_code == 200
    body = r.json()
    assert "meta" in body
    # Tariffs section exists and is a list (may be empty if capped)
    assert "tariffs" in body
    assert isinstance(body["tariffs"], list)
    # Optical section exists with 'onts' list (empty ok)
    assert "optical" in body
    assert isinstance(body["optical"], dict)
    assert "onts" in body["optical"]
    assert isinstance(body["optical"]["onts"], list)


def test_debug_snapshot_sections_filter(monkeypatch):
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    c = _client()
    r = c.get("/api/debug/full-snapshot", params={"sections": "devices,tariffs", "pretty": True})
    assert r.status_code == 200
    body = r.json()
    # Only requested sections should be present among payload keys (meta is always present)
    keys = set(body.keys()) - {"meta"}
    assert keys == {"devices", "tariffs"}


def test_debug_snapshot_device_effective_status_override(monkeypatch):
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    init_db()
    with get_session() as s:
        d = Device(
            id="dev-override-1",
            name="dev-override-1",
            type=DeviceType.CORE_ROUTER,
            provisioned=True,
            status=Status.UP,  # stored
            admin_override_status=Status.DOWN,  # effective should be DOWN
        )
        s.add(d)
        s.commit()

    c = _client()
    r = c.get("/api/debug/full-snapshot", params={"sections": "devices"})
    assert r.status_code == 200
    devices = r.json()["devices"]
    row = next(x for x in devices if x["id"] == "dev-override-1")
    assert row["status"] == "UP"  # stored
    assert row["effective_status"] == "DOWN"  # computed
    assert row["admin_override_status"] == "DOWN"


def test_debug_snapshot_effective_status_unprovisioned_active(monkeypatch):
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    init_db()
    with get_session() as s:
        d = Device(
            id="dev-unprov-1",
            name="dev-unprov-1",
            type=DeviceType.EDGE_ROUTER,
            provisioned=False,
            status=Status.UP,  # stored may be UP by default
        )
        s.add(d)
        s.commit()

    c = _client()
    r = c.get("/api/debug/full-snapshot", params={"sections": "devices"})
    assert r.status_code == 200
    devices = r.json()["devices"]
    row = next(x for x in devices if x["id"] == "dev-unprov-1")
    # Active + not provisioned -> DOWN effective
    assert row["effective_status"] == "DOWN"
