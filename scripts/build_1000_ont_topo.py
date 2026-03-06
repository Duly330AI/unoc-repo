#!/usr/bin/env python3
"""
HGO-011: Build 1000-Device Topology for Load Testing

Creates topology in PostgreSQL:
- 1 Backbone Gateway
- 1 Core Router
- 5 OLTs (200 ONTs each)
- 15 ODFs (passive, 3 per OLT)
- 1000 ONTs (distributed across 15 strands, ~67 per strand)

Total: 1022 devices, ~1036 links

Usage:
    $env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
    python scripts/build_1000_ont_topo.py
"""

import subprocess
import sys
from pathlib import Path

# Add repo root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import (
    VRF,
    Device,
    DeviceType,
    Interface,
    Link,
    LinkType,
    Prefix,
    Status,
    Tariff,
)
from backend.services.provisioning_service import provision_device


def main():
    print("[BUILD] Creating 1000-ONT topology (5 OLTs)...")

    # Reset DB (catalog only, no seed devices to avoid conflicts)
    reset_script = ROOT / "scripts" / "reset_dev_db.py"
    subprocess.run([sys.executable, str(reset_script), "--force", "--catalog-only"], check=True)
    init_db()

    with get_session() as s:
        # Create default tariff manually (since we skipped --seed)
        default_tariff = Tariff(
            id=1,
            name="Default",
            max_up_mbps=50.0,
            max_down_mbps=100.0,
        )
        s.add(default_tariff)
        s.commit()
        print("[OK] Created default tariff")

        # Create VRF and IP prefixes for provisioning (CRITICAL FIX)
        # Previous issue: No prefixes created → POOL_EXHAUSTED at ~254 ONTs
        # Fix: Create /16 prefixes (65k IPs) for realistic enterprise scale
        vrf = VRF(name="mgmt")
        s.add(vrf)
        s.commit()
        s.refresh(vrf)
        assert vrf.id is not None, "VRF must have ID after commit"
        print(f"[OK] Created VRF: {vrf.name} (id={vrf.id})")

        # Create management prefixes with LARGE address pools
        # /16 = 65534 usable IPs (enough for 65k ONTs in production)
        # Each device type gets dedicated range (no overlap)
        # NOTE: These match seed_helpers/ipam.py defaults for consistency
        prefixes = [
            Prefix(
                prefix="10.250.0.0/16", vrf_id=vrf.id, description="ont_mgmt"
            ),  # ONTs: 10.250.0.1 - 10.250.255.254
            Prefix(
                prefix="10.251.0.0/24", vrf_id=vrf.id, description="olt_mgmt"
            ),  # OLTs: 10.251.0.1 - 10.251.0.254
            Prefix(
                prefix="10.252.0.0/24", vrf_id=vrf.id, description="core_mgmt"
            ),  # Core: 10.252.0.1 - 10.252.0.254
            Prefix(
                prefix="10.253.0.0/24", vrf_id=vrf.id, description="aon_mgmt"
            ),  # AON: 10.253.0.1 - 10.253.0.254
            Prefix(
                prefix="10.254.0.0/24", vrf_id=vrf.id, description="cpe_mgmt"
            ),  # CPE: 10.254.0.1 - 10.254.0.254
        ]
        for p in prefixes:
            s.add(p)
        s.commit()
        print(f"[OK] Created {len(prefixes)} IP management prefixes")
        print("     ont_mgmt: 10.250.0.0/16 (65534 IPs available)")
        print("     olt_mgmt: 10.251.0.0/24 (254 IPs)")
        print("     core_mgmt: 10.252.0.0/24 (254 IPs)")
        print()

        # Now create topology devices
        # 1. Backbone Gateway
        backbone = Device(
            id="backbone1", name="Backbone-1", type=DeviceType.BACKBONE_GATEWAY, status=Status.UP
        )
        s.add(backbone)
        s.add(Interface(id="backbone1-if0", device_id="backbone1", name="if0"))

        # 2. Core Router
        core = Device(
            id="core1",
            name="Core-1",
            type=DeviceType.CORE_ROUTER,
            status=Status.UP,
            provisioned=False,
        )
        s.add(core)
        s.add(Interface(id="core1-if0", device_id="core1", name="if0"))

        # 3. Link: Backbone → Core
        s.add(
            Link(
                id="link_bb_core",
                a_interface_id="backbone1-if0",
                b_interface_id="core1-if0",
                kind=LinkType.P2P,
                status=Status.UP,
            )
        )

        s.commit()
        print("[OK] Created backbone + core")

        # 4. Create 5 OLTs + links to core
        for olt_num in range(1, 6):
            olt_id = f"olt{olt_num}"
            olt = Device(
                id=olt_id,
                name=f"OLT-{olt_num}",
                type=DeviceType.OLT,
                status=Status.UP,
                provisioned=False,
            )
            s.add(olt)

            # OLT interfaces: if0 (uplink), if1-if3 (strands), mgmt0
            s.add(Interface(id=f"{olt_id}-if0", device_id=olt_id, name="if0"))
            for strand_local in range(1, 4):
                s.add(
                    Interface(
                        id=f"{olt_id}-if{strand_local}", device_id=olt_id, name=f"if{strand_local}"
                    )
                )
            s.add(Interface(id=f"{olt_id}-mgmt0", device_id=olt_id, name="mgmt0"))

            # Link: Core → OLT
            core_port = olt_num  # core1-if1, core1-if2, ..., core1-if5
            s.add(Interface(id=f"core1-if{core_port}", device_id="core1", name=f"if{core_port}"))
            s.add(
                Link(
                    id=f"link_core_olt{olt_num}",
                    a_interface_id=f"core1-if{core_port}",
                    b_interface_id=f"{olt_id}-if0",
                    kind=LinkType.FIBER,
                    status=Status.UP,
                )
            )

        s.commit()
        print("[OK] Created 5 OLTs with core links")

        # 5. Create 15 ODFs (3 per OLT) + links to OLTs
        strand_global = 1
        for olt_num in range(1, 6):
            for strand_local in range(1, 4):  # 3 strands per OLT
                odf_id = f"odf{strand_global}"
                odf = Device(
                    id=odf_id,
                    name=f"ODF-{strand_global}",
                    type=DeviceType.ODF,
                    status=Status.UP,
                    provisioned=False,
                )
                s.add(odf)

                # ODF interfaces: if0 (from OLT), if1-if67 (to ONTs)
                s.add(Interface(id=f"{odf_id}-if0", device_id=odf_id, name="if0"))
                for port in range(1, 68):  # 67 ports for ONTs
                    s.add(Interface(id=f"{odf_id}-if{port}", device_id=odf_id, name=f"if{port}"))

                # Link: OLT → ODF
                olt_id = f"olt{olt_num}"
                s.add(
                    Link(
                        id=f"link_olt{olt_num}_odf{strand_global}",
                        a_interface_id=f"{olt_id}-if{strand_local}",
                        b_interface_id=f"{odf_id}-if0",
                        kind=LinkType.FIBER,
                        status=Status.UP,
                    )
                )

                strand_global += 1

        s.commit()
        print("[OK] Created 15 ODFs with OLT links")

        # 6. Create 1000 ONTs + links to ODFs
        ont_count = 0
        for strand in range(1, 16):  # 15 strands
            # First 10 strands: 67 ONTs, last 5 strands: 66 ONTs (67*10 + 66*5 = 1000)
            onts_this_strand = 67 if strand <= 10 else 66

            for ont_num in range(1, onts_this_strand + 1):
                ont_id = f"ont{strand}_{ont_num}"
                ont = Device(
                    id=ont_id,
                    name=f"ONT-{strand}-{ont_num}",
                    type=DeviceType.ONT,
                    status=Status.UP,
                    provisioned=False,
                )
                s.add(ont)
                s.add(Interface(id=f"{ont_id}-if0", device_id=ont_id, name="if0"))

                # Link: ODF → ONT
                odf_id = f"odf{strand}"
                s.add(
                    Link(
                        id=f"link_odf{strand}_ont{strand}_{ont_num}",
                        a_interface_id=f"{odf_id}-if{ont_num}",
                        b_interface_id=f"{ont_id}-if0",
                        kind=LinkType.FIBER,
                        status=Status.UP,
                    )
                )

                ont_count += 1
                if ont_count % 100 == 0:
                    print(f"[PROGRESS] Created {ont_count}/1000 ONTs...")

        s.commit()
        print("[OK] Created 1000 ONTs with ODF links")

        # 7. Assign tariffs to all ONTs
        tariff = s.exec(select(Tariff).where(Tariff.id == 1)).first()
        if not tariff:
            print("[ERROR] Default tariff not found! Run with --seed")
            return 1

        onts = s.exec(select(Device).where(Device.type == DeviceType.ONT)).all()
        for ont in onts:
            ont.tariff_id = 1
        s.commit()
        print(f"[OK] Assigned tariffs to {len(onts)} ONTs")

        # 8. Provision devices (Core, 5 OLTs, 1000 ONTs)
        print("[PROVISION] Provisioning core router...")
        core_dev = s.get(Device, "core1")
        if core_dev:
            provision_device(s, core_dev)
        s.commit()

        for olt_num in range(1, 6):
            print(f"[PROVISION] Provisioning OLT{olt_num}...")
            olt_dev = s.get(Device, f"olt{olt_num}")
            if olt_dev:
                provision_device(s, olt_dev)
            s.commit()

        # NOTE: ODFs are PASSIVE devices (fiber distribution frames)
        # They do NOT get provisioned - only used for interface mapping!
        print("[INFO] ODFs are passive devices - no provisioning needed")

        print("[PROVISION] Provisioning 1000 ONTs (this will take ~30-60 seconds)...")
        for strand in range(1, 16):
            onts_this_strand = 67 if strand <= 10 else 66
            for ont_num in range(1, onts_this_strand + 1):
                ont_id = f"ont{strand}_{ont_num}"
                try:
                    ont_dev = s.get(Device, ont_id)
                    if ont_dev:
                        provision_device(s, ont_dev)
                except Exception as e:
                    print(f"[WARN] Could not provision {ont_id}: {e}")
            s.commit()  # Commit per strand
            print(f"[PROGRESS] Provisioned strand {strand}/15...")

        print(
            "[OK] Provisioned 1006 devices (1 backbone auto + 1 core + 5 OLTs + 1000 ONTs - 15 ODFs passive)"
        )

        # Summary
        devices = s.exec(select(Device)).all()
        links = s.exec(select(Link)).all()
        provisioned = sum(1 for d in devices if d.provisioned)
        print("\n[SUCCESS] 1000-ONT topology ready!")
        print(f"  Total devices: {len(devices)}")
        print(f"  Total links: {len(links)}")
        print(f"  Provisioned: {provisioned}")
        print("\nNext: Start Go engine manually and test")

        return 0


if __name__ == "__main__":
    sys.exit(main())
