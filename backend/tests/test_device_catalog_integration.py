from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, HardwareModel, Interface, PortProfile
from backend.services.catalog_service import load_catalog_dir


def _write_catalog(tmpdir: Path):
    data = {
        "catalog_id": "SW_GENERIC_48P_RJ45_V1",
        "device_type": "EDGE_ROUTER",
        "vendor": "Generic",
        "model": "SW-48P",
        "version": "1.0",
        "attributes": {"capacity_gbps": 176, "ports_total": 50},
        "ports": [
            {"name": "mgmt", "count": 1, "role": "management", "speed_gbps": 1, "media": "rj45"},
            {"name": "uplink", "count": 2, "role": "uplink", "speed_gbps": 10, "media": "sfp+"},
            {"name": "eth", "count": 48, "role": "access", "speed_gbps": 1, "media": "rj45"},
        ],
        "meta": {"source": "test", "notes": "unit"},
    }
    tmpdir.mkdir(parents=True, exist_ok=True)
    (tmpdir / "switch.json").write_text(json.dumps(data), encoding="utf-8")


def test_device_creation_auto_interfaces(tmp_path: Path):
    init_db()
    _write_catalog(tmp_path)
    with get_session() as s:
        count = load_catalog_dir(s, str(tmp_path))
        assert count == 1
        hm = s.exec(select(HardwareModel)).first()
        assert hm is not None
        # sanity check port profiles
        profs = s.exec(select(PortProfile).where(PortProfile.hardware_model_id == hm.id)).all()
        assert any(p.name == "mgmt" and p.count == 1 for p in profs)
        assert any(p.name == "uplink" and p.count == 2 for p in profs)
        assert any(p.name == "eth" and p.count == 48 for p in profs)

    client = TestClient(app)
    # create device referencing the hardware model
    r = client.post(
        "/api/devices",
        json={
            "id": "sw1",
            "name": "Switch 1",
            "type": "EDGE_ROUTER",
            "status": "UP",
            "hardware_model_id": hm.id,
        },
    )
    assert r.status_code == 201, r.text
    # verify interfaces were created: 1 mgmt, 2 uplink, 48 eth = 51 total
    with get_session() as s:
        d = s.get(Device, "sw1")
        assert d is not None
        ifaces = s.exec(select(Interface).where(Interface.device_id == d.id)).all()
        # Expect exactly 51 interfaces
        assert len(ifaces) == 51
        names = {i.name for i in ifaces}
        # mgmt0 created
        assert "mgmt0" in names
        # uplink1..2 created
        assert "uplink1" in names and "uplink2" in names
        # eth1..48 created
        for i in range(1, 49):
            assert f"eth{i}" in names
        # all have MAC addresses
        assert all(getattr(i, "mac_address", None) for i in ifaces)
