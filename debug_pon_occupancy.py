#!/usr/bin/env python3
"""Debug script to check PON occupancy calculation."""

from sqlmodel import select

from backend.db import get_session
from backend.models import Device, DeviceType, Interface, PortRole


def main():
    with get_session() as s:
        # Check ONTs
        onts = s.exec(select(Device).where(Device.type == DeviceType.ONT)).all()
        print(f"📊 Total ONTs in DB: {len(onts)}")

        provisioned_onts = [o for o in onts if o.provisioned]
        print(f"✅ Provisioned ONTs: {len(provisioned_onts)}")

        if provisioned_onts:
            print("\n📋 Sample provisioned ONTs:")
            for ont in provisioned_onts[:5]:
                print(f"  - {ont.id}: provisioned={ont.provisioned}, status={ont.status}")

        # Check OLT
        olts = s.exec(select(Device).where(Device.type == DeviceType.OLT)).all()
        print(f"\n📊 Total OLTs in DB: {len(olts)}")

        for olt in olts:
            print(f"\n🔌 OLT: {olt.id}")

            # Get PON interfaces
            pon_ifaces = s.exec(
                select(Interface).where(
                    (Interface.device_id == olt.id) & (Interface.port_role == PortRole.PON)
                )
            ).all()

            print(f"  PON interfaces: {len(pon_ifaces)}")
            for pon in pon_ifaces[:3]:
                print(f"    - {pon.id} ({pon.name})")

        # Check AON Switch
        aon_switches = s.exec(select(Device).where(Device.type == DeviceType.AON_SWITCH)).all()
        print(f"\n📊 Total AON Switches in DB: {len(aon_switches)}")

        for sw in aon_switches:
            print(f"\n🔌 AON Switch: {sw.id}")

            # Get ACCESS interfaces
            access_ifaces = s.exec(
                select(Interface).where(
                    (Interface.device_id == sw.id) & (Interface.port_role == PortRole.ACCESS)
                )
            ).all()

            print(f"  ACCESS interfaces: {len(access_ifaces)}")
            for acc in access_ifaces[:3]:
                print(f"    - {acc.id} ({acc.name})")


if __name__ == "__main__":
    main()
