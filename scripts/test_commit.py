"""Minimal reproduction script to test PostgreSQL commit behavior."""

from sqlalchemy import create_engine
from sqlmodel import Session, select

# Import ALL models to populate metadata
import backend.models  # noqa: F401
from backend.models_pkg.device import Device, DeviceType, Status

# Create engine
engine = create_engine("postgresql://unoc:unocpw@localhost:5432/unocdb")

# Write test device
with Session(engine) as session:
    # Clean up
    for device in session.exec(select(Device).where(Device.id == "test-commit-device")).all():
        session.delete(device)
    session.commit()

    # Create device
    device = Device(
        id="test-commit-device",
        name="Test Device",
        type=DeviceType.ONT,
        status=Status.UP,
        provisioned=False,
    )
    session.add(device)
    session.commit()
    print("✅ Device created and committed")

# Verify in NEW session (like Go service would)
with Session(engine) as session:
    device = session.exec(select(Device).where(Device.id == "test-commit-device")).first()
    if device:
        print(f"✅ Device found in new session: {device.id} ({device.type})")
    else:
        print("❌ Device NOT found in new session!")

print("\nNow check with external script...")
