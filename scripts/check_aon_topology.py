#!/usr/bin/env python3
"""Check AON switch topology - which CPEs are connected to which access ports."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import select

from backend.db import get_session
from backend.models import Device, DeviceType, Interface, Link


def main():
    with get_session() as s:
        # Find AON switch
        aon_switch = s.exec(select(Device).where(Device.type == DeviceType.AON_SWITCH)).first()
        if not aon_switch:
            print("No AON switch found in database")
            return

        print(f"AON Switch: {aon_switch.id} ({aon_switch.name})")
        print()

        # Find all CPEs
        cpes = s.exec(select(Device).where(Device.type == DeviceType.AON_CPE)).all()
        print(f"Found {len(cpes)} CPEs:")
        for cpe in cpes:
            print(
                f"  - {cpe.id} ({cpe.name}) - Status: {cpe.status}, Provisioned: {cpe.provisioned}"
            )
        print()

        # Get all interfaces of the AON switch
        switch_interfaces = s.exec(
            select(Interface).where(Interface.device_id == aon_switch.id)
        ).all()
        switch_if_map = {iface.id: iface.name for iface in switch_interfaces}

        # Find all links
        all_links = s.exec(select(Link)).all()

        print("Links from AON switch:")
        access_port_usage = {}
        for link in all_links:
            # Check if this link involves the AON switch
            switch_if_name = None
            other_if_id = None

            if link.a_interface_id in switch_if_map:
                switch_if_name = switch_if_map[link.a_interface_id]
                other_if_id = link.b_interface_id
            elif link.b_interface_id in switch_if_map:
                switch_if_name = switch_if_map[link.b_interface_id]
                other_if_id = link.a_interface_id

            if switch_if_name:
                # Get the other device
                other_if = s.get(Interface, other_if_id)
                if other_if:
                    other_dev = s.get(Device, other_if.device_id)
                    if other_dev:
                        print(
                            f"  {aon_switch.id}/{switch_if_name} <-> {other_dev.id}/{other_if.name}"
                        )

                        # Track access port usage
                        if switch_if_name.startswith("access"):
                            if switch_if_name not in access_port_usage:
                                access_port_usage[switch_if_name] = []
                            access_port_usage[switch_if_name].append(other_dev.id)

        print()
        print("Access port distribution:")
        for port in sorted(access_port_usage.keys(), key=lambda x: int(x.replace("access", ""))):
            devices = access_port_usage[port]
            print(f"  {port}: {len(devices)} device(s) - {', '.join(devices)}")

        # Check if all CPEs are on the same port
        if access_port_usage:
            max_port = max(access_port_usage.values(), key=len)
            if len(max_port) > 1:
                print()
                print(f"⚠️  WARNING: {len(max_port)} CPEs share the same access port!")
                print("   Expected AON topology: 1 CPE per access port (1:1 mapping)")


if __name__ == "__main__":
    main()
