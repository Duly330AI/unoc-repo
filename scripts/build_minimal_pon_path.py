"""
Build minimal realistic PON path for traffic generation validation.

Topology:
  pop1 (POP, existing)
    ↓ link1
  core1 (CORE_ROUTER, existing)
    ↓ link2
  olt1 (OLT, existing)
    ↓ link3
  ont_test1 (ONT, existing, provisioned, tariff_id=1)

Creates 8 interfaces + 3 links for a complete path from ONT to POP (anchor).
"""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import get_session
from backend.models import Device, Interface, Link


def build_minimal_pon_path():
    """Create interfaces and links for minimal PON path."""
    with get_session() as session:
        # Verify devices exist
        pop1 = session.query(Device).filter_by(id="pop1").first()
        core1 = session.query(Device).filter_by(id="core1").first()
        olt1 = session.query(Device).filter_by(id="olt1").first()
        ont_test1 = session.query(Device).filter_by(id="ont_test1").first()

        if not all([pop1, core1, olt1, ont_test1]):
            print("❌ Missing required devices!")
            print(f"  pop1: {pop1 is not None}")
            print(f"  core1: {core1 is not None}")
            print(f"  olt1: {olt1 is not None}")
            print(f"  ont_test1: {ont_test1 is not None}")
            return

        print("✅ All devices found")

        # Create interfaces
        from backend.models_pkg.interface import AdminStatus, PortRole

        interfaces = [
            # POP interfaces
            Interface(
                id="pop1_if1",
                device_id="pop1",
                name="eth0",
                port_role=PortRole.UPLINK,
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="pop1_if2",
                device_id="pop1",
                name="eth1",
                port_role=PortRole.UPLINK,
                admin_status=AdminStatus.UP,
            ),
            # Core Router interfaces
            Interface(
                id="core1_if_up",
                device_id="core1",
                name="eth0",
                port_role=PortRole.UPLINK,
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="core1_if_down",
                device_id="core1",
                name="eth1",
                port_role=PortRole.ACCESS,
                admin_status=AdminStatus.UP,
            ),
            # OLT interfaces
            Interface(
                id="olt1_if_up",
                device_id="olt1",
                name="eth0",
                port_role=PortRole.UPLINK,
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="olt1_pon1",
                device_id="olt1",
                name="pon1",
                port_role=PortRole.PON,
                admin_status=AdminStatus.UP,
            ),
            # ONT interface
            Interface(
                id="ont_test1_pon0",
                device_id="ont_test1",
                name="pon0",
                port_role=PortRole.PON,
                admin_status=AdminStatus.UP,
            ),
            Interface(
                id="ont_test1_eth0",
                device_id="ont_test1",
                name="eth0",
                port_role=PortRole.ACCESS,
                admin_status=AdminStatus.UP,
            ),
        ]

        # Check for existing interfaces
        existing_iface_ids = {iface.id for iface in session.query(Interface).all()}
        new_interfaces = [iface for iface in interfaces if iface.id not in existing_iface_ids]

        if new_interfaces:
            session.add_all(new_interfaces)
            session.flush()
            print(f"✅ Created {len(new_interfaces)} interfaces")
        else:
            print("⚠️  All interfaces already exist")

        # Create links
        from backend.models_pkg.device import Status
        from backend.models_pkg.link import LinkType

        links = [
            # Link 1: POP ↔ Core
            Link(
                id="link_pop_core",
                a_interface_id="pop1_if1",
                b_interface_id="core1_if_up",
                kind=LinkType.FIBER,
                status=Status.UP,
            ),
            # Link 2: Core ↔ OLT
            Link(
                id="link_core_olt",
                a_interface_id="core1_if_down",
                b_interface_id="olt1_if_up",
                kind=LinkType.FIBER,
                status=Status.UP,
            ),
            # Link 3: OLT ↔ ONT (PON)
            Link(
                id="link_olt_ont_test1",
                a_interface_id="olt1_pon1",
                b_interface_id="ont_test1_pon0",
                kind=LinkType.FIBER,
                status=Status.UP,
            ),
        ]

        # Check for existing links
        existing_link_ids = {link.id for link in session.query(Link).all()}
        new_links = [link for link in links if link.id not in existing_link_ids]

        if new_links:
            session.add_all(new_links)
            session.flush()
            print(f"✅ Created {len(new_links)} links")
        else:
            print("⚠️  All links already exist")

        session.commit()

        # Verify path
        print("\n📊 Final topology:")
        print(f"  Devices: {session.query(Device).count()}")
        print(f"  Interfaces: {session.query(Interface).count()}")
        print(f"  Links: {session.query(Link).count()}")

        print("\n✅ Minimal PON path created:")
        print("  pop1 (POP, anchor)")
        print("    ↓ link_pop_core (10G)")
        print("  core1 (CORE_ROUTER)")
        print("    ↓ link_core_olt (10G)")
        print("  olt1 (OLT)")
        print("    ↓ link_olt_ont_test1 (2.5G PON)")
        print("  ont_test1 (ONT, provisioned, tariff_id=1)")
        print("\n🎯 BFS should now find path: ont_test1 → olt1 → core1 → pop1")


if __name__ == "__main__":
    build_minimal_pon_path()
