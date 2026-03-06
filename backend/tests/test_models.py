from __future__ import annotations

from sqlmodel import select

from backend.db import get_session
from backend.models import Device, DeviceRole, DeviceType, Interface, Link, LinkType


def test_device_interface_link_creation():
    with get_session() as s:
        d = Device(id="dev1", name="POP-1", type=DeviceType.POP)
        s.add(d)
        i1 = Interface(id="if1", device_id="dev1", name="ge-0/0/0")
        i2 = Interface(id="if2", device_id="dev1", name="ge-0/0/1")
        s.add(i1)
        s.add(i2)
        link = Link(id="lnk1", a_interface_id="if1", b_interface_id="if2", kind=LinkType.FIBER)
        s.add(link)
        s.commit()

        # refresh / query
        got = s.get(Device, "dev1")
        assert got is not None
        assert got.name == "POP-1"
    # relationships lazy - ensure interfaces persisted
    interfaces = s.exec(select(Interface).where(Interface.device_id == "dev1")).all()
    assert len(interfaces) == 2
    link = s.get(Link, "lnk1")
    assert link is not None
    assert link.a_interface_id == "if1"
    assert link.b_interface_id == "if2"


def test_device_role_derivation():
    d1 = Device(id="d1", name="POP-1", type=DeviceType.POP)
    d2 = Device(id="d2", name="ONT-1", type=DeviceType.ONT)
    d3 = Device(id="d3", name="SPL-1", type=DeviceType.SPLITTER)
    assert d1.derive_role() == DeviceRole.ALWAYS_ONLINE
    assert d2.derive_role() == DeviceRole.ACTIVE
    assert d3.derive_role() == DeviceRole.PASSIVE
