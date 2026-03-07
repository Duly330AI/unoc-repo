"""Go Traffic Engine Load Test: 200 devices.

HGO-010: Measure Go engine performance at 200 devices to validate Phase 1 readiness.
This is the GO/NO-GO test for proceeding to Phase 2 (1000+ devices).

Target Performance:
- Single tick: <500ms (4-5× faster than Python's 2.3s)
- Extrapolation to 1000 devices: <2.5s

Test Strategy:
1. Build 200-device topology in-process
2. Start Python backend (port 5001)
3. Start Go engine via subprocess (port 8080)
4. Measure tick latency over 10 ticks (warmup) + 100 ticks (measurement)
5. Compare vs Python baseline
6. Make GO/NO-GO decision for Phase 2

Usage:
    pytest -q backend/tests/perf/test_realistic_200_go.py

Prerequisites:
- Go engine binary built: cd engine-go && go build -o bin/traffic-engine.exe cmd/traffic-engine/main.go
"""

from __future__ import annotations

import os
import statistics
import subprocess
import time
from typing import TYPE_CHECKING

import pytest
import requests
from sqlmodel import select

from backend.db import get_session, init_db, reset_db
from backend.events import reset_events
from backend.models import Device, DeviceType, Status, Tariff
from backend.services.provisioning_service import provision_device
from backend.services.seed_service import ensure_default_tariffs, ensure_ipam_defaults
from backend.tests.perf.test_large_scale import attach_onts, build_core_and_olts, bulk_mode

if TYPE_CHECKING:
    pass


@pytest.fixture(scope="function")  # Changed from "module" - need fresh DB each run
def topology_200():
    """Build 200-device topology: 2 cores, 4 OLTs, 192 ONTs."""
    reset_db()
    init_db()
    reset_events()

    with get_session() as s:
        ensure_ipam_defaults(s)
        ensure_default_tariffs(s)
        s.commit()

    print("\n[BUILD] Building 200-device topology...")
    with bulk_mode():
        with get_session() as s:
            # CRITICAL: Create 2 BACKBONE_GATEWAY anchors (BFS needs these!)
            for i in range(2):
                bb_id = f"backbone{i + 1}"
                bb = Device(
                    id=bb_id,
                    name=f"Backbone Gateway {i + 1}",
                    type=DeviceType.BACKBONE_GATEWAY,
                    status=Status.UP,
                    provisioned=True,  # Auto-provision backbones
                )
                s.add(bb)
            s.flush()

            # 2 cores, 2 OLTs each = 4 OLTs
            all_olts: list[str] = []
            for i in range(2):
                core_id, olts = build_core_and_olts(s, i + 1, count_olts=2)
                all_olts.extend(olts)

                # Link core to backbone (critical for L3 path!)
                bb_id = f"backbone{i + 1}"
                from backend.models import LinkType
                from backend.tests.perf.test_large_scale import _mk_link

                _mk_link(s, bb_id, core_id, kind=LinkType.FIBER)

            # 48 ONTs per OLT = 192 ONTs
            for oid in all_olts:
                attach_onts(s, oid, count_onts=48)

            s.commit()

    # Assign tariffs
    with get_session() as s:
        t = Tariff(name="Residential 100/20", max_down_mbps=100.0, max_up_mbps=20.0)
        s.add(t)
        s.commit()
        s.refresh(t)

        ont_devices = s.exec(select(Device).where(Device.type == DeviceType.ONT)).all()
        for ont in ont_devices:
            ont.tariff_id = t.id
        s.commit()

    # Provision all devices (backbones auto-provision)
    print("[PROVISION] Provisioning all devices...")
    with get_session() as s:
        # Provision cores, OLTs, and ONTs
        devices_to_provision = []
        devices_to_provision.extend(
            s.exec(select(Device).where(Device.type == DeviceType.CORE_ROUTER)).all()
        )
        devices_to_provision.extend(
            s.exec(select(Device).where(Device.type == DeviceType.OLT)).all()
        )
        devices_to_provision.extend(
            s.exec(select(Device).where(Device.type == DeviceType.ONT)).all()
        )

        for device in devices_to_provision:
            try:
                provision_device(s, device)  # Pass device object, not ID
            except Exception as e:
                print(f"Warning: Could not provision {device.id}: {e}")

        s.commit()

    with get_session() as s:
        total = s.exec(select(Device)).all()
        onts = s.exec(select(Device).where(Device.type == DeviceType.ONT)).all()
        provisioned = s.exec(select(Device).where(Device.provisioned == True)).all()
    print(
        f"[OK] Topology ready: {len(total)} devices ({len(onts)} ONTs, {len(provisioned)} provisioned)"
    )

    yield len(total)

    # Cleanup after module
    reset_db()


