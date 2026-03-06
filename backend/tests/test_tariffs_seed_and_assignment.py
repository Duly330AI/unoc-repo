from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import DeviceType, Tariff
from backend.services.seed_service import ensure_default_tariffs


def _client() -> TestClient:
    return TestClient(app)


def test_ensure_default_tariffs_idempotent():
    init_db()
    with get_session() as s:
        ensure_default_tariffs(s)
        s.commit()
        first_count = len(s.exec(select(Tariff)).all())
        ensure_default_tariffs(s)
        s.commit()
        second_count = len(s.exec(select(Tariff)).all())
        assert second_count == first_count


def test_device_create_auto_assigns_tariff_by_technology():
    c = _client()
    # Create ONT and expect GPON tariff assigned
    r = c.post(
        "/api/devices",
        json={"id": "ont-1", "name": "ONT 1", "type": DeviceType.ONT.value},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["tariff_id"] is not None
    # Create AON_CPE and expect AON tariff assigned
    r = c.post(
        "/api/devices",
        json={"id": "aoncpe-1", "name": "AON CPE 1", "type": DeviceType.AON_CPE.value},
    )
    assert r.status_code == 201
    body2 = r.json()
    assert body2["tariff_id"] is not None
