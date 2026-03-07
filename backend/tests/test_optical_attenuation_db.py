"""
Test that optical_service correctly persists attenuation_db to database.
"""

from fastapi.testclient import TestClient

from backend import events
from backend.db import get_session, init_db
from backend.main import app
from backend.models_pkg.device import Device

client = TestClient(app)


def _create_device(dev_id: str, dev_type: str, provision: bool = True):
    payload = {"id": dev_id, "name": dev_id, "type": dev_type, "status": "DOWN"}
    r = client.post("/api/devices", json=payload)
    assert r.status_code == 201, r.text
    if provision and dev_type in {"CORE_ROUTER", "OLT", "ONT"}:
        pr = client.post(f"/api/devices/{dev_id}/provision")
        assert pr.status_code == 200, pr.text


def test_attenuation_db_persisted_on_first_provision():
    """Test that attenuation_db is set and persisted when ONT is first provisioned."""
    init_db()
    events.reset_events()

    # Create devices (defer provision for OLT/ONT)
    _create_device("core", "CORE_ROUTER")
    _create_device("olt", "OLT", provision=False)
    _create_device("odf", "ODF")
    _create_device("ont", "ONT", provision=False)

    # Create links FIRST using generated interface IDs
    client.post(
        "/api/links",
        json={
            "id": "core__olt",
            "a_interface_id": "core-if0",  # Auto-created interfaces
            "b_interface_id": "olt-if0",
            "status": "UP",
            "kind": "FIBER",
        },
    )
    client.post(
        "/api/links",
        json={
            "id": "odf__olt-pon1",
            "a_interface_id": "odf-if0",
            "b_interface_id": "olt-pon1",
            "status": "UP",
            "kind": "FIBER",
        },
    )
    client.post(
        "/api/links",
        json={
            "id": "odf__ont-ge1",
            "a_interface_id": "odf-if0",
            "b_interface_id": "ont-ge1",
            "status": "UP",
            "kind": "FIBER",
        },
    )

    # NOW provision OLT (this triggers optical computation for ONT!)
    pr = client.post("/api/devices/olt/provision")
    assert pr.status_code == 200, pr.text

    # Check ONT - attenuation_db should ALREADY be set (from OLT provision!)
    with get_session() as s:
        ont = s.get(Device, "ont")
        assert (
            ont.attenuation_db is not None
        ), f"attenuation_db should be set after OLT provision! Got: {ont.attenuation_db}"
        first_attenuation = ont.attenuation_db

    # Provision ONT (should not change attenuation_db since nothing changed)
    pr = client.post("/api/devices/ont/provision")
    assert pr.status_code == 200, pr.text

    # Check ONT after provision - attenuation_db should still be set!
    with get_session() as s:
        ont = s.get(Device, "ont")
        assert (
            ont.attenuation_db is not None
        ), f"attenuation_db should still be persisted! Got: {ont.attenuation_db}"
        assert ont.attenuation_db > 0.0
        assert ont.attenuation_db < 10.0  # Sanity check
        assert abs(ont.attenuation_db - first_attenuation) < 0.01  # Should be same value


def test_attenuation_db_updated_on_recompute():
    """Test that attenuation_db is updated even when other optical values don't change."""
    init_db()
    events.reset_events()

    # Create topology and provision
    _create_device("core", "CORE_ROUTER")
    _create_device("olt", "OLT")
    _create_device("odf", "ODF")
    _create_device("ont", "ONT")  # Auto-provisions

    # Create links
    client.post(
        "/api/links",
        json={
            "id": "core__olt",
            "a_interface_id": "core-uplink1",
            "b_interface_id": "olt-uplink1",
            "status": "UP",
            "kind": "FIBER",
        },
    )
    client.post(
        "/api/links",
        json={
            "id": "odf__olt-pon1",
            "a_interface_id": "odf-if0",
            "b_interface_id": "olt-pon1",
            "status": "UP",
            "kind": "FIBER",
        },
    )
    client.post(
        "/api/links",
        json={
            "id": "odf__ont-ge1",
            "a_interface_id": "odf-if0",
            "b_interface_id": "ont-ge1",
            "status": "UP",
            "kind": "FIBER",
        },
    )

    # Get initial attenuation value
    with get_session() as s:
        ont = s.get(Device, "ont")
        first_attenuation = ont.attenuation_db
        assert first_attenuation is not None

        # Manually clear it (simulating old DB without attenuation_db)
        ont.attenuation_db = None
        s.commit()

    # Re-provision OLT (triggers optical recomputation for all ONTs)
    # Force OLT DOWN first
    client.patch("/api/devices/olt", json={"status_override": "DOWN"})
    client.delete("/api/devices/olt/status_override")

    # Re-provision
    pr = client.post("/api/devices/olt/provision")
    assert pr.status_code == 200, pr.text

    # Check that attenuation_db was set again!
    with get_session() as s:
        ont = s.get(Device, "ont")
        assert ont.attenuation_db is not None, "attenuation_db should be re-persisted on recompute!"
        assert abs(ont.attenuation_db - first_attenuation) < 0.1
