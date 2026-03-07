"""Benchmark batch operations: links, devices, provision.

Usage:
    python tools/benchmark_batch_operations.py --scenario links_64
    python tools/benchmark_batch_operations.py --scenario provision_100
    python tools/benchmark_batch_operations.py --scenario all

Outputs:
    - Prints timing results to console
    - Saves JSON report to benchmarks/results_{timestamp}.json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, Interface, Link


def benchmark_create_links(count=64):
    """Benchmark creating N links simultaneously."""
    print(f"\n{'='*80}")
    print(f"BENCHMARK: Create {count} Links")
    print(f"{'='*80}")

    with get_session() as s:
        # Get existing devices with interfaces
        devs = s.exec(select(Device).limit(count + 10)).all()
        ifaces = s.exec(select(Interface).limit(count * 2)).all()

        if len(ifaces) < count * 2:
            print(f"⚠️  Not enough interfaces ({len(ifaces)}), need {count * 2}")
            return None

        # Prepare link data
        link_data = []
        for i in range(0, count * 2, 2):
            link_data.append(
                {
                    "a_interface_id": ifaces[i].id,
                    "b_interface_id": ifaces[i + 1].id,
                }
            )

        # Measure creation time
        start = time.perf_counter()

        created_links = []
        for ld in link_data:
            link = Link(
                a_interface_id=ld["a_interface_id"],
                b_interface_id=ld["b_interface_id"],
            )
            s.add(link)
            created_links.append(link)

        s.commit()

        end = time.perf_counter()
        duration_ms = (end - start) * 1000

        # Cleanup
        for link in created_links:
            s.delete(link)
        s.commit()

        print(f"✅ Created {count} links in {duration_ms:.2f}ms")
        print(f"   Average: {duration_ms / count:.2f}ms per link")

        return {
            "operation": "create_links",
            "count": count,
            "duration_ms": duration_ms,
            "avg_ms_per_item": duration_ms / count,
        }


def benchmark_batch_provision(count=100):
    """Benchmark batch provisioning N devices."""
    print(f"\n{'='*80}")
    print(f"BENCHMARK: Batch Provision {count} Devices")
    print(f"{'='*80}")

    with get_session() as s:
        # Get unprovisioned devices
        devs = s.exec(select(Device).where(Device.provisioned == False).limit(count)).all()

        if len(devs) < count:
            print(f"⚠️  Not enough unprovisioned devices ({len(devs)}), need {count}")
            return None

        device_ids = [d.id for d in devs[:count]]

        # Measure provision time (without API overhead)
        start = time.perf_counter()

        from backend.services.provisioning_service import provision_device

        for dev_id in device_ids:
            dev = s.get(Device, dev_id)
            provision_device(s, dev)

        s.commit()

        end = time.perf_counter()
        duration_ms = (end - start) * 1000

        # Revert provisioning
        for dev_id in device_ids:
            dev = s.get(Device, dev_id)
            dev.provisioned = False
        s.commit()

        print(f"✅ Provisioned {count} devices in {duration_ms:.2f}ms")
        print(f"   Average: {duration_ms / count:.2f}ms per device")

        return {
            "operation": "batch_provision",
            "count": count,
            "duration_ms": duration_ms,
            "avg_ms_per_item": duration_ms / count,
        }


def benchmark_status_recompute(device_count=100):
    """Benchmark status recomputation for N devices."""
    print(f"\n{'='*80}")
    print(f"BENCHMARK: Status Recompute ({device_count} devices)")
    print(f"{'='*80}")

    with get_session() as s:
        devs = s.exec(select(Device).limit(device_count)).all()
        device_ids = [d.id for d in devs]

        # Measure recompute time
        start = time.perf_counter()

        from backend.services.status_service import recompute_dirty

        dirty = type("DirtySet", (), {"devices": device_ids, "links": []})()
        recompute_dirty(s, dirty)

        end = time.perf_counter()
        duration_ms = (end - start) * 1000

        print(f"✅ Recomputed status for {device_count} devices in {duration_ms:.2f}ms")
        print(f"   Average: {duration_ms / device_count:.2f}ms per device")

        return {
            "operation": "status_recompute",
            "count": device_count,
            "duration_ms": duration_ms,
            "avg_ms_per_item": duration_ms / device_count,
        }


def benchmark_traffic_tick(ticks=10):
    """Benchmark N traffic ticks."""
    print(f"\n{'='*80}")
    print(f"BENCHMARK: Traffic Engine ({ticks} ticks)")
    print(f"{'='*80}")

    from backend.services.traffic_engine import ENGINE_SINGLETON

    durations = []

    for i in range(ticks):
        start = time.perf_counter()
        ENGINE_SINGLETON.run_tick()
        end = time.perf_counter()
        durations.append((end - start) * 1000)

    avg_ms = sum(durations) / len(durations)
    min_ms = min(durations)
    max_ms = max(durations)

    print("✅ Traffic ticks completed:")
    print(f"   Average: {avg_ms:.2f}ms")
    print(f"   Min: {min_ms:.2f}ms")
    print(f"   Max: {max_ms:.2f}ms")

    return {
        "operation": "traffic_tick",
        "count": ticks,
        "avg_ms": avg_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "all_durations_ms": durations,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        choices=["links_64", "provision_100", "status_100", "traffic_10", "all"],
        default="all",
        help="Which benchmark to run",
    )
    parser.add_argument("--output-dir", default="benchmarks", help="Output directory for results")
    args = parser.parse_args()

    init_db()

    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    results = {
        "timestamp": datetime.now().isoformat(),
        "benchmarks": [],
    }

    # Run requested benchmarks
    if args.scenario in ["links_64", "all"]:
        result = benchmark_create_links(count=64)
        if result:
            results["benchmarks"].append(result)

    if args.scenario in ["provision_100", "all"]:
        result = benchmark_batch_provision(count=100)
        if result:
            results["benchmarks"].append(result)

    if args.scenario in ["status_100", "all"]:
        result = benchmark_status_recompute(device_count=100)
        if result:
            results["benchmarks"].append(result)

    if args.scenario in ["traffic_10", "all"]:
        result = benchmark_traffic_tick(ticks=10)
        if result:
            results["benchmarks"].append(result)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"results_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✅ Results saved to: {output_file}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
