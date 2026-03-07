"""
HGO-010: Load Test for Go Traffic Engine @ 200 Devices

CLEAN IMPLEMENTATION (following production topology rules):
- 1 Backbone Gateway (not 2!)
- Correct hierarchy: Backbone → Core → OLT → ODF → ONT
- 64 ONTs per ODF (3 ODFs = 192 ONTs)
- Correct provision order: Core, OLT, then ONTs (strand-by-strand)
- DB reset with --catalog-only (clean slate)

Performance targets:
- @ 200 devices: p95 < 500ms per tick → GO
- @ 1000 devices: p95 < 2500ms per tick (extrapolated) → Phase 2 approved

Test structure:
1. topology_200_clean: Builds correct PON hierarchy
2. go_engine_process: Starts Go engine subprocess
3. test_go_engine_200_devices_load: Measures performance + GO/NO-GO decision

IMPORTANT: Set DATABASE_URL in terminal before running:
    $env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
    pytest -m perf backend/tests/perf/test_go_200_clean.py
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
from sqlmodel import select

# Add repo root to path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status, Tariff
from backend.services.provisioning_service import provision_device


@pytest.fixture(scope="function")
def topology_200_clean():
    """
    Build clean 200-device PON topology following production rules.

    Hierarchy:
    - 1 Backbone Gateway (auto-online, anchor for BFS)
    - 1 Core Router
    - 1 OLT (with 3 ports for 3 strands)
    - 3 ODFs (one per strand)
    - 192 ONTs (64 per ODF = 3 strands)

    Total: 1 + 1 + 1 + 3 + 192 = 198 devices
    (Close to 200, respects 64-ONT limit per ODF)
    """
    # Reset DB using catalog-only (clean slate + default hardware models)
    reset_script = ROOT / "scripts" / "reset_dev_db.py"
    subprocess.run(
        [sys.executable, str(reset_script), "--force", "--catalog-only"],
        check=True,
        env=os.environ,  # Inherits DATABASE_URL from module top
    )

    # Re-init DB (schema ready)
    init_db()

    print("[BUILD] Building clean 200-device PON topology...")

    with get_session() as s:
        # 1. Create Backbone Gateway (anchor device, auto-online)
        backbone = Device(
            id="backbone1",
            name="Backbone-1",
            type=DeviceType.BACKBONE_GATEWAY,
            status=Status.UP,
        )
        s.add(backbone)
        s.add(Interface(id="backbone1-if0", device_id="backbone1", name="if0"))

        # 2. Create Core Router
        core = Device(
            id="core1",
            name="Core-1",
            type=DeviceType.CORE_ROUTER,
            status=Status.UP,  # Will be provisioned later
            provisioned=False,
        )
        s.add(core)
        s.add(Interface(id="core1-if0", device_id="core1", name="if0"))

        # 3. Create OLT
        olt = Device(
            id="olt1",
            name="OLT-1",
            type=DeviceType.OLT,
            status=Status.UP,  # Will be provisioned later
            provisioned=False,
        )
        s.add(olt)
        s.add(Interface(id="olt1-if0", device_id="olt1", name="if0"))  # → Core
        s.add(Interface(id="olt1-if1", device_id="olt1", name="if1"))  # → ODF1
        s.add(Interface(id="olt1-if2", device_id="olt1", name="if2"))  # → ODF2
        s.add(Interface(id="olt1-if3", device_id="olt1", name="if3"))  # → ODF3

        # 4. Create 3 ODFs (one per strand)
        odfs = []
        for strand in range(1, 4):
            odf_id = f"odf{strand}"
            odf = Device(
                id=odf_id,
                name=f"ODF-{strand}",
                type=DeviceType.ODF,
                status=Status.UP,  # Passive devices always UP
            )
            s.add(odf)
            s.add(Interface(id=f"{odf_id}-if0", device_id=odf_id, name="if0"))  # → OLT
            # Each ODF has 64 interfaces for ONTs
            for port in range(1, 65):
                s.add(Interface(id=f"{odf_id}-if{port}", device_id=odf_id, name=f"if{port}"))
            odfs.append(odf_id)

        # 5. Create 192 ONTs (64 per ODF)
        ont_ids = []
        for strand in range(1, 4):
            for ont_num in range(1, 65):  # 64 ONTs per strand
                ont_id = f"ont{strand}_{ont_num}"
                ont = Device(
                    id=ont_id,
                    name=f"ONT-{strand}-{ont_num}",
                    type=DeviceType.ONT,
                    status=Status.UP,  # Will be provisioned later
                    provisioned=False,
                )
                s.add(ont)
                s.add(Interface(id=f"{ont_id}-if0", device_id=ont_id, name="if0"))
                ont_ids.append(ont_id)

        s.commit()
        print("[OK] Created 198 devices: 1 backbone, 1 core, 1 OLT, 3 ODFs, 192 ONTs")

        # 6. Create Links (hierarchy: Backbone → Core → OLT → ODF → ONT)

        # Backbone → Core
        s.add(
            Link(
                id="link_backbone1_core1",
                a_interface_id="backbone1-if0",
                b_interface_id="core1-if0",
                kind=LinkType.P2P,
                status=Status.UP,
            )
        )

        # Core → OLT
        s.add(
            Link(
                id="link_core1_olt1",
                a_interface_id="core1-if0",
                b_interface_id="olt1-if0",
                kind=LinkType.FIBER,
                status=Status.UP,
            )
        )

        # OLT → ODFs (3 links, one per strand)
        for strand in range(1, 4):
            s.add(
                Link(
                    id=f"link_olt1_odf{strand}",
                    a_interface_id=f"olt1-if{strand}",
                    b_interface_id=f"odf{strand}-if0",
                    kind=LinkType.FIBER,
                    status=Status.UP,
                )
            )

        # ODF → ONTs (192 links, 64 per strand)
        for strand in range(1, 4):
            odf_id = f"odf{strand}"
            for ont_num in range(1, 65):
                ont_id = f"ont{strand}_{ont_num}"
                s.add(
                    Link(
                        id=f"link_{odf_id}_{ont_id}",
                        a_interface_id=f"{odf_id}-if{ont_num}",
                        b_interface_id=f"{ont_id}-if0",
                        kind=LinkType.FIBER,
                        status=Status.UP,
                    )
                )

        s.commit()
        print("[OK] Created 197 links (1+1+3+192)")

        # 7. Assign Tariffs to all ONTs
        tariff = Tariff(
            name="Residential 100/20",
            max_down_mbps=100.0,
            max_up_mbps=20.0,
        )
        s.add(tariff)
        s.commit()

        onts = s.exec(select(Device).where(Device.type == DeviceType.ONT)).all()
        for ont in onts:
            ont.tariff_id = tariff.id
        s.commit()
        print(f"[OK] Assigned tariff to {len(onts)} ONTs")

        # 8. Provision devices (correct order: Core → OLT → ODFs → ONTs strand-by-strand)

        # Provision Core
        print("[PROVISION] Provisioning Core Router...")
        core_dev = s.get(Device, "core1")
        assert core_dev is not None
        provision_device(s, core_dev)
        s.commit()

        # Provision OLT
        print("[PROVISION] Provisioning OLT...")
        olt_dev = s.get(Device, "olt1")
        assert olt_dev is not None
        provision_device(s, olt_dev)
        s.commit()

        # NOTE: ODFs are PASSIVE devices (fiber distribution frames)
        # They do NOT get provisioned - only used for interface mapping!
        print("[INFO] ODFs are passive devices - no provisioning needed")

        # Provision ONTs strand-by-strand (respects upstream dependency)
        for strand in range(1, 4):
            print(f"[PROVISION] Provisioning ONTs on strand {strand}...")
            for ont_num in range(1, 65):
                ont_id = f"ont{strand}_{ont_num}"
                ont_dev = s.get(Device, ont_id)
                if ont_dev is None:
                    continue
                try:
                    provision_device(s, ont_dev)
                except Exception as e:
                    print(f"Warning: Could not provision {ont_id}: {e}")
            s.commit()

        # Final count
        provisioned_count = s.exec(select(Device).where(Device.provisioned == True)).all()

        # CRITICAL: Final commit before closing session
        # (get_session() only calls close(), not commit()!)
        s.commit()

        print(f"[OK] Topology ready: 198 devices ({len(provisioned_count)} provisioned)")

    # Return outside of session context (session committed and closed)
    return len(provisioned_count)


@pytest.fixture(scope="function")
def go_engine_process(topology_200_clean):
    """Start Go traffic engine subprocess on port 8080."""
    go_bin = ROOT / "engine-go" / "bin" / "traffic-engine.exe"
    if not go_bin.exists():
        pytest.skip(f"Go binary not found: {go_bin}")

    env = {
        **os.environ,
        "DATABASE_URL": "postgresql://unoc:unocpw@localhost:5432/unocdb",
        "PORT": "8080",
        "GO_ENV": "test",
    }

    print(f"[START] Starting Go engine: {go_bin}")
    proc = subprocess.Popen(
        [str(go_bin)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for health check (max 5 seconds)
    base_url = "http://localhost:8080"
    health_url = f"{base_url}/health"

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
        pytest.fail("Go engine failed to start within 5 seconds")

    yield base_url

    # Cleanup
    print("[STOP] Stopping Go engine...")
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()

    # Print Go engine logs for debugging
    stdout, stderr = proc.communicate()
    if stdout:
        print("\n[GO STDOUT]")
        print(stdout.decode("utf-8", errors="replace"))
    if stderr:
        print("\n[GO STDERR]")
        print(stderr.decode("utf-8", errors="replace"))

    print("[OK] Go engine stopped")


@pytest.mark.perf
def test_go_engine_200_devices_load(go_engine_process):
    """
    HGO-010: Load test @ 200 devices.

    Measures:
    - Warmup: 10 ticks (cache warming, JIT)
    - Measurement: 100 ticks (performance data)
    - Statistics: p50, p95, p99
    - Comparison: vs Python baseline (2.3s)
    - Extrapolation: 200 → 1000 devices (×5)
    - Decision: GO/NO-GO for Phase 2 (1000+ devices)
    """
    base_url = go_engine_process
    tick_url = f"{base_url}/api/v1/tick"
    snapshot_url = f"{base_url}/api/v1/snapshot"

    print("\nHGO-010: GO TRAFFIC ENGINE LOAD TEST @ 200 DEVICES")
    print("=" * 60)

    # Warmup phase (10 ticks)
    print("[WARMUP] WARMUP: 10 ticks (cache warming, JIT)...")
    for i in range(10):
        start = time.perf_counter()
        resp = requests.post(tick_url, json={}, timeout=120)  # 2 min for BFS @ 200 devices
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200, f"Tick {i+1} failed: {resp.status_code}"
        data = resp.json()

        # First tick: validate structure + get device count
        if i == 0:
            assert "tick" in data
            assert "timestamp" in data
            assert "success" in data

            # Get snapshot to check device count
            snap_resp = requests.get(snapshot_url, timeout=2)
            assert snap_resp.status_code == 200
            snap_data = snap_resp.json()
            device_count = len(snap_data.get("device_metrics", {}))
            link_count = len(snap_data.get("link_metrics", {}))

            print(f"   Tick 1: {elapsed*1000:.1f}ms (devices: {device_count}, links: {link_count})")

            # Sanity check
            if device_count < 150:
                pytest.fail(f"Expected ~192 devices with traffic, got {device_count}")

    print("[OK] Warmup complete")

    # Measurement phase (100 ticks)
    print("[MEASURE] MEASUREMENT: 100 ticks (performance data)...")
    measure_times = []
    snapshot_times = []

    for i in range(100):
        # Tick request
        start = time.perf_counter()
        resp = requests.post(tick_url, json={}, timeout=120)  # 2 min for BFS @ 200 devices
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200, f"Measurement tick {i+1} failed"
        measure_times.append(elapsed)

        # Every 10th tick: snapshot query
        if i % 10 == 0:
            snap_start = time.perf_counter()
            snap_resp = requests.get(snapshot_url, timeout=2)
            snap_elapsed = time.perf_counter() - snap_start

            assert snap_resp.status_code == 200
            snapshot_times.append(snap_elapsed)

        # Progress indicator
        if (i + 1) % 20 == 0:
            print(f"   Progress: {i+1}/100 ticks ({elapsed*1000:.1f}ms last)")

    print("[OK] Measurement complete")

    # Statistical analysis
    import statistics

    times_ms = [t * 1000 for t in measure_times]
    avg = statistics.mean(times_ms)
    median = statistics.median(times_ms)
    stdev = statistics.stdev(times_ms)

    # Percentiles (p50, p95, p99)
    sorted_times = sorted(times_ms)
    p50 = sorted_times[int(len(sorted_times) * 0.50)]
    p95 = sorted_times[int(len(sorted_times) * 0.95)]
    p99 = sorted_times[int(len(sorted_times) * 0.99)]
    max_time = max(times_ms)

    print("\n[STATS] PERFORMANCE STATISTICS @ 200 DEVICES:")
    print(f"  Average:  {avg:.1f}ms")
    print(f"  Median:   {median:.1f}ms")
    print(f"  Stdev:    {stdev:.1f}ms")
    print(f"  p50:      {p50:.1f}ms")
    print(f"  p95:      {p95:.1f}ms  [TARGET: <500ms]")
    print(f"  p99:      {p99:.1f}ms")
    print(f"  Max:      {max_time:.1f}ms")

    # Snapshot performance
    if snapshot_times:
        snap_avg = statistics.mean(t * 1000 for t in snapshot_times)
        print(f"\n  Snapshot avg: {snap_avg:.1f}ms (10 queries)")

    # Comparison to Python baseline (2.3s @ 200 devices)
    python_baseline = 2300.0  # ms
    speedup = python_baseline / avg
    print("\n[COMPARE] VS PYTHON BASELINE:")
    print(f"  Python: {python_baseline:.0f}ms")
    print(f"  Go:     {avg:.1f}ms")
    print(f"  Speedup: {speedup:.1f}×")

    # Extrapolation to 1000 devices (linear scaling assumption)
    scale_factor = 1000 / 200  # 5×
    projected_avg = avg * scale_factor
    projected_p95 = p95 * scale_factor
    projected_p99 = p99 * scale_factor

    print("\n[EXTRAPOLATE] PROJECTED @ 1000 DEVICES (5× scale):")
    print(f"  Avg:  {projected_avg:.1f}ms")
    print(f"  p95:  {projected_p95:.1f}ms  [TARGET: <2500ms]")
    print(f"  p99:  {projected_p99:.1f}ms")

    # GO/NO-GO Decision
    print("\n[DECISION] GO/NO-GO DECISION:")

    pass_200 = p95 < 500.0
    pass_1000 = projected_p95 < 2500.0

    print(f"  @ 200 devices:  p95={p95:.1f}ms < 500ms?  {'[OK]' if pass_200 else '[FAIL]'}")
    print(
        f"  @ 1000 devices: p95={projected_p95:.1f}ms < 2500ms?  {'[OK]' if pass_1000 else '[FAIL]'}"
    )

    if pass_200 and pass_1000:
        print("\n  RESULT: [OK] GO for Phase 2 (1000+ devices)")
    else:
        print("\n  RESULT: [FAIL] NO-GO - performance targets not met")
        pytest.fail("Performance targets not met")

    print("=" * 60)
