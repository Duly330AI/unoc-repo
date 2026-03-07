"""Check live AON topology configuration."""

import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://unoc:unocpw@localhost:5432/unocdb"

from sqlmodel import select

from backend.db import get_session
from backend.models import Device, Interface, Link

with get_session() as session:
    # Get AON Switch
    aon = session.exec(select(Device).where(Device.name.contains("aon"))).first()
    if aon:
        print("\n=== AON Switch ===")
        print(f"Name: {aon.name}")
        print(f"ID: {aon.id}")
        print(f"Type: {aon.type}")

        # Get ACCESS ports
        access_ports = session.exec(
            select(Interface)
            .where(Interface.device_id == aon.id)
            .where(Interface.name.like("access%"))
            .order_by(Interface.name)
        ).all()

        print(f"\n=== ACCESS Ports: {len(access_ports)} total ===")

        # Check link distribution
        link_distribution = {}
        for port in access_ports:
            links = session.exec(
                select(Link).where(
                    (Link.a_interface_id == port.id) | (Link.b_interface_id == port.id)
                )
            ).all()
            link_distribution[port.name] = len(links)

        # Show distribution summary
        for port_name, count in sorted(link_distribution.items())[:10]:
            print(f"  {port_name}: {count} link(s)")

        if len(link_distribution) > 10:
            print(f"  ... ({len(link_distribution) - 10} more ports)")

    # Get CPEs
    cpes = session.exec(select(Device).where(Device.type == "AON_CPE")).all()
    print(f"\n=== CPE Devices: {len(cpes)} total ===")

    # Check first 5 CPE connections
    for cpe in cpes[:5]:
        print(f"\n{cpe.name} (id={cpe.id}):")
        uplink = session.exec(
            select(Interface).where(Interface.device_id == cpe.id).where(Interface.role == "UPLINK")
        ).first()

        if uplink:
            link = session.exec(
                select(Link).where(
                    (Link.a_interface_id == uplink.id) | (Link.b_interface_id == uplink.id)
                )
            ).first()

            if link:
                peer_if_id = (
                    link.b_interface_id if link.a_interface_id == uplink.id else link.a_interface_id
                )
                peer_if = session.get(Interface, peer_if_id)
                if peer_if:
                    print(f"  uplink → {peer_if.device_id}-{peer_if.name}")
