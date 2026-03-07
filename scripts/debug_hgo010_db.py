"""Quick DB diagnostics for HGO-010 debugging."""

from sqlmodel import func, select

from backend.db import get_session
from backend.models import Device, Link


def main():
    with get_session() as s:
        print("=== LINK COUNT ===")
        total_links = s.exec(select(func.count()).select_from(Link)).first()
        print(f"Total links: {total_links}")
        up_links = s.exec(select(func.count()).select_from(Link).where(Link.status == "UP")).first()
        print(f"UP links: {up_links}")

        print("\n=== BACKBONE_GATEWAY ===")
        gateways = s.exec(select(Device).where(Device.type == "BACKBONE_GATEWAY")).all()
        print(f"Count: {len(gateways)}")
        for g in gateways:
            print(f"  {g.id}: {g.name} (status={g.status})")

        print("\n=== ONT PROVISIONED ===")
        onts = s.exec(select(Device).where(Device.type == "ONT", Device.provisioned == True)).all()
        print(f"Provisioned ONTs: {len(onts)}")
        onts_with_tariff = [o for o in onts if o.tariff_id]
        print(f"ONTs with tariff: {len(onts_with_tariff)}")

        print("\n=== SAMPLE LINKS ===")
        from backend.models import Interface

        links = s.exec(select(Link).where(Link.status == "UP").limit(10)).all()
        for link in links:
            iface_a = s.get(Interface, link.interface_a_id)
            iface_b = s.get(Interface, link.interface_b_id)
            print(f"  {link.id}: {iface_a.device_id} <-> {iface_b.device_id}")


if __name__ == "__main__":
    main()
