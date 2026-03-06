"""
Quick script to create 2-ONT topology for minimal BFS test.
Run this, then manually test Go engine.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.db import get_session
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status, Tariff
from backend.services.provisioning_service import provision_device

print("[BUILD] Creating 2-ONT topology...")

with get_session() as s:
    # 1. Backbone
    s.add(
        Device(
            id="backbone1",
            name="Backbone-1",
            type=DeviceType.BACKBONE_GATEWAY,
            status=Status.UP,
            provisioned=True,
        )
    )
    s.add(Interface(id="backbone1-if0", device_id="backbone1", name="if0"))

    # 2. Core
    s.add(
        Device(
            id="core1",
            name="Core-1",
            type=DeviceType.CORE_ROUTER,
            status=Status.UP,
            provisioned=False,
        )
    )
    s.add(Interface(id="core1-if0", device_id="core1", name="if0"))

    # 3. OLT
    s.add(Device(id="olt1", name="OLT-1", type=DeviceType.OLT, status=Status.UP, provisioned=False))
    s.add(Interface(id="olt1-if0", device_id="olt1", name="if0"))
    s.add(Interface(id="olt1-if1", device_id="olt1", name="if1"))

    # 4. ODF
    s.add(Device(id="odf1", name="ODF-1", type=DeviceType.ODF, status=Status.UP, provisioned=False))
    s.add(Interface(id="odf1-if0", device_id="odf1", name="if0"))
    s.add(Interface(id="odf1-if1", device_id="odf1", name="if1"))
    s.add(Interface(id="odf1-if2", device_id="odf1", name="if2"))

    # 5. ONTs
    s.add(Device(id="ont1", name="ONT-1", type=DeviceType.ONT, status=Status.UP, provisioned=False))
    s.add(Interface(id="ont1-if0", device_id="ont1", name="if0"))

    s.add(Device(id="ont2", name="ONT-2", type=DeviceType.ONT, status=Status.UP, provisioned=False))
    s.add(Interface(id="ont2-if0", device_id="ont2", name="if0"))

    s.commit()
    print("[OK] Created 6 devices")

    # 6. Links
    s.add(
        Link(
            id="link_bb_core",
            a_interface_id="backbone1-if0",
            b_interface_id="core1-if0",
            kind=LinkType.P2P,
            status=Status.UP,
        )
    )
    s.add(
        Link(
            id="link_core_olt",
            a_interface_id="core1-if0",
            b_interface_id="olt1-if0",
            kind=LinkType.FIBER,
            status=Status.UP,
        )
    )
    s.add(
        Link(
            id="link_olt_odf",
            a_interface_id="olt1-if1",
            b_interface_id="odf1-if0",
            kind=LinkType.FIBER,
            status=Status.UP,
        )
    )
    s.add(
        Link(
            id="link_odf_ont1",
            a_interface_id="odf1-if1",
            b_interface_id="ont1-if0",
            kind=LinkType.FIBER,
            status=Status.UP,
        )
    )
    s.add(
        Link(
            id="link_odf_ont2",
            a_interface_id="odf1-if2",
            b_interface_id="ont2-if0",
            kind=LinkType.FIBER,
            status=Status.UP,
        )
    )
    s.commit()
    print("[OK] Created 5 links")

    # 7. Tariff
    s.add(Tariff(id=1, name="Residential 100/20", max_down_mbps=100, max_up_mbps=20))
    s.commit()

    ont1 = s.get(Device, "ont1")
    ont1.tariff_id = 1
    ont2 = s.get(Device, "ont2")
    ont2.tariff_id = 1
    s.commit()
    print("[OK] Assigned tariffs")

    # 8. Provision (Core, OLT, ONTs - NOT ODF!)
    # NOTE: ODF is passive device (fiber distribution frame) - no provisioning!
    core = s.get(Device, "core1")
    provision_device(s, core)

    olt = s.get(Device, "olt1")
    provision_device(s, olt)

    # ODF is passive - skip it!

    ont1_dev = s.get(Device, "ont1")
    provision_device(s, ont1_dev)

    ont2_dev = s.get(Device, "ont2")
    provision_device(s, ont2_dev)

    s.commit()
    print("[OK] Provisioned 4 devices (Core, OLT, 2 ONTs - ODF is passive)")

    # Final commit
    s.commit()

print("[SUCCESS] 2-ONT topology ready!")
print("Next: Start Go engine manually and test")
