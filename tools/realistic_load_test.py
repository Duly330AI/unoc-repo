"""REALISTIC LOAD TEST - Everything runs simultaneously!

This is NOT a synthetic benchmark. This simulates REAL production:
- Traffic engine ticking in background (every 5s)
- Status recompute on every event
- WebSocket fanout to clients
- API requests from multiple endpoints
- Provisioning operations running
- Database locks and contention

The problem with previous tests: They measured operations in ISOLATION.
In reality, EVERYTHING runs at the SAME TIME with contention!

Usage:
    # Start realistic load test with 1000 devices
    python tools/realistic_load_test.py --devices 1000 --duration 300

    # This will:
    # 1. Create topology
    # 2. Start background workers (traffic, status, API simulation)
    # 3. Run for N seconds while measuring
    # 4. Report realistic performance under REAL load
"""

import argparse
import json
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")

from sqlmodel import col, select

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link
from backend.services.provisioning_service import provision_device
from backend.services.status_service import recompute_dirty


class RealisticLoadTest:
    """Simulates real production load with everything running simultaneously."""

    def __init__(self, device_count=1000):
        self.device_count = device_count
        self.running = False
        self.metrics = defaultdict(list)
        self.lock = threading.Lock()

    def log_metric(self, name, value_ms):
        """Thread-safe metric logging."""
        with self.lock:
            self.metrics[name].append(
                {
                    "timestamp": time.time(),
                    "value_ms": value_ms,
                }
            )

    def create_topology(self):
        """Create realistic topology."""
        print(f"\n{'='*80}")
        print(f"CREATING TOPOLOGY: {self.device_count} devices")
        print(f"{'='*80}")

        start = time.perf_counter()

        with get_session() as s:
            # Backbone
            backbone = Device(
                id="backbone_gw",
                name="Backbone Gateway",
                type=DeviceType.BACKBONE_GATEWAY,
            )
            s.add(backbone)

            # Core routers (2)
            cores = []
            for i in range(2):
                core = Device(
                    id=f"core_{i}",
                    name=f"Core Router {i}",
                    type=DeviceType.CORE_ROUTER,
                )
                s.add(core)
                cores.append(core)

            # Edge routers (10)
            edges = []
            for i in range(10):
                edge = Device(
                    id=f"edge_{i}",
                    name=f"Edge Router {i}",
                    type=DeviceType.EDGE_ROUTER,
                )
                s.add(edge)
                edges.append(edge)

            # AON switches (50)
            switches = []
            for i in range(50):
                switch = Device(
                    id=f"aon_switch_{i}",
                    name=f"AON Switch {i}",
                    type=DeviceType.AON_SWITCH,
                )
                s.add(switch)
                switches.append(switch)

            # CPE/ONT (rest)
            remaining = self.device_count - 1 - 2 - 10 - 50
            cpe_count = remaining // 2
            ont_count = remaining - cpe_count

            endpoints = []
            for i in range(cpe_count):
                cpe = Device(
                    id=f"cpe_{i}",
                    name=f"CPE {i}",
                    type=DeviceType.AON_CPE,
                )
                s.add(cpe)
                endpoints.append(cpe)

            for i in range(ont_count):
                ont = Device(
                    id=f"ont_{i}",
                    name=f"ONT {i}",
                    type=DeviceType.ONT,
                )
                s.add(ont)
                endpoints.append(ont)

            s.commit()

            # Interfaces (2 per device) - BULK INSERT for performance
            all_devices = [backbone] + cores + edges + switches + endpoints
            interfaces = []
            for dev in all_devices:
                for port_num in range(2):
                    iface = Interface(
                        id=f"{dev.id}_if{port_num}",
                        device_id=dev.id,
                        name=f"eth{port_num}",
                    )
                    interfaces.append(iface)

            # Bulk insert all interfaces at once
            s.bulk_save_objects(interfaces)
            s.commit()

            # Links (hierarchical topology) - BULK INSERT for performance
            links = []
            link_id = 0

            # Backbone → Cores
            for core in cores:
                links.append(
                    Link(
                        id=f"link_{link_id}",
                        a_interface_id="backbone_gw_if0",
                        b_interface_id=f"{core.id}_if0",
                    )
                )
                link_id += 1

            # Cores → Edges
            edges_per_core = len(edges) // len(cores)
            for c_idx, core in enumerate(cores):
                start_edge = c_idx * edges_per_core
                end_edge = start_edge + edges_per_core

                for edge in edges[start_edge:end_edge]:
                    links.append(
                        Link(
                            id=f"link_{link_id}",
                            a_interface_id=f"{core.id}_if1",
                            b_interface_id=f"{edge.id}_if0",
                        )
                    )
                    link_id += 1

            # Edges → Switches
            switches_per_edge = len(switches) // len(edges)
            for e_idx, edge in enumerate(edges):
                start_switch = e_idx * switches_per_edge
                end_switch = start_switch + switches_per_edge

                for switch in switches[start_switch:end_switch]:
                    links.append(
                        Link(
                            id=f"link_{link_id}",
                            a_interface_id=f"{edge.id}_if1",
                            b_interface_id=f"{switch.id}_if0",
                        )
                    )
                    link_id += 1

            # Switches → Endpoints
            endpoints_per_switch = len(endpoints) // len(switches)
            for s_idx, switch in enumerate(switches):
                start_ep = s_idx * endpoints_per_switch
                end_ep = start_ep + endpoints_per_switch

                for endpoint in endpoints[start_ep:end_ep]:
                    links.append(
                        Link(
                            id=f"link_{link_id}",
                            a_interface_id=f"{switch.id}_if1",
                            b_interface_id=f"{endpoint.id}_if0",
                        )
                    )
                    link_id += 1

            # Bulk insert all links at once
            s.bulk_save_objects(links)
            s.commit()

        duration = time.perf_counter() - start
        print(f"✅ Topology created in {duration:.2f}s")
        return duration

    def background_traffic_worker(self):
        """Simulates traffic engine ticking every 5 seconds."""
        print("🚀 Starting background traffic worker (tick every 5s)...")

        # Import and create V2 engine instance
        try:
            from backend.services.traffic.v2_engine import TrafficEngine

            engine = TrafficEngine()
        except Exception as e:
            print(f"   ❌ Failed to create traffic engine: {e}")
            return

        while self.running:
            start = time.perf_counter()

            try:
                # V2 engine uses run_tick() which handles its own session
                engine.run_tick()

                duration_ms = (time.perf_counter() - start) * 1000
                self.log_metric("traffic_tick", duration_ms)

                if duration_ms > 100:
                    print(f"   ⚠️  SLOW traffic tick: {duration_ms:.0f}ms")

            except Exception as e:
                print(f"   ❌ Traffic tick error: {e}")

            # Sleep 5s (or remaining time)
            elapsed = time.perf_counter() - start
            sleep_time = max(0, 5.0 - elapsed)
            time.sleep(sleep_time)

    def background_status_worker(self):
        """Simulates status recompute on events (every 2s)."""
        print("🚀 Starting background status worker (recompute every 2s)...")

        while self.running:
            start = time.perf_counter()

            try:
                with get_session() as s:
                    # Get random 50 devices as "dirty"
                    devs = s.exec(select(Device).limit(50)).all()
                    device_ids = [d.id for d in devs]

                    dirty = type("DirtySet", (), {"devices": device_ids, "links": []})()
                    recompute_dirty(s, dirty)
                    s.commit()

                duration_ms = (time.perf_counter() - start) * 1000
                self.log_metric("status_recompute", duration_ms)

                if duration_ms > 100:
                    print(f"   ⚠️  SLOW status recompute: {duration_ms:.0f}ms")

            except Exception as e:
                print(f"   ❌ Status recompute error: {e}")

            # Sleep 2s
            elapsed = time.perf_counter() - start
            sleep_time = max(0, 2.0 - elapsed)
            time.sleep(sleep_time)

    def background_api_worker(self):
        """Simulates API requests (list devices, links, metrics every 1s)."""
        print("🚀 Starting background API worker (queries every 1s)...")

        while self.running:
            start = time.perf_counter()

            try:
                with get_session() as s:
                    # Simulate /api/devices
                    devs = s.exec(select(Device).limit(100)).all()

                    # Simulate /api/links
                    links = s.exec(select(Link).limit(100)).all()

                    # Simulate /api/metrics/snapshot
                    # (would normally call traffic engine)

                duration_ms = (time.perf_counter() - start) * 1000
                self.log_metric("api_queries", duration_ms)

            except Exception as e:
                print(f"   ❌ API query error: {e}")

            # Sleep 1s
            elapsed = time.perf_counter() - start
            sleep_time = max(0, 1.0 - elapsed)
            time.sleep(sleep_time)

    def background_provision_worker(self):
        """Simulates provision/unprovision operations (every 10s)."""
        print("🚀 Starting background provision worker (provision every 10s)...")

        while self.running:
            start = time.perf_counter()

            try:
                with get_session() as s:
                    # Pick random 10 devices to provision
                    devs = s.exec(
                        select(Device)
                        .where(col(Device.type).in_([DeviceType.AON_CPE, DeviceType.ONT]))
                        .limit(10)
                    ).all()

                    for dev in devs:
                        # Just provision all (realistic: many provision ops)
                        provision_device(s, dev)

                    s.commit()

                duration_ms = (time.perf_counter() - start) * 1000
                self.log_metric("provisioning", duration_ms)

                if duration_ms > 200:
                    print(f"   ⚠️  SLOW provisioning: {duration_ms:.0f}ms")

            except Exception as e:
                print(f"   ❌ Provisioning error: {e}")

            # Sleep 10s
            elapsed = time.perf_counter() - start
            sleep_time = max(0, 10.0 - elapsed)
            time.sleep(sleep_time)

    def run_load_test(self, duration_sec=300):
        """Run realistic load test for N seconds."""
        print(f"\n{'='*80}")
        print(f"REALISTIC LOAD TEST - Duration: {duration_sec}s")
        print(f"{'='*80}")
        print("\nStarting background workers:")
        print("  - Traffic engine (tick every 5s)")
        print("  - Status recompute (every 2s)")
        print("  - API queries (every 1s)")
        print("  - Provisioning ops (every 10s)")
        print("\nAll workers run SIMULTANEOUSLY with DB contention!")
        print(f"{'='*80}\n")

        self.running = True

        # Start background workers
        workers = [
            threading.Thread(target=self.background_traffic_worker, daemon=True),
            threading.Thread(target=self.background_status_worker, daemon=True),
            threading.Thread(target=self.background_api_worker, daemon=True),
            threading.Thread(target=self.background_provision_worker, daemon=True),
        ]

        for w in workers:
            w.start()

        # Run for duration
        start_time = time.time()
        try:
            while time.time() - start_time < duration_sec:
                elapsed = time.time() - start_time
                remaining = duration_sec - elapsed
                print(
                    f"⏱️  Running... {elapsed:.0f}s / {duration_sec}s (remaining: {remaining:.0f}s)"
                )
                time.sleep(10)

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user!")

        finally:
            print("\n🛑 Stopping workers...")
            self.running = False

            # Wait for workers to finish (max 10s)
            for w in workers:
                w.join(timeout=10)

        # Calculate statistics
        return self.calculate_statistics()

    def calculate_statistics(self):
        """Calculate statistics from collected metrics."""
        print(f"\n{'='*80}")
        print("RESULTS - Realistic Load Under Contention")
        print(f"{'='*80}\n")

        stats = {}

        for metric_name, samples in self.metrics.items():
            if not samples:
                continue

            values = [s["value_ms"] for s in samples]

            stats[metric_name] = {
                "count": len(values),
                "avg_ms": sum(values) / len(values),
                "min_ms": min(values),
                "max_ms": max(values),
                "p50_ms": sorted(values)[len(values) // 2],
                "p95_ms": (
                    sorted(values)[int(len(values) * 0.95)] if len(values) > 20 else max(values)
                ),
                "p99_ms": (
                    sorted(values)[int(len(values) * 0.99)] if len(values) > 100 else max(values)
                ),
            }

            print(f"{metric_name}:")
            print(f"  Count:   {stats[metric_name]['count']}")
            print(f"  Avg:     {stats[metric_name]['avg_ms']:.2f}ms")
            print(f"  Min:     {stats[metric_name]['min_ms']:.2f}ms")
            print(f"  Max:     {stats[metric_name]['max_ms']:.2f}ms")
            print(f"  p50:     {stats[metric_name]['p50_ms']:.2f}ms")
            print(f"  p95:     {stats[metric_name]['p95_ms']:.2f}ms")
            print(f"  p99:     {stats[metric_name]['p99_ms']:.2f}ms")
            print()

        return stats

    def save_results(self, stats, duration_sec):
        """Save results to JSON."""
        output_dir = Path("load_test_results")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = (
            output_dir / f"realistic_load_{self.device_count}dev_{duration_sec}s_{timestamp}.json"
        )

        result = {
            "device_count": self.device_count,
            "duration_sec": duration_sec,
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "raw_metrics": {k: v for k, v in self.metrics.items()},
        }

        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"\n💾 Results saved to: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(description="Realistic load test with concurrent operations")
    parser.add_argument("--devices", type=int, default=1000, help="Number of devices")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--skip-create", action="store_true", help="Skip topology creation")
    args = parser.parse_args()

    init_db()

    test = RealisticLoadTest(device_count=args.devices)

    if not args.skip_create:
        test.create_topology()

    stats = test.run_load_test(duration_sec=args.duration)
    test.save_results(stats, args.duration)

    print(f"\n{'='*80}")
    print("✅ REALISTIC LOAD TEST COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
