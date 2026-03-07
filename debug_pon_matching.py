"""Debug PON occupancy calculation logic."""

import asyncio

from sqlmodel import select

from backend.clients.go_services.optical_client import OpticalClient
from backend.db import get_async_session
from backend.models import Device, Interface, Link, PortRole


async def debug_pon_occupancy():
    async_session_gen = get_async_session()
    s = await anext(async_session_gen)
    try:
        # Get OLT
        olt = await s.get(Device, "olt")
        if not olt:
            print("❌ OLT not found")
            return

        # Get OLT interfaces
        result = await s.exec(select(Interface).where(Interface.device_id == "olt"))
        ifaces = result.all()
        pon_ifaces = [i for i in ifaces if i.port_role == PortRole.PON]
        print(f"\n📋 OLT has {len(ifaces)} interfaces, {len(pon_ifaces)} PON ports")

        # Get links
        result = await s.exec(select(Link))
        links = result.all()
        print(f"📋 Total links in DB: {len(links)}")

        # Build neighbor map for OLT
        ifmap = {i.id: i for i in ifaces}
        iface_ids = {i.id for i in ifaces}
        neigh_by_if: dict[str, set[str]] = {i.id: set() for i in ifaces}

        # Get counterpart interfaces
        counterpart_ids = set()
        for ln in links:
            if ln.a_interface_id and ln.a_interface_id not in iface_ids:
                counterpart_ids.add(ln.a_interface_id)
            if ln.b_interface_id and ln.b_interface_id not in iface_ids:
                counterpart_ids.add(ln.b_interface_id)

        counterpart_dev_by_if: dict[str, str] = {}
        if counterpart_ids:
            res = await s.exec(select(Interface).where(Interface.id.in_(counterpart_ids)))  # type: ignore
            for c_if in res.all():
                counterpart_dev_by_if[c_if.id] = c_if.device_id

        # Build neighbor relationships
        for ln in links:
            a_if = ifmap.get(ln.a_interface_id)
            b_if = ifmap.get(ln.b_interface_id)
            if a_if and a_if.device_id == olt.id and ln.b_interface_id:
                nb_dev = counterpart_dev_by_if.get(ln.b_interface_id)
                if not nb_dev and ln.b_interface_id in iface_ids:
                    nb_dev = olt.id
                if nb_dev:
                    neigh_by_if[a_if.id].add(nb_dev)
            if b_if and b_if.device_id == olt.id and ln.a_interface_id:
                nb_dev = counterpart_dev_by_if.get(ln.a_interface_id)
                if not nb_dev and ln.a_interface_id in iface_ids:
                    nb_dev = olt.id
                if nb_dev:
                    neigh_by_if[b_if.id].add(nb_dev)

        print("\n📋 Neighbor map for OLT interfaces:")
        for iface_id, neighbors in neigh_by_if.items():
            if neighbors:
                iface = ifmap.get(iface_id)
                print(f"  - {iface.name if iface else iface_id}: {neighbors}")

        # Get ONT path from Go Service
        optical_client = OpticalClient()
        path_data = await asyncio.to_thread(optical_client.get_path, "ont")
        print("\n📋 Go Optical Path for 'ont':")
        print(f"  OLT ID: {path_data.get('olt_id')}")
        print(f"  Segments: {len(path_data.get('segments', []))}")

        # Extract path device IDs
        path_devs = []
        for seg in path_data.get("segments", []):
            path_devs.append(seg.get("from_device_id"))
        if path_data.get("segments"):
            last_seg = path_data["segments"][-1]
            path_devs.append(last_seg.get("to_device_id"))

        print(f"  Path devices: {path_devs}")

        # Find matching PON interface
        print("\n🔍 Looking for PON interface match:")
        for pi in pon_ifaces:
            nb = neigh_by_if.get(pi.id, set())
            match = any(nd in path_devs for nd in nb)
            print(f"  - {pi.name}: neighbors={nb}, matches_path={match}")
    finally:
        await s.close()


if __name__ == "__main__":
    asyncio.run(debug_pon_occupancy())
