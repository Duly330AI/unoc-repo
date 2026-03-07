"""
Build 64-ONT topology for debugging.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.db import get_session
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status, Tariff
from backend.services.provisioning_service import provision_device

print("[BUILD] Creating 64-ONT topology...")

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

    # 4. ODF (1 strand, 64 ports)
    s.add(Device(id="odf1", name="ODF-1", type=DeviceType.ODF, status=Status.UP, provisioned=False))
    s.add(Interface(id="odf1-if0", device_id="odf1", name="if0"))  # To OLT
    for i in range(1, 65):
        s.add(Interface(id=f"odf1-if{i}", device_id="odf1", name=f"if{i}"))

    s.commit()
    print("[OK] Created backbone, core, OLT, ODF (68 interfaces)")

    # 5. Create 64 ONTs
    for i in range(1, 65):
        s.add(
            Device(
                id=f"ont1_{i}",
                name=f"ONT-1-{i}",
                type=DeviceType.ONT,
                status=Status.UP,
                provisioned=False,
            )
        )
        s.add(Interface(id=f"ont1_{i}-if0", device_id=f"ont1_{i}", name="if0"))

    s.commit()
    print("[OK] Created 64 ONTs (total 68 devices)")

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

    for i in range(1, 65):
        s.add(
            Link(
                id=f"link_odf1_ont1_{i}",
                a_interface_id=f"odf1-if{i}",
                b_interface_id=f"ont1_{i}-if0",
                kind=LinkType.FIBER,
                status=Status.UP,
            )
        )

    s.commit()
    print("[OK] Created 67 links")

    # 7. Tariff
    s.add(Tariff(id=1, name="Residential 100/20", max_down_mbps=100, max_up_mbps=20))
    s.commit()

    for i in range(1, 65):
        ont = s.get(Device, f"ont1_{i}")
        ont.tariff_id = 1
    s.commit()
    print("[OK] Assigned tariffs to 64 ONTs")

    # 8. Provision Core + OLT first
    core = s.get(Device, "core1")
    provision_device(s, core)

    olt = s.get(Device, "olt1")
    provision_device(s, olt)

    s.commit()
    print("[OK] Provisioned Core + OLT")

    # 9. Provision ONTs (all 64)
    for i in range(1, 65):
        ont = s.get(Device, f"ont1_{i}")
        provision_device(s, ont)

    s.commit()
    print("[OK] Provisioned 64 ONTs")

    # Final commit
    s.commit()

print("[SUCCESS] 64-ONT topology ready!")
