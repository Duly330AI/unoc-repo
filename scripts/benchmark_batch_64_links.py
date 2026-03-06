#!/usr/bin/env python3
"""
Benchmark: 64-Link Batch Creation Performance Test

Measures end-to-end performance of batch link creation:
  Request → Bulk INSERT → Optical Recompute → Response

Target: <10 seconds (262× speedup vs Python sequential 37 min)
Acceptable: <15 seconds (148× speedup)

Usage:
    python scripts/benchmark_batch_64_links.py
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select

from backend.clients.go_services.batch_client import get_batch_client
from backend.db import engine  # Use global engine from db.py
from backend.models import Device, DeviceType, Interface, Link, Status


def setup_benchmark_topology(session: Session) -> tuple[list[str], list[str]]:
    """
    Create benchmark topology: 1 Core + 64 OLTs with interfaces.

    Returns:
        (core_interface_ids, olt_interface_ids): Lists of interface IDs for linking
    """
    print("📦 Setting up benchmark topology...")
    start = time.time()

    # Create Core Switch with 64 interfaces
    core = Device(
        id="bench_core1",
        name="Benchmark Core Switch",
        type=DeviceType.CORE_ROUTER,  # Use CORE_ROUTER (no CORE_SWITCH in enum)
        status=Status.UP,
        provisioned=True,
    )
    session.add(core)

    core_interfaces = []
    for i in range(1, 65):
        iface = Interface(
            id=f"bench_core1_eth{i}",
            name=f"eth{i}",
            device_id="bench_core1",
        )
        session.add(iface)
        core_interfaces.append(iface.id)

    # Create 64 OLTs, each with 1 interface
    olt_interfaces = []
    for i in range(1, 65):
        olt = Device(
            id=f"bench_olt{i}",
            name=f"Benchmark OLT {i}",
            type=DeviceType.OLT,
            status=Status.UP,
            provisioned=True,
        )
        session.add(olt)

        iface = Interface(
            id=f"bench_olt{i}_uplink0",
            name="uplink0",
            device_id=f"bench_olt{i}",
        )
        session.add(iface)
        olt_interfaces.append(iface.id)

    session.commit()

    duration = time.time() - start
    print(f"✅ Created 1 Core + 64 OLTs with interfaces ({duration:.2f}s)")
    print(f"   Core interfaces: {len(core_interfaces)}")
    print(f"   OLT interfaces: {len(olt_interfaces)}")

    return core_interfaces, olt_interfaces


def cleanup_benchmark_topology(session: Session) -> None:
    """Remove all benchmark devices, interfaces, and links."""
    print("\n🧹 Cleaning up benchmark topology...")
    start = time.time()

    # Delete all links first (to avoid FK constraints)
    links = session.exec(select(Link).where(Link.id.startswith("bench_"))).all()
    for link in links:
        session.delete(link)

    # Delete interfaces
    interfaces = session.exec(select(Interface).where(Interface.id.startswith("bench_"))).all()
    for iface in interfaces:
        session.delete(iface)

    # Delete devices (last, due to FKs)
    devices = session.exec(select(Device).where(Device.id.startswith("bench_"))).all()
    for device in devices:
        session.delete(device)

    session.commit()

    duration = time.time() - start
    print(f"✅ Cleanup complete ({duration:.2f}s)")


def run_benchmark() -> dict:
    """
    Run the 64-link batch creation benchmark.

    Returns:
        dict with benchmark results (duration, speedup, links created, etc.)
    """
    print("=" * 80)
    print("🚀 BATCH OPERATIONS BENCHMARK - 64 Link Creation")
    print("=" * 80)
    print()

    # Phase 1: Setup topology
    with Session(engine) as session:
        core_ifaces, olt_ifaces = setup_benchmark_topology(session)

    # Phase 2: Prepare link data (64 links)
    print("\n📋 Preparing 64 link specifications...")
    links_data = [
        {
            "a_interface_id": core_ifaces[i],
            "b_interface_id": olt_ifaces[i],
            "length_km": 5.0 + (i * 0.1),  # Varying lengths (5.0 - 11.3 km)
            "status": "UP",
            "metadata": {
                "fiber_type": "SM",
                "benchmark": "true",
                "index": str(i),
            },
        }
        for i in range(64)
    ]
    print(f"✅ Prepared {len(links_data)} link specifications")

    # Phase 3: Batch Create (THE BENCHMARK!)
    print("\n" + "=" * 80)
    print("⏱️  BENCHMARK START - Creating 64 links via Go Batch Service")
    print("=" * 80)

    client = get_batch_client()

    start_time = time.time()

    result = client.batch_create_links(
        links=links_data,
        dry_run=False,
        skip_optical_recompute=False,  # Include optical recompute (critical!)
    )

    duration = time.time() - start_time

    print("=" * 80)
    print(f"⏱️  BENCHMARK COMPLETE - Duration: {duration:.2f}s")
    print("=" * 80)

    # Phase 4: Analyze results
    print("\n📊 RESULTS:")
    print("-" * 80)
    print(f"Backend:            {result.get('backend', 'unknown')}")
    print(f"Total Requested:    {result.get('total_requested', 0)}")
    print(f"Total Created:      {result.get('total_created', 0)}")
    print(f"Total Failed:       {len(result.get('failed_links', []))}")
    print(f"Duration:           {duration:.2f}s")
    print(f"Avg per link:       {(duration / 64) * 1000:.1f}ms")

    # Calculate speedup
    python_baseline_seconds = 37 * 60  # 37 minutes baseline
    speedup = python_baseline_seconds / duration

    print("\n🚀 PERFORMANCE:")
    print("-" * 80)
    print(f"Python Baseline:    {python_baseline_seconds}s (37 minutes)")
    print(f"Go Batch Service:   {duration:.2f}s")
    print(f"Speedup:            {speedup:.0f}× faster")

    # Target evaluation
    if duration <= 10:
        print("Status:             ✅ EXCELLENT (≤10s target achieved!)")
    elif duration <= 15:
        print("Status:             ✅ GOOD (≤15s acceptable threshold)")
    elif duration <= 30:
        print("Status:             ⚠️  ACCEPTABLE (still much faster than baseline)")
    else:
        print("Status:             ❌ NEEDS OPTIMIZATION (>30s)")

    print("-" * 80)

    # Detailed failures (if any)
    if result.get("failed_links"):
        print("\n⚠️  FAILED LINKS:")
        for i, failure in enumerate(result["failed_links"][:5], 1):  # Show first 5
            print(
                f"  {i}. Index {failure.get('index')}: {failure.get('error_code')} - {failure.get('error_message')}"
            )
        if len(result["failed_links"]) > 5:
            print(f"  ... and {len(result['failed_links']) - 5} more")

    # Phase 5: Cleanup
    with Session(engine) as session:
        cleanup_benchmark_topology(session)

    return {
        "duration": duration,
        "speedup": speedup,
        "links_created": result.get("total_created", 0),
        "links_failed": len(result.get("failed_links", [])),
        "backend": result.get("backend", "unknown"),
        "target_achieved": duration <= 10,
        "acceptable": duration <= 15,
    }


def main():
    """Run the benchmark and exit with appropriate code."""
    try:
        results = run_benchmark()

        print("\n" + "=" * 80)
        print("📋 BENCHMARK SUMMARY")
        print("=" * 80)
        print(f"Duration:      {results['duration']:.2f}s")
        print(f"Speedup:       {results['speedup']:.0f}×")
        print(f"Links Created: {results['links_created']}/64")
        print(f"Backend:       {results['backend']}")

        if results["target_achieved"]:
            print("\n✅ TARGET ACHIEVED: <10s response time!")
            exit_code = 0
        elif results["acceptable"]:
            print("\n✅ ACCEPTABLE: <15s response time")
            exit_code = 0
        else:
            print("\n⚠️  OPTIMIZATION NEEDED: >15s response time")
            exit_code = 1

        print("=" * 80)
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
