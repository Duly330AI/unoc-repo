"""Manual test to reproduce fixture creation logic."""

from sqlmodel import Session, create_engine, select

import backend.models  # noqa: F401
from backend.models import Device, DeviceType, Interface, Link, PhysicalMedium, Status
from backend.models_pkg.interface import AdminStatus
from backend.models_pkg.link import LinkType

POSTGRES_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
engine = create_engine(POSTGRES_URL)

with Session(engine) as session:
    # Clean up first
    for link in session.exec(select(Link).where(Link.id.like("test-manual-%"))).all():
        session.delete(link)
    for interface in session.exec(
        select(Interface).where(Interface.id.like("test-manual-%"))
    ).all():
        session.delete(interface)
    for device in session.exec(select(Device).where(Device.id.like("test-manual-%"))).all():
        session.delete(device)
    session.commit()

    # Get fiber
    fiber = session.exec(select(PhysicalMedium).where(PhysicalMedium.code == "SMF_G652D")).first()
    if not fiber:
        print("❌ SMF_G652D fiber not found!")
        exit(1)
    print(f"✅ Found fiber: {fiber.code}")

    # Create ONT
    ont = Device(
        id="test-manual-ont-1",
        name="Manual Test ONT",
        type=DeviceType.ONT,
        status=Status.UP,
    )
    session.add(ont)
    print(f"Created ONT: {ont.id}")

    # Create OLT
    olt = Device(
        id="test-manual-olt-1",
        name="Manual Test OLT",
        type=DeviceType.OLT,
        status=Status.UP,
    )
    session.add(olt)
    print(f"Created OLT: {olt.id}")

    # Create interfaces
    ont_port = Interface(
        id="test-manual-ont-1-optical",
        device_id="test-manual-ont-1",
        name="optical",
        admin_status=AdminStatus.UP,
    )
    session.add(ont_port)

    olt_port = Interface(
        id="test-manual-olt-1-port-1",
        device_id="test-manual-olt-1",
        name="port-1",
        admin_status=AdminStatus.UP,
    )
    session.add(olt_port)
    print("Created interfaces")

    # Create link
    link = Link(
        id="test-manual-link-1",
        a_interface_id="test-manual-ont-1-optical",
        b_interface_id="test-manual-olt-1-port-1",
        kind=LinkType.FIBER,
        physical_medium_id=fiber.id,
        length_km=1.0,
    )
    session.add(link)
    print("Created link")

    session.commit()
    print("\n✅ All data committed")

# Verify in new session
with Session(engine) as verify_session:
    devices = verify_session.exec(select(Device).where(Device.id.like("test-manual-%"))).all()
    print(f"\n📊 Verification: Found {len(devices)} devices:")
    for d in devices:
        print(f"  - {d.id}: {d.type}")

    links = verify_session.exec(select(Link).where(Link.id.like("test-manual-%"))).all()
    print(f"  Found {len(links)} links")

print("\n✅ Manual fixture creation successful!")
