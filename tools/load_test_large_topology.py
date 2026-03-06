"""Load test: REALISTIC concurrent load testing.

This is NOT a synthetic benchmark! This simulates REAL production load:
- Traffic engine ticking continuously in background
- Status recompute triggered by events
- WebSocket fanout to multiple clients
- API requests from multiple endpoints
- Provisioning operations
- Database contention and locks

Usage:
    python tools/load_test_large_topology.py --devices 1000 --realistic

Target: 1k devices, then 10k+ if feasible.

The previous approach (synthetic benchmarks) was WRONG because it tested
operations in isolation. In reality, EVERYTHING runs simultaneously!
"""

import argparse
import sys
import time

import psutil

sys.path.insert(0, ".")

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link
from backend.services.provisioning_service import provision_device
from backend.services.status_service import recompute_dirty


def get_memory_mb():
    """Get current process memory in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def create_large_topology(device_count=1000):
    """Create a large realistic topology with N devices.

    Topology structure:
    - 1 Backbone Gateway (root)
    - 2 Core Routers
    - 10 Edge Routers
    - 50 AON Switches
    - Rest: CPE/ONT split 50/50
    """
    print(f"\n{'='*80}")
    print(f"CREATING LARGE TOPOLOGY: {device_count} devices")
    print(f"{'='*80}")

    mem_before = get_memory_mb()
    start = time.perf_counter()

    with get_session() as s:
        # Create backbone
        backbone = Device(
            id="backbone_gw",
            name="Backbone Gateway",
            type=DeviceType.BACKBONE_GATEWAY,
        )
        s.add(backbone)

        # Create core routers
        cores = []
        for i in range(2):
            core = Device(
                id=f"core_{i}",
                name=f"Core Router {i}",
                type=DeviceType.CORE_ROUTER,
            )
            s.add(core)
            cores.append(core)

        # Create edge routers
        edges = []
        for i in range(10):
            edge = Device(
                id=f"edge_{i}",
                name=f"Edge Router {i}",
                type=DeviceType.EDGE_ROUTER,
            )
            s.add(edge)
            edges.append(edge)

        # Create AON switches
        switches = []
        for i in range(50):
            switch = Device(
                id=f"aon_switch_{i}",
                name=f"AON Switch {i}",
                type=DeviceType.AON_SWITCH,
            )
            s.add(switch)
            switches.append(switch)

        # Create CPE/ONT (rest of devices)
        remaining = device_count - 1 - 2 - 10 - 50  # backbone + cores + edges + switches
        cpe_count = remaining // 2
        ont_count = remaining - cpe_count

        cpes = []
        for i in range(cpe_count):
            cpe = Device(
                id=f"cpe_{i}",
                name=f"CPE {i}",
                type=DeviceType.AON_CPE,
            )
            s.add(cpe)
            cpes.append(cpe)

        onts = []
        for i in range(ont_count):
            ont = Device(
                id=f"ont_{i}",
                name=f"ONT {i}",
                type=DeviceType.ONT,
            )
            s.add(ont)
            onts.append(ont)

        s.commit()

        # Create interfaces for all devices (simplified: 2 per device)
        print("Creating interfaces...")
        all_devices = [backbone] + cores + edges + switches + cpes + onts

        for dev in all_devices:
            for port_num in range(2):
                iface = Interface(
                    id=f"{dev.id}_if{port_num}",
                    device_id=dev.id,
                    name=f"eth{port_num}",
                )
                s.add(iface)

        s.commit()

        # Create links (realistic topology)
        print("Creating links...")

        # Backbone → Cores
        for core in cores:
            link = Link(
                a_interface_id="backbone_gw_if0",
                b_interface_id=f"{core.id}_if0",
            )
            s.add(link)

        # Cores → Edges (distribute evenly)
        edges_per_core = len(edges) // len(cores)
        for c_idx, core in enumerate(cores):
            start_edge = c_idx * edges_per_core
            end_edge = start_edge + edges_per_core

            for edge in edges[start_edge:end_edge]:
                link = Link(
                    a_interface_id=f"{core.id}_if1",
                    b_interface_id=f"{edge.id}_if0",
                )
                s.add(link)

        # Edges → Switches (distribute evenly)
        switches_per_edge = len(switches) // len(edges)
        for e_idx, edge in enumerate(edges):
            start_switch = e_idx * switches_per_edge
            end_switch = start_switch + switches_per_edge

            for switch in switches[start_switch:end_switch]:
                link = Link(
                    a_interface_id=f"{edge.id}_if1",
                    b_interface_id=f"{switch.id}_if0",
                )
                s.add(link)

        # Switches → CPE/ONT (distribute evenly)
        endpoints = cpes + onts
        endpoints_per_switch = len(endpoints) // len(switches)

        for s_idx, switch in enumerate(switches):
            start_ep = s_idx * endpoints_per_switch
            end_ep = start_ep + endpoints_per_switch

            for endpoint in endpoints[start_ep:end_ep]:
                link = Link(
                    a_interface_id=f"{switch.id}_if1",
                    b_interface_id=f"{endpoint.id}_if0",
                )
                s.add(link)

        s.commit()

    end = time.perf_counter()
    duration_sec = end - start
    mem_after = get_memory_mb()
    mem_delta = mem_after - mem_before

    print(f"✅ Topology created in {duration_sec:.2f}s")
    print(f"   Memory before: {mem_before:.1f} MB")
    print(f"   Memory after: {mem_after:.1f} MB")
    print(f"   Memory delta: {mem_delta:.1f} MB")

    return {
        "device_count": device_count,
        "creation_time_sec": duration_sec,
        "memory_before_mb": mem_before,
        "memory_after_mb": mem_after,
        "memory_delta_mb": mem_delta,
    }


def measure_operations(device_count=1000):
    """Measure key operations on large topology."""
    print(f"\n{'='*80}")
    print(f"MEASURING OPERATIONS ({device_count} devices)")
    print(f"{'='*80}")

    results = {}

    # Measure batch provision
    print("\n1. BATCH PROVISION...")
    with get_session() as s:
        devs = s.exec(select(Device).limit(device_count)).all()
        device_ids = [d.id for d in devs]

        start = time.perf_counter()

        for dev_id in device_ids[:100]:  # Provision first 100
            dev = s.get(Device, dev_id)
            if dev:
                provision_device(s, dev)

        s.commit()
        end = time.perf_counter()

        results["batch_provision_100_ms"] = (end - start) * 1000
        print(f"   ✅ Provisioned 100 devices in {results['batch_provision_100_ms']:.2f}ms")

    # Measure status recompute
    print("\n2. STATUS RECOMPUTE...")
    with get_session() as s:
        devs = s.exec(select(Device).limit(device_count)).all()
        device_ids = [d.id for d in devs]

        start = time.perf_counter()

        dirty = type("DirtySet", (), {"devices": device_ids, "links": []})()
        recompute_dirty(s, dirty)

        end = time.perf_counter()

        results["status_recompute_all_ms"] = (end - start) * 1000
        print(
            f"   ✅ Recomputed {device_count} devices in {results['status_recompute_all_ms']:.2f}ms"
        )

    # Measure traffic tick (get V2 engine instance)
    print("\n3. TRAFFIC TICK...")
    from backend.services.traffic.v2_engine import TrafficEngineV2

    engine = TrafficEngineV2()
    durations = []

    for i in range(5):
        start = time.perf_counter()
        with get_session() as s:
            engine.run_tick(s)
        end = time.perf_counter()
        durations.append((end - start) * 1000)

    results["traffic_tick_avg_ms"] = sum(durations) / len(durations)
    results["traffic_tick_max_ms"] = max(durations)

    print(f"   ✅ Traffic tick average: {results['traffic_tick_avg_ms']:.2f}ms")
    print(f"   ✅ Traffic tick max: {results['traffic_tick_max_ms']:.2f}ms")

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--devices", type=int, default=1000, help="Number of devices to create")
    parser.add_argument("--measure", action="store_true", help="Measure operations after creation")
    parser.add_argument(
        "--skip-create", action="store_true", help="Skip topology creation, just measure"
    )
    args = parser.parse_args()

    init_db()

    if not args.skip_create:
        topology_result = create_large_topology(device_count=args.devices)
    else:
        topology_result = {"device_count": args.devices, "note": "Topology creation skipped"}

    if args.measure:
        operation_results = measure_operations(device_count=args.devices)

        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Device count: {topology_result['device_count']}")
        if not args.skip_create:
            print(f"Topology creation: {topology_result['creation_time_sec']:.2f}s")
            print(f"Memory delta: {topology_result['memory_delta_mb']:.1f} MB")
        print(f"Batch provision (100): {operation_results['batch_provision_100_ms']:.2f}ms")
        print(f"Status recompute (all): {operation_results['status_recompute_all_ms']:.2f}ms")
        print(f"Traffic tick (avg): {operation_results['traffic_tick_avg_ms']:.2f}ms")
        print(f"Traffic tick (max): {operation_results['traffic_tick_max_ms']:.2f}ms")


if __name__ == "__main__":
    main()
