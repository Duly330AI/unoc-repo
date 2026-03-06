from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.db import engine, init_db, reset_db
from backend.main import app
from backend.models import HardwareModel, PortProfile
from backend.services.catalog_service import load_catalog_dir


def _write_json(tmpdir: Path, rel: str, data: dict) -> Path:
    p = tmpdir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_catalog_loader_idempotent(tmp_path: Path):
    reset_db()
    init_db()
    # Create two simple entries
    data1 = {
        "catalog_id": "OLT_FAKE_V1",
        "device_type": "OLT",
        "vendor": "FakeCo",
        "model": "F-OLT-1",
        "version": "1.0",
        "attributes": {"tx_power_dbm": 5.0, "capacity_gbps": 40},
        "ports": [{"name": "uplink", "count": 2, "speed_gbps": 10, "role": "uplink"}],
        "meta": {"source": "test"},
    }
    data2 = {
        "catalog_id": "ONT_FAKE_V1",
        "device_type": "ONT",
        "vendor": "FakeCo",
        "model": "F-ONT-1",
        "version": "1.0",
        "attributes": {"sensitivity_min_dbm": -28.0},
        "ports": [{"name": "ge", "count": 1, "speed_gbps": 1, "role": "access", "media": "rj45"}],
        "meta": {"source": "test"},
    }
    _write_json(tmp_path, "hardware/olt/olt1.json", data1)
    _write_json(tmp_path, "hardware/ont/ont1.json", data2)

    with Session(engine) as s:
        n1 = load_catalog_dir(s, tmp_path)
        n2 = load_catalog_dir(s, tmp_path)  # idempotent second pass
        assert n1 == 2
        assert n2 == 2
        # Verify entries
        rows = s.exec(select(HardwareModel)).all()
        assert {r.catalog_id for r in rows} == {"OLT_FAKE_V1", "ONT_FAKE_V1"}
        # Verify port profiles
        for r in rows:
            pps = s.exec(select(PortProfile).where(PortProfile.hardware_model_id == r.id)).all()
            assert len(pps) >= 1


def test_api_endpoints_list_and_get(tmp_path: Path):
    reset_db()
    init_db()
    sample = {
        "catalog_id": "OLT_FAKE_V2",
        "device_type": "OLT",
        "vendor": "FakeCo",
        "model": "F-OLT-2",
        "version": "2.0",
        "attributes": {"tx_power_dbm": 6.0, "capacity_gbps": 80},
        "ports": [{"name": "uplink", "count": 4, "speed_gbps": 25, "role": "uplink"}],
    }
    _write_json(tmp_path, "hardware/olt/olt2.json", sample)
    with Session(engine) as s:
        load_catalog_dir(s, tmp_path)

    client = TestClient(app)
    # List
    r = client.get("/api/catalog/hardware?type=OLT")
    assert r.status_code == 200, r.text
    items = r.json()
    assert any(x["catalog_id"] == "OLT_FAKE_V2" for x in items)
    # Get single
    r2 = client.get("/api/catalog/hardware/OLT_FAKE_V2")
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["vendor"] == "FakeCo"
    assert body["device_type"] == "OLT"
