"""Cross-VRF IP reuse behavioral test using provisioning path.

Ensures same host IP can be provisioned in two different VRFs without conflict.
"""

from __future__ import annotations

from backend.db import get_session, init_db
from backend.models import VRF, Device, DeviceType, Prefix
from backend.services.provisioning_service import provision_device


def test_cross_vrf_reuse_via_provisioning():
    init_db()
    with get_session() as s:
        # Create two VRFs and assign different mgmt prefixes (same CIDR ok)
        vrf1 = VRF(name="tenant1")
        vrf2 = VRF(name="tenant2")
        s.add(vrf1)
        s.add(vrf2)
        s.flush()
        assert vrf1.id is not None and vrf2.id is not None
        p1 = Prefix(prefix="10.250.210.0/24", vrf_id=vrf1.id, description="olt_mgmt")
        p2 = Prefix(prefix="10.250.210.0/24", vrf_id=vrf2.id, description="olt_mgmt")
        s.add(p1)
        s.add(p2)
        s.commit()
        # Two OLTs in same POP can reuse same host IP across VRFs
        pop = Device(id="popZ", name="POPZ", type=DeviceType.POP)
        core = Device(id="coreZ", name="coreZ", type=DeviceType.CORE_ROUTER)
        s.add(pop)
        s.add(core)
        s.commit()
        a = Device(id="oltA", name="oltA", type=DeviceType.OLT, parent_container_id=pop.id)
        b = Device(id="oltB", name="oltB", type=DeviceType.OLT, parent_container_id=pop.id)
        s.add(a)
        s.add(b)
        s.commit()
        # Minimal topology for strict path: core<->oltA and core<->oltB
        from backend.models import Interface, Link, LinkType

        for dev in (core, a, b):
            s.add(Interface(id=f"{dev.id}-if0", device_id=dev.id, name="if0"))
        s.flush()
        s.add(
            Link(
                id=f"{core.id}-{a.id}",
                a_interface_id=f"{core.id}-if0",
                b_interface_id=f"{a.id}-if0",
                kind=LinkType.FIBER,
            )
        )
        s.add(
            Link(
                id=f"{core.id}-{b.id}",
                a_interface_id=f"{core.id}-if0",
                b_interface_id=f"{b.id}-if0",
                kind=LinkType.FIBER,
            )
        )
        s.commit()
        provision_device(s, core)
        out_a = provision_device(s, a)
        out_b = provision_device(s, b)
        assert out_a.provisioned and out_b.provisioned
        # No uniqueness violation should have occurred
