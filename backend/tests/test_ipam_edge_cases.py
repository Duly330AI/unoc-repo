"""IPAM edge case tests.

Covers duplicate management interface scenario which raises DUPLICATE_MGMT_INTERFACE.
Parallel provisioning semantics (optimistic guard) are indirectly covered by existing
double provisioning test (ALREADY_PROVISIONED)."""

from fastapi import HTTPException
from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import (
    Device,
    DeviceType,
    Interface,
    InterfaceAddress,
    InterfaceRole,
    Link,
    LinkType,
    Prefix,
)
from backend.services.provisioning_service import provision_device
from backend.services.seed_service import ensure_ipam_defaults


def test_duplicate_mgmt_interface_rejected():
    init_db()
    with get_session() as s:
        # Provide POP dependency so OLT provisioning path is valid
        pop = Device(id="pop1", name="POP", type=DeviceType.POP)
        core = Device(id="coreX", name="CORE", type=DeviceType.CORE_ROUTER)
        s.add(pop)
        s.add(core)
        s.commit()

        d = Device(id="olt-edge", name="OLT", type=DeviceType.OLT, parent_container_id="pop1")
        s.add(d)
        s.commit()

        # Ensure logical adjacency core<->olt for strict path validation
        s.add(Interface(id=f"{core.id}-if0", device_id=core.id, name="if0"))
        s.add(Interface(id=f"{d.id}-if0", device_id=d.id, name="if0"))
        s.add(
            Link(
                id=f"{core.id}-{d.id}",
                a_interface_id=f"{core.id}-if0",
                b_interface_id=f"{d.id}-if0",
                kind=LinkType.FIBER,
            )
        )
        s.commit()

        # Pre-create management interface and an address (simulates prior manual allocation)
        iface = Interface(
            id="olt-edge-mgmt0",
            device_id=d.id,
            name="mgmt0",
            role=InterfaceRole.MANAGEMENT,
        )
        s.add(iface)
        s.flush()

        # Ensure a management prefix exists and bind the address to it
        ensure_ipam_defaults(s)
        olt_pref = s.exec(select(Prefix).where(Prefix.description == "olt_mgmt")).first()
        assert olt_pref is not None

        s.add(
            InterfaceAddress(
                interface_id=iface.id,
                ip="10.250.4.10",
                prefix_len=24,
                prefix_id=olt_pref.id,
            )
        )
        s.commit()

        # Now provisioning should detect duplicate mgmt interface usage
        try:
            provision_device(s, d)
        except HTTPException as e:  # expected
            assert e.detail == "DUPLICATE_MGMT_INTERFACE"
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected DUPLICATE_MGMT_INTERFACE not raised")
