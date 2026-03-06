#!/usr/bin/env python3
"""Check zombie devices (test-bulk-1/2)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import select

from backend.db import get_session
from backend.models import Device, Interface, Link


def main():
    with get_session() as s:
        for dev_id in ["test-bulk-1", "test-bulk-2"]:
            dev = s.get(Device, dev_id)
            print(f"\n{dev_id}:")
            print(f"  Device exists: {dev is not None}")

            if dev:
                # Check interfaces
                ifaces = s.exec(select(Interface).where(Interface.device_id == dev_id)).all()
                print(f"  Interfaces: {len(ifaces)}")
                for iface in ifaces:
                    print(f"    - {iface.id} ({iface.name})")

                # Check links
                links_a = s.exec(select(Link).where(Link.a_interface_id.like(f"{dev_id}%"))).all()
                links_b = s.exec(select(Link).where(Link.b_interface_id.like(f"{dev_id}%"))).all()
                print(f"  Links: {len(links_a) + len(links_b)}")


if __name__ == "__main__":
    main()
