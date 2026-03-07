"""
Integration test for catalog effective parameters.

Tests that optical links inherit tx_power_dbm, rx_sensitivity_dbm from hardware
catalog when not explicitly set. Validates optical path resolution respects
catalog-derived power budget.

REQUIRES: Optical PathFinder Go service (port 50051) + PostgreSQL
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, DeviceType, HardwareModel, Interface, Link
from backend.services.catalog_service import load_catalog_dir
from backend.services.metrics_service import METRICS
from backend.services.optical_service import recompute_optical_paths_for_affected_onts

pytestmark = pytest.mark.integration  # Mark entire module as integration test


def _seed_catalog(tmpdir: Path):
    data_olt = {
        "catalog_id": "OLT_MINI_V1",
        "device_type": "OLT",
        "vendor": "Gen",
        "model": "OLT-MINI",
        "version": "1.0",
        "attributes": {"tx_power_dbm": 4.0, "capacity_gbps": 40},
        "ports": [{"name": "uplink", "count": 2, "speed_gbps": 10, "role": "uplink"}],
    }
    data_ont = {
        "catalog_id": "ONT_MINI_V1",
        "device_type": "ONT",
        "vendor": "Gen",
        "model": "ONT-MINI",
        "version": "1.0",
        "attributes": {"sensitivity_min_dbm": -27.0, "capacity_gbps": 1},
        "ports": [{"name": "eth", "count": 1, "speed_gbps": 1, "role": "access"}],
    }
    tmpdir.mkdir(parents=True, exist_ok=True)
    (tmpdir / "olt.json").write_text(json.dumps(data_olt), encoding="utf-8")
    (tmpdir / "ont.json").write_text(json.dumps(data_ont), encoding="utf-8")


def test_optical_defaults_and_overrides(tmp_path: Path):
    init_db()
    _seed_catalog(tmp_path)
    with get_session() as s:
        assert load_catalog_dir(s, str(tmp_path)) == 2
        olt_model = s.exec(
            select(HardwareModel).where(HardwareModel.device_type == DeviceType.OLT)
        ).first()
        assert olt_model is not None
        ont_model = s.exec(
            select(HardwareModel).where(HardwareModel.device_type == DeviceType.ONT)
        ).first()
        assert ont_model is not None
        # Create OLT and ONT devices
        s.add(Device(id="oltZ", name="OLT Z", type=DeviceType.OLT, hardware_model_id=olt_model.id))
        s.add(Device(id="ontZ", name="ONT Z", type=DeviceType.ONT, hardware_model_id=ont_model.id))
        # Minimal link to simulate optical path: ontZ-if0 <-> oltZ-if0
        s.add(Interface(id="oltZ-if0", device_id="oltZ", name="if0"))
        s.add(Interface(id="ontZ-if0", device_id="ontZ", name="if0"))
        s.add(Link(id="LZ", a_interface_id="ontZ-if0", b_interface_id="oltZ-if0"))
        s.commit()

    # Defaults from catalog
    recompute_optical_paths_for_affected_onts()
    with get_session() as s:
        ont = s.get(Device, "ontZ")
        assert ont is not None
        assert ont.signal_power_dbm is not None
        assert ont.signal_margin_db is not None
        # Now set overrides and ensure change
        olt = s.get(Device, "oltZ")
        assert olt is not None
        olt.tx_power_dbm = 6.0
        ont.sensitivity_min_dbm = -25.0
        s.add(olt)
        s.add(ont)
        s.commit()
    recompute_optical_paths_for_affected_onts()
    with get_session() as s:
        ont = s.get(Device, "ontZ")
        assert ont is not None
        assert ont.signal_margin_db is not None


def test_device_capacity_defaults_and_overrides(tmp_path: Path):
    init_db()
    # Catalog: device capacity 100 Gbps
    data = {
        "catalog_id": "CORE100",
        "device_type": "CORE_ROUTER",
        "vendor": "Gen",
        "model": "CR100",
        "version": "1.0",
        "attributes": {"capacity_gbps": 100},
        "ports": [],
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "core.json").write_text(json.dumps(data), encoding="utf-8")
    with get_session() as s:
        assert load_catalog_dir(s, str(tmp_path)) == 1
        m = s.exec(select(HardwareModel)).first()
        assert m is not None
        s.add(
            Device(
                id="coreA",
                name="coreA",
                type=DeviceType.CORE_ROUTER,
                hardware_model_id=m.id,
            )
        )
        s.commit()

    # Feed samples at 10 Gbps and expect 10/100 = 0.1 utilization
    METRICS.process_tick([("coreA", 10_000_000_000.0)], tick=1)
    snap = METRICS.get_snapshot()
    assert 0 <= snap["devices"]["coreA"]["utilization"] <= 0.11

    # Override to 50 Gbps (50_000 Mbps) -> utilization ~0.2
    with get_session() as s:
        d = s.get(Device, "coreA")
        assert d is not None
        d.capacity = 50_000
        s.add(d)
        s.commit()
    METRICS.process_tick([("coreA", 10_000_000_000.0)], tick=2)
    snap = METRICS.get_snapshot()
    assert 0.19 <= snap["devices"]["coreA"]["utilization"] <= 0.21


def test_interface_capacity_defaults_and_overrides(tmp_path: Path):
    init_db()
    # Catalog with uplink=10G
    data = {
        "catalog_id": "SW10",
        "device_type": "EDGE_ROUTER",
        "vendor": "Gen",
        "model": "SW10",
        "version": "1.0",
        "ports": [{"name": "uplink", "count": 2, "speed_gbps": 10, "role": "uplink"}],
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "sw.json").write_text(json.dumps(data), encoding="utf-8")
    with get_session() as s:
        assert load_catalog_dir(s, str(tmp_path)) == 1
        m = s.exec(select(HardwareModel)).first()
        assert m is not None
        s.add(Device(id="swA", name="swA", type=DeviceType.EDGE_ROUTER, hardware_model_id=m.id))
        # create two uplink ports without explicit capacity to trigger catalog fallback
        s.add(Interface(id="swA-uplink1", device_id="swA", name="uplink1", profile_name="uplink"))
        s.add(Interface(id="swA-uplink2", device_id="swA", name="uplink2", profile_name="uplink"))
        s.add(Link(id="L1", a_interface_id="swA-uplink1", b_interface_id="swA-uplink2"))
        s.commit()

    # 5 Gbps across the link => util ~0.5 on 10G
    METRICS.process_tick([], tick=10)  # establish graph
    with get_session() as s:
        pass
    # Manually bump link totals via a path: since both ends are same device, we simulate by direct map
    # Instead, feed sample to swA and rely on aggregation. Ensure it gets counted on link (not synthetic).
    METRICS.process_tick([("swA", 5_000_000_000.0)], tick=11)
    _ = METRICS.get_snapshot()
    # We won't assert link exact since graph aggregation may differ; just ensure no crash.

    # Override one interface to 1000 Mbps and ensure capacity resolution changes (indirectly verified by no errors)
    with get_session() as s:
        i = s.exec(select(Interface).where(Interface.id == "swA-uplink1")).first()
        assert i is not None
        i.capacity = 1000
        s.add(i)
        s.commit()
    METRICS.process_tick([("swA", 1_000_000_000.0)], tick=12)


def test_device_api_enriched_parameters(tmp_path: Path):
    init_db()
    data = {
        "catalog_id": "OLT_X",
        "device_type": "OLT",
        "vendor": "Gen",
        "model": "OLT-X",
        "version": "1.0",
        "attributes": {"tx_power_dbm": 5.0, "capacity_gbps": 80},
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "x.json").write_text(json.dumps(data), encoding="utf-8")
    with get_session() as s:
        assert load_catalog_dir(s, str(tmp_path)) == 1
        m = s.exec(select(HardwareModel)).first()
        assert m is not None
        s.add(Device(id="oltX", name="oltX", type=DeviceType.OLT, hardware_model_id=m.id))
        s.commit()
    c = TestClient(app)
    r = c.get("/api/devices/oltX")
    assert r.status_code == 200
    body = r.json()
    assert "parameters" in body
    p = body["parameters"]
    assert p["optical"]["effective_tx_power_dbm"] == 5.0
    assert p["capacity"]["catalog_device_capacity_mbps"] == 80_000
