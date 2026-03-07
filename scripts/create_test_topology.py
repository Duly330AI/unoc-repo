from sqlalchemy import create_engine
from sqlmodel import Session, select

engine = create_engine("postgresql://unoc:unocpw@localhost:5432/unocdb")

with Session(engine) as session:
    # Import models
    from backend.models_pkg.device import Device, DeviceType, Status
    from backend.models_pkg.interface import AdminStatus, Interface
    from backend.models_pkg.link import Link, LinkType
    from backend.models_pkg.physical import PhysicalMedium

    # Clean up
    for link in session.exec(select(Link).where(Link.id.like("test-go-%"))).all():
        session.delete(link)
    for interface in session.exec(select(Interface).where(Interface.id.like("test-go-%"))).all():
        session.delete(interface)
    for device in session.exec(select(Device).where(Device.id.like("test-go-%"))).all():
        session.delete(device)
    session.commit()

    # Get fiber
    fiber = session.exec(select(PhysicalMedium).where(PhysicalMedium.code == "SMF_G652D")).first()
    print(f"Fiber: {fiber.id if fiber else 'NOT FOUND'}")

    # Create OLT
    olt = Device(
        id="test-go-olt-1",
        name="Test OLT 1",
        type=DeviceType.OLT,
        status=Status.UP,
        provisioned=False,
    )
    session.add(olt)

    # Create SPLITTER
    splitter = Device(
        id="test-go-splitter-1",
        name="Test Splitter 1:8",
        type=DeviceType.SPLITTER,
        status=Status.UP,
        insertion_loss_db=10.5,
        provisioned=False,
    )
    session.add(splitter)

    # Create ONT
    ont = Device(
        id="test-go-ont-1",
        name="Test ONT 1",
        type=DeviceType.ONT,
        status=Status.UP,
        provisioned=False,
    )
    session.add(ont)
    session.commit()

    # Create interfaces
    olt_port = Interface(
        id="test-go-olt-1-port-1",
        device_id="test-go-olt-1",
        name="1/1/1",
        admin_status=AdminStatus.UP,
    )
    session.add(olt_port)

    splitter_uplink = Interface(
        id="test-go-splitter-1-uplink",
        device_id="test-go-splitter-1",
        name="uplink",
        admin_status=AdminStatus.UP,
    )
    session.add(splitter_uplink)

    splitter_downlink = Interface(
        id="test-go-splitter-1-port-1",
        device_id="test-go-splitter-1",
        name="port-1",
        admin_status=AdminStatus.UP,
    )
    session.add(splitter_downlink)

    ont_port = Interface(
        id="test-go-ont-1-optical",
        device_id="test-go-ont-1",
        name="optical",
        admin_status=AdminStatus.UP,
    )
    session.add(ont_port)
    session.commit()

    # Create links
    link1 = Link(
        id="test-go-link-1",
        a_interface_id="test-go-olt-1-port-1",
        b_interface_id="test-go-splitter-1-uplink",
        kind=LinkType.FIBER,
        length_km=2.0,
        physical_medium_id=fiber.id if fiber else None,
        status=Status.UP,
    )
    session.add(link1)

    link2 = Link(
        id="test-go-link-2",
        a_interface_id="test-go-splitter-1-port-1",
        b_interface_id="test-go-ont-1-optical",
        kind=LinkType.FIBER,
        length_km=1.0,
        physical_medium_id=fiber.id if fiber else None,
        status=Status.UP,
    )
    session.add(link2)

    session.commit()
    print("✅ Test topology created successfully!")

# Verify data persisted
with Session(engine) as session:
    devices = session.exec(select(Device).where(Device.id.like("test-go-%"))).all()
    print(f"\nCreated {len(devices)} test devices:")
    for dev in devices:
        print(f"  {dev.id} ({dev.type})")
