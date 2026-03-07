from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, InterfaceAddress, Link, LinkType
from backend.services.provisioning_service import provision_device


def _mk(session, id: str, name: str, type_: DeviceType, parent: str | None = None):
    d = Device(id=id, name=name, type=type_, parent_container_id=parent)
    session.add(d)
    session.commit()
    session.refresh(d)
    return d


def test_basic_provision_flow():
    init_db()
    with get_session() as s:
        # Seed infrastructure
        _mk(s, "bb1", "Backbone", DeviceType.BACKBONE_GATEWAY)
        core = _mk(s, "core1", "Core", DeviceType.CORE_ROUTER)
        _mk(s, "pop1", "POP", DeviceType.POP)
        olt = _mk(s, "olt1", "OLT", DeviceType.OLT, parent="pop1")
        # Ensure logical adjacency core<->olt and core<->backbone for strict path validation
        s.add(Interface(id=f"{core.id}-if0", device_id=core.id, name="if0"))
        s.add(Interface(id=f"{olt.id}-if0", device_id=olt.id, name="if0"))
        s.add(Interface(id="bb1-if0", device_id="bb1", name="if0"))
        s.add(
            Link(
                id="core1-olt1",
                a_interface_id="core1-if0",
                b_interface_id="olt1-if0",
                kind=LinkType.FIBER,
            )
        )
        s.add(
            Link(
                id="core1-bb1",
                a_interface_id="core1-if0",
                b_interface_id="bb1-if0",
                kind=LinkType.FIBER,
            )
        )
        s.commit()
        provision_device(s, core)
        provision_device(s, olt)
        s.commit()
        s.refresh(olt)
        mgmt_if = s.get(Interface, "olt1-mgmt0")
    assert mgmt_if is not None
    # verify an InterfaceAddress exists and matches OLT mgmt prefix
    addrs = s.exec(
        select(InterfaceAddress).where(InterfaceAddress.interface_id == mgmt_if.id)
    ).all()
    assert len(addrs) >= 1
    # The provisioning service seeds an 'olt_mgmt' prefix; assert the allocated address belongs to it
    from backend.models import Prefix  # local import to avoid circulars at module import time

    olt_prefix = s.exec(select(Prefix).where(Prefix.description == "olt_mgmt")).first()
    assert olt_prefix is not None
    assert any(a.prefix_id == olt_prefix.id for a in addrs)
    assert olt.provisioned is True
