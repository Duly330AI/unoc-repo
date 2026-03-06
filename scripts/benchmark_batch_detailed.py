#!/usr/bin/env python3
"""
Detailed Benchmark: 64-Link Batch Creation with Timing Breakdown

Measures each phase separately:
  1. Topology Setup (1 Core + 64 OLTs)
  2. Link Specification Preparation
  3. gRPC Call → Go Service
  4. DB Verification
  5. Cleanup

Usage:
    python scripts/benchmark_batch_detailed.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select

from backend.clients.go_services.batch_client import get_batch_client
from backend.db import engine
from backend.models import Device, DeviceType, Interface, Link, Status


def main():
    print("=" * 80)
    print("📊 DETAILED 64-LINK BATCH BENCHMARK")
    print("=" * 80)
    print()

    times = {}

    # Phase 1: Setup
    print("Phase 1: Topology Setup")
    start = time.time()
    with Session(engine) as session:
        core = Device(
            id="detail_core1",
            name="Detail Core",
            type=DeviceType.CORE_ROUTER,
            status=Status.UP,
            provisioned=True,
        )
        session.add(core)

        core_ifaces = []
        olt_ifaces = []

        for i in range(1, 65):
            # Core interface
            c_if = Interface(
                id=f"detail_core1_eth{i}",
                name=f"eth{i}",
                device_id="detail_core1",
            )
            session.add(c_if)
            core_ifaces.append(c_if.id)

            # OLT device + interface
            olt = Device(
                id=f"detail_olt{i}",
                name=f"Detail OLT {i}",
                type=DeviceType.OLT,
                status=Status.UP,
                provisioned=True,
            )
            session.add(olt)

            o_if = Interface(
                id=f"detail_olt{i}_up0",
                name="up0",
                device_id=f"detail_olt{i}",
            )
            session.add(o_if)
            olt_ifaces.append(o_if.id)

        session.commit()

    times["setup"] = time.time() - start
    print(f"  ⏱️  {times['setup']:.3f}s\n")

    # Phase 2: Prepare link data
    print("Phase 2: Prepare Link Specs")
    start = time.time()
    links_data = [
        {
            "a_interface_id": core_ifaces[i],
            "b_interface_id": olt_ifaces[i],
            "length_km": 5.0,
            "status": "UP",
            "metadata": {"idx": str(i)},
        }
        for i in range(64)
    ]
    times["prepare"] = time.time() - start
    print(f"  ⏱️  {times['prepare']:.3f}s\n")

    # Phase 3: Batch Create (CRITICAL MEASUREMENT)
    print("Phase 3: Batch Create (Go Service)")
    print("  📡 Calling batch_create_links...")

    client = get_batch_client()

    start = time.time()
    result = client.batch_create_links(
        links=links_data,
        dry_run=False,
        skip_optical_recompute=False,
    )
    times["batch_create"] = time.time() - start

    print(f"  ⏱️  {times['batch_create']:.3f}s")
    print(f"  ✅ Created: {result['total_created']}/{result['total_requested']}")
    print(f"  🔧 Backend: {result['backend']}")
    print()

    # Phase 4: DB Verification
    print("Phase 4: DB Verification")
    start = time.time()
    with Session(engine) as session:
        link_count = session.exec(select(Link).where(Link.id.startswith("detail_"))).all()
        link_count = len(link_count)
    times["verify"] = time.time() - start
    print(f"  ⏱️  {times['verify']:.3f}s")
    print(f"  📊 Links in DB: {link_count}")
    print()

    # Phase 5: Cleanup
    print("Phase 5: Cleanup")
    start = time.time()
    with Session(engine) as session:
        # Delete links
        links = session.exec(select(Link).where(Link.id.startswith("detail_"))).all()
        for link in links:
            session.delete(link)

        # Delete interfaces
        ifaces = session.exec(select(Interface).where(Interface.id.startswith("detail_"))).all()
        for iface in ifaces:
            session.delete(iface)

        # Delete devices
        devices = session.exec(select(Device).where(Device.id.startswith("detail_"))).all()
        for device in devices:
            session.delete(device)

        session.commit()
    times["cleanup"] = time.time() - start
    print(f"  ⏱️  {times['cleanup']:.3f}s\n")

    # Summary
    print("=" * 80)
    print("📋 TIMING BREAKDOWN")
    print("=" * 80)
    print(f"Setup (topology):       {times['setup']:.3f}s")
    print(f"Prepare (link specs):   {times['prepare']:.3f}s")
    print(f"Batch Create (gRPC):    {times['batch_create']:.3f}s  ⭐ CORE METRIC")
    print(f"Verify (DB query):      {times['verify']:.3f}s")
    print(f"Cleanup:                {times['cleanup']:.3f}s")
    print("-" * 80)
    total = sum(times.values())
    print(f"TOTAL:                  {total:.3f}s")
    print()

    # Performance Analysis
    batch_create_ms = times["batch_create"] * 1000
    per_link_ms = batch_create_ms / 64

    print("=" * 80)
    print("🚀 PERFORMANCE ANALYSIS")
    print("=" * 80)
    print(f"Batch Create Time:      {batch_create_ms:.1f}ms")
    print(f"Per Link:               {per_link_ms:.2f}ms")
    print()

    # Baseline comparison
    python_baseline_s = 37 * 60
    speedup = python_baseline_s / times["batch_create"]

    print(f"Python Baseline:        {python_baseline_s}s (37 minutes)")
    print(f"Go Batch Service:       {times['batch_create']:.3f}s")
    print(f"Speedup:                {speedup:.0f}×")
    print()

    if times["batch_create"] <= 0.01:
        print("Target:                 ✅ EXCELLENT (<10ms!)")
    elif times["batch_create"] <= 0.1:
        print("Target:                 ✅ EXCELLENT (<100ms)")
    elif times["batch_create"] <= 1.0:
        print("Target:                 ✅ GOOD (<1s)")
    elif times["batch_create"] <= 10.0:
        print("Target:                 ✅ TARGET ACHIEVED (<10s)")
    else:
        print("Target:                 ⚠️  NEEDS OPTIMIZATION (>10s)")

    print("=" * 80)


if __name__ == "__main__":
    main()
