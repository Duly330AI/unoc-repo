from sqlmodel import select

from backend.db import get_session, reset_db
from backend.models import Device, DeviceType, Interface, InterfaceAddress
from backend.services.mac_allocator import next_mac


def setup_function():
    reset_db()


def test_interface_address_persistence_and_lookup():
    with get_session() as s:
        d = Device(id="dev-ifaddr", name="dev-ifaddr", type=DeviceType.CORE_ROUTER)
        s.add(d)
        iface = Interface(id="dev-ifaddr-if0", device_id=d.id, name="if0")
        s.add(iface)
        s.commit()
        s.refresh(iface)
        a1 = InterfaceAddress(interface_id=iface.id, ip="10.0.0.1", prefix_len=24)
        a2 = InterfaceAddress(interface_id=iface.id, ip="10.0.0.2", prefix_len=24)
        s.add(a1)
        s.add(a2)
        s.commit()

        rows = s.exec(
            select(InterfaceAddress).where(InterfaceAddress.interface_id == iface.id)
        ).all()
        assert {r.ip for r in rows} == {"10.0.0.1", "10.0.0.2"}


def test_mac_allocator_uniqueness_and_format():
    with get_session() as s:
        d = Device(id="dev-mac", name="dev-mac", type=DeviceType.EDGE_ROUTER)
        s.add(d)
        s.commit()
        if1 = Interface(id="dev-mac-if0", device_id=d.id, name="if0")
        if2 = Interface(id="dev-mac-if1", device_id=d.id, name="if1")
        s.add(if1)
        s.add(if2)
        s.commit()

    mac1 = next_mac()
    mac2 = next_mac()
    assert mac1 != mac2
    for mac in (mac1, mac2):
        parts = mac.split(":")
        assert len(parts) == 6
        assert parts[0] == "02"  # locally administered
        int("".join(parts), 16)  # parseable
