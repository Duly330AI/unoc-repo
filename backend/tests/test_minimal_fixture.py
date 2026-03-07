"""Minimal test to debug fixture data persistence."""

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, select

import backend.models  # noqa: F401
from backend.models import Device, DeviceType, Status

POSTGRES_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
_engine = create_engine(POSTGRES_URL)


@pytest.fixture
def create_test_device():
    """Create a test device and verify it persists."""
    print("\n[FIXTURE SETUP] Creating test device...")

    with Session(_engine) as session:
        # Clean up first
        for device in session.exec(select(Device).where(Device.id == "test-minimal-device")).all():
            session.delete(device)
        session.commit()
        print("[FIXTURE SETUP] Cleaned up old data")

        # Create device
        device = Device(
            id="test-minimal-device",
            name="Minimal Test Device",
            type=DeviceType.ONT,
            status=Status.UP,
        )
        session.add(device)
        session.commit()
        print("[FIXTURE SETUP] Device created and committed")

    # Verify in NEW session
    with Session(_engine) as verify_session:
        verify_device = verify_session.get(Device, "test-minimal-device")
        if verify_device:
            print(f"[FIXTURE SETUP] ✅ Device verified in new session: {verify_device.id}")
        else:
            print("[FIXTURE SETUP] ❌ Device NOT FOUND in new session!")

    yield "test-minimal-device"

    # Cleanup
    with Session(_engine) as session:
        device = session.get(Device, "test-minimal-device")
        if device:
            session.delete(device)
            session.commit()
        print("[FIXTURE CLEANUP] Deleted test device")


def test_device_persists(create_test_device):
    """Test that fixture data persists for the test."""
    device_id = create_test_device
    print(f"\n[TEST] Testing with device: {device_id}")

    # Query in test scope
    with Session(_engine) as session:
        device = session.get(Device, device_id)
        if device:
            print(f"[TEST] ✅ Device found in test: {device.id} - {device.type}")
        else:
            print("[TEST] ❌ Device NOT FOUND in test!")

        assert device is not None, "Device should exist in test scope"
        assert device.type == DeviceType.ONT

    print("[TEST] Test assertions passed ✅")
