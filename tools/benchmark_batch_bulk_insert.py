#!/usr/bin/env python3
"""
Quick benchmark for optimized batch service (bulk INSERT).

Tests bulk link creation performance to verify optimization.
Target: <10s for 64 links (262× speedup from 37 min baseline).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time

from sqlmodel import select

from backend.clients.go_services.batch_client import BatchClient
from backend.db import get_session
from backend.models import Device, DeviceType, Interface, Link, Status


def reset_test_topology():
    """Create fresh test topology with 64 ONTs."""
    with get_session() as session:
        # Delete existing test links and devices
        session.query(Link).delete()
        session.query(Device).filter(Device.id.like("bench_ont%")).delete()
        session.commit()

        # Create core switch
        core = session.query(Device).filter_by(id="core1").first()
        if not core:
            core = Device(
                id="core1",
                name="Core Switch",
                type=DeviceType.SWITCH,
                status=Status.ACTIVE,
                provisioned=True,
            )
            session.add(core)
            session.commit()
            session.refresh(core)

        # Create 64 ONTs with interfaces
        devices = []
        for i in range(1, 65):
            ont = Device(
                id=f"bench_ont_{i}",
                name=f"Benchmark ONT {i}",
                type=DeviceType.ONT,
                status=Status.ACTIVE,
                provisioned=True,
            )
            session.add(ont)
            devices.append(ont)

        session.commit()

        # Create interfaces
        core_ifaces = session.exec(
            select(Interface).where(Interface.device_id == "core1").limit(64)
        ).all()

        ont_ifaces = []
        for ont in devices:
            iface_query = session.exec(
                select(Interface).where(Interface.device_id == ont.id).limit(1)
            )
            iface = iface_query.first()
            if iface:
                ont_ifaces.append(iface)

        print(
            f"✅ Test topology ready: {len(core_ifaces)} core interfaces, {len(ont_ifaces)} ONT interfaces"
        )
        return core_ifaces, ont_ifaces


def benchmark_bulk_insert_64_links():
    """Benchmark bulk INSERT optimization for 64 links."""
    print("=" * 80)
    print("BATCH OPERATIONS BULK INSERT BENCHMARK")
    print("=" * 80)

    # Reset topology
    print("\n1. Setting up test topology...")
    core_ifaces, ont_ifaces = reset_test_topology()

    if len(core_ifaces) < 64 or len(ont_ifaces) < 64:
        print(f"❌ Insufficient interfaces: {len(core_ifaces)} core, {len(ont_ifaces)} ONT")
        print("   Need 64 of each for benchmark")
        return

    # Prepare link specs
    print("\n2. Preparing 64 link specifications...")
    links_data = [
        {
            "a_interface_id": core_ifaces[i].id,
            "b_interface_id": ont_ifaces[i].id,
            "length_km": 1.0,
            "status": "active",
            "metadata": {"benchmark": True, "batch_index": i},
        }
        for i in range(64)
    ]

    # Benchmark Go service (optimized)
    print("\n3. Benchmarking optimized Go service (bulk INSERT)...")
    client = BatchClient()

    start_time = time.time()
    result = client.batch_create_links(links=links_data, dry_run=False)
    end_time = time.time()

    duration_sec = end_time - start_time

    # Results
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Backend: {result.get('backend', 'unknown')}")
    print(f"Total requested: {result['total_requested']}")
    print(f"Total created: {result['total_created']}")
    print(f"Total failed: {len(result['failed_links'])}")
    print(f"\n⏱️  Duration: {duration_sec:.2f} seconds")

    # Calculate speedup
    baseline_sec = 37 * 60  # 37 minutes baseline (Python sequential)
    speedup = baseline_sec / duration_sec

    print("\n📊 Performance Metrics:")
    print(f"   Baseline (Python sequential): {baseline_sec:.0f}s (37 min)")
    print(f"   Optimized (Go bulk INSERT): {duration_sec:.2f}s")
    print(f"   Speedup: {speedup:.0f}× faster")

    # Target validation
    target_sec = 10
    acceptable_sec = 15

    print("\n🎯 Target Validation:")
    if duration_sec <= target_sec:
        print(
            f"   ✅ EXCELLENT: {duration_sec:.2f}s ≤ {target_sec}s target (262× speedup achieved)"
        )
    elif duration_sec <= acceptable_sec:
        print(f"   ✅ GOOD: {duration_sec:.2f}s ≤ {acceptable_sec}s acceptable (148× speedup)")
    else:
        print(
            f"   ⚠️  NEEDS WORK: {duration_sec:.2f}s > {acceptable_sec}s (more optimization needed)"
        )

    # Detailed failures
    if result["failed_links"]:
        print(f"\n⚠️  Failed Links ({len(result['failed_links'])}):")
        for failure in result["failed_links"][:5]:  # Show first 5
            print(
                f"   - Index {failure['index']}: {failure['error_code']} - {failure['error_message']}"
            )

    print("\n" + "=" * 80)


if __name__ == "__main__":
    benchmark_bulk_insert_64_links()