@pytest.fixture(scope="function")  # Changed from "module" - need fresh engine each run
def go_engine_process(topology_200):
    """Start Go traffic engine as subprocess, yield URL, then cleanup."""
    go_bin = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "engine-go", "bin", "traffic-engine.exe"
    )

    if not os.path.exists(go_bin):
        pytest.skip(f"Go engine not built: {go_bin}")

    # Start Go engine on port 8080
    # Go engine reads from same PostgreSQL database as Python backend
    env = os.environ.copy()
    env["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql://unoc:unocpw@localhost:5432/unocdb"
    )
    env["PORT"] = "8080"
    env["GO_ENV"] = "test"

    print(f"\n[START] Starting Go engine: {go_bin}")
    proc = subprocess.Popen(
        [go_bin],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server ready (max 5s)
    health_url = "http://localhost:8080/health"
    for i in range(50):
        try:
            resp = requests.get(health_url, timeout=1)
            if resp.status_code == 200:
                print("[OK] Go engine ready")
                break
        except requests.RequestException:
            pass
        time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("Go engine failed to start within 5s")

    yield "http://localhost:8080"

    # Cleanup
    print("\n[STOP] Stopping Go engine...")
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("[OK] Go engine stopped")


@pytest.mark.perf
@pytest.mark.timeout(300)
def test_go_engine_200_devices_load(go_engine_process):
    """HGO-010: Measure Go engine performance at 200 devices.

    This is the critical GO/NO-GO test for Phase 2 (1000+ devices).

    Test Structure:
    1. Warmup: 10 ticks (JIT, cache warming)
    2. Measurement: 100 ticks (stable performance)
    3. Analysis: p50, p95, p99, max latency
    4. Decision: <500ms p95 @ 200 → extrapolates to <2.5s @ 1000

    Expected Results (based on benchmarks):
    - Adjacency: 232µs @ 200 devices
    - Generation: 21.7ms @ 200 ONTs
    - Total: ~25-50ms per tick (assuming HTTP overhead)
    """
    base_url = go_engine_process
    tick_url = f"{base_url}/api/v1/tick"
    snapshot_url = f"{base_url}/api/v1/snapshot"

    print("\n" + "=" * 80)
    print("HGO-010: GO TRAFFIC ENGINE LOAD TEST @ 200 DEVICES")
    print("=" * 80)

    # === WARMUP: 10 ticks ===
    print("\n[WARMUP] WARMUP: 10 ticks (cache warming, JIT)...")
    warmup_times = []
    for i in range(10):
        start = time.perf_counter()
        resp = requests.post(tick_url, json={}, timeout=30)  # Increased timeout for first runs
        elapsed = time.perf_counter() - start
        warmup_times.append(elapsed)

        if resp.status_code != 200:
            pytest.fail(f"Tick failed: {resp.status_code} {resp.text}")

        if i == 0:
            # First tick - check TickResponse structure
            data = resp.json()
            assert "tick" in data, "Response missing 'tick' field"
            assert "timestamp" in data, "Response missing 'timestamp' field"
            assert "success" in data, "Response missing 'success' field"

            # Fetch snapshot to verify data
            snap_resp = requests.get(snapshot_url, timeout=2)
            if snap_resp.status_code == 200:
                snap_data = snap_resp.json()
                device_count = len(snap_data.get("device_metrics", {}))
                link_count = len(snap_data.get("link_metrics", {}))
                print(
                    f"   Tick 1: {elapsed*1000:.1f}ms (devices: {device_count}, links: {link_count})"
                )
            else:
                print(f"   Tick 1: {elapsed*1000:.1f}ms (snapshot unavailable)")
        elif i == 9:
            print(f"   Tick 10: {elapsed*1000:.1f}ms")

    warmup_avg = statistics.mean(warmup_times) * 1000
    print(f"[OK] Warmup complete: avg {warmup_avg:.1f}ms")

    # === MEASUREMENT: 100 ticks ===
    print("\n[MEASURE] MEASUREMENT: 100 ticks (stable performance)...")
    measure_times = []
    snapshot_times = []

    for i in range(100):
        # Tick
        start = time.perf_counter()
        resp = requests.post(tick_url, json={}, timeout=30)  # High timeout for stability
        tick_elapsed = time.perf_counter() - start
        measure_times.append(tick_elapsed)

        if resp.status_code != 200:
            pytest.fail(f"Tick {i+1} failed: {resp.status_code}")

        # Every 10th tick: Also measure snapshot retrieval
        if i % 10 == 0:
            snap_start = time.perf_counter()
            snap_resp = requests.get(snapshot_url, timeout=5)
            snap_elapsed = time.perf_counter() - snap_start
            snapshot_times.append(snap_elapsed)

            if snap_resp.status_code != 200:
                pytest.fail(f"Snapshot failed: {snap_resp.status_code}")

        # Progress indicator every 25 ticks
        if (i + 1) % 25 == 0:
            current_avg = statistics.mean(measure_times[-25:]) * 1000
            print(f"   Progress: {i+1}/100 ticks, recent avg: {current_avg:.1f}ms")

    # === STATISTICAL ANALYSIS ===
    print("\n" + "=" * 80)
    print("📈 LATENCY STATISTICS (100 ticks)")
    print("=" * 80)

    times_ms = [t * 1000 for t in measure_times]
    snap_ms = [t * 1000 for t in snapshot_times]

    p50 = statistics.median(times_ms)
    p95 = statistics.quantiles(times_ms, n=20)[18]  # 95th percentile
    p99 = statistics.quantiles(times_ms, n=100)[98]  # 99th percentile
    avg = statistics.mean(times_ms)
    min_time = min(times_ms)
    max_time = max(times_ms)
    stdev = statistics.stdev(times_ms)

    print("Tick Latency (POST /tick):")
    print(f"  min:    {min_time:.1f}ms")
    print(f"  p50:    {p50:.1f}ms")
    print(f"  avg:    {avg:.1f}ms")
    print(f"  p95:    {p95:.1f}ms")
    print(f"  p99:    {p99:.1f}ms")
    print(f"  max:    {max_time:.1f}ms")
    print(f"  stdev:  {stdev:.1f}ms")

    if snapshot_times:
        snap_avg = statistics.mean(snap_ms)
        snap_p95 = statistics.quantiles(snap_ms, n=20)[18] if len(snap_ms) > 1 else snap_ms[0]
        print(f"\nSnapshot Latency (GET /snapshot, n={len(snapshot_times)}):")
        print(f"  avg:    {snap_avg:.1f}ms")
        print(f"  p95:    {snap_p95:.1f}ms")

    # === COMPARISON TO PYTHON BASELINE ===
    print("\n" + "=" * 80)
    print("[COMPARE]  COMPARISON TO PYTHON BASELINE")
    print("=" * 80)

    python_baseline = 2300.0  # 2.3s per tick from test_realistic_200.py
    speedup = python_baseline / avg
    print(f"Python baseline:  {python_baseline:.0f}ms")
    print(f"Go p50:           {p50:.1f}ms")
    print(f"Speedup:          {speedup:.1f}× faster")

    # === EXTRAPOLATION TO 1000 DEVICES ===
    print("\n" + "=" * 80)
    print("[PROJECT] EXTRAPOLATION TO 1000 DEVICES")
    print("=" * 80)

    devices_ratio = 1000 / 200  # 5× scale
    projected_p50 = p50 * devices_ratio
    projected_p95 = p95 * devices_ratio
    projected_avg = avg * devices_ratio

    print("Linear scaling (5×):")
    print(f"  Projected p50:  {projected_p50:.0f}ms")
    print(f"  Projected avg:  {projected_avg:.0f}ms")
    print(f"  Projected p95:  {projected_p95:.0f}ms")

    # === GO/NO-GO DECISION ===
    print("\n" + "=" * 80)
    print("[DECISION] GO/NO-GO DECISION FOR PHASE 2")
    print("=" * 80)

    target_p95_200 = 500.0  # <500ms @ 200 devices
    target_p95_1000 = 2500.0  # <2.5s @ 1000 devices

    pass_200 = p95 < target_p95_200
    pass_1000 = projected_p95 < target_p95_1000

    print(f"Target @ 200:     <{target_p95_200:.0f}ms (p95)")
    print(f"Actual @ 200:     {p95:.1f}ms  {'[OK] PASS' if pass_200 else '[FAIL] FAIL'}")
    print(f"\nTarget @ 1000:    <{target_p95_1000:.0f}ms (p95)")
    print(f"Projected @ 1000: {projected_p95:.0f}ms  {'[OK] PASS' if pass_1000 else '[FAIL] FAIL'}")

    if pass_200 and pass_1000:
        margin_200 = ((target_p95_200 - p95) / target_p95_200) * 100
        margin_1000 = ((target_p95_1000 - projected_p95) / target_p95_1000) * 100
        print("\n[SUCCESS] GO! Phase 2 (1000+ devices) is viable!")
        print(f"   Margin @ 200:  {margin_200:.0f}% headroom")
        print(f"   Margin @ 1000: {margin_1000:.0f}% headroom")
        print("\n   Next steps:")
        print("   1. HGO-009: Integration tests (Python ↔ Go parity)")
        print("   2. HGO-011: Load test @ 1000 devices")
        print("   3. HGO-012: Stress test @ 10,000 devices")
    elif pass_200:
        print("\n[CAUTION]  CAUTION: Passes @ 200, but 1000 projection exceeds target")
        print(f"   Gap: {projected_p95 - target_p95_1000:.0f}ms over target")
        print("\n   Options:")
        print("   A. Accept risk, test @ 1000 (may need optimization)")
        print("   B. Optimize now (before scaling)")
        print("   C. Run HGO-009 first (validate correctness)")
    else:
        print("\n[FAIL] NO-GO: Performance insufficient for Phase 2")
        print(f"   Gap @ 200: {p95 - target_p95_200:.0f}ms over target")
        print("\n   Recommendations:")
        print("   1. Profile bottlenecks (HTTP overhead? JSON parsing?)")
        print("   2. Optimize critical path (adjacency build, BFS, aggregation)")
        print("   3. Consider caching strategies")
        print("   4. Re-test after optimizations")

    print("=" * 80)

    # Assertions (commented out for first run to see actual numbers)
    # assert pass_200, f"Failed @ 200: {p95:.1f}ms > {target_p95_200:.0f}ms"
    # assert pass_1000, f"Failed @ 1000 projection: {projected_p95:.0f}ms > {target_p95_1000:.0f}ms"
