"""
HGO-010-A: REDUCED Load Test for Go Traffic Engine @ 64 ONTs

PURPOSE: Isolate BFS performance bottleneck with smaller topology
- 1 Backbone Gateway (anchor)
- 1 Core Router
- 1 OLT
- 1 ODF
- 64 ONTs

Total: 68 devices (vs 198 in full test)

Expected: BFS should finish in <10s if O(N²) hypothesis correct:
- 64 ONTs × 68 nodes = 4,352 visits (vs 38,400 in full test)
- Should be ~9× faster (2 min → 13s)

IMPORTANT: Set DATABASE_URL before running:
    $env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
    pytest -m perf backend/tests/perf/test_go_64_clean.py -v
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
from sqlmodel import select

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, Status, Tariff
from backend.services.provisioning_service import provision_device


@pytest.fixture(scope="function")
def topology_64_clean():
    """
    Build minimal PON topology: 1 ODF × 64 ONTs = 68 devices total.

    Hierarchy:
    - Backbone (anchor)
    - Core
    - OLT
    - ODF
    - 64 ONTs
    """
    # Reset DB
    reset_script = ROOT / "scripts" / "reset_dev_db.py"
    subprocess.run(
        [sys.executable, str(reset_script), "--force", "--catalog-only"],
        check=True,
        env=os.environ,
    )
    init_db()

    print("[BUILD] Building 64-ONT PON topology...")

    with get_session() as s:
        # 1. Backbone Gateway (anchor)
        backbone = Device(
            id="backbone1",
            name="Backbone-1",
            type=DeviceType.BACKBONE_GATEWAY,
            status=Status.UP,
        )
        s.add(backbone)
        s.add(Interface(id="backbone1-if0", device_id="backbone1", name="if0"))
        s.commit()

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
        s.add(Interface(id="core1-if1", device_id="core1", name="if1"))
        s.add(
            Link(
                id="backbone1-core1",
                a_interface_id="backbone1-if0",
                b_interface_id="core1-if0",
            )
        )
        s.commit()

        # 3. OLT
        olt = Device(
            id="olt1",
            name="OLT-1",
            type=DeviceType.OLT,
            status=Status.UP,
            provisioned=False,
        )
        s.add(olt)
        s.add(Interface(id="olt1-if0", device_id="olt1", name="if0"))
        s.add(Interface(id="olt1-if1", device_id="olt1", name="if1"))
        s.add(
            Link(
                id="core1-olt1",
                a_interface_id="core1-if1",
                b_interface_id="olt1-if0",
            )
        )
        s.commit()

        # 4. ODF
        odf = Device(
            id="odf1",
            name="ODF-1",
            type=DeviceType.ODF,
        )
        s.add(odf)
        s.add(Interface(id="odf1-if0", device_id="odf1", name="if0"))
        s.add(
            Link(
                id="olt1-odf1",
                a_interface_id="olt1-if1",
                b_interface_id="odf1-if0",
            )
        )
        s.commit()

        # 5. Tariff (for ONTs)
        tariff = Tariff(
            name="Residential 100/20",
            max_down_mbps=100,
            max_up_mbps=20,
        )
        s.add(tariff)
        s.commit()

        # 6. 64 ONTs
        for ont_num in range(1, 65):
            ont_id = f"ont1_{ont_num}"
            ont = Device(
                id=ont_id,
                name=f"ONT-1-{ont_num}",
                type=DeviceType.ONT,
                tariff_id=tariff.id,
                provisioned=False,
            )
            s.add(ont)
            s.add(Interface(id=f"{ont_id}-if0", device_id=ont_id, name="if0"))

            # ODF needs 64 interfaces (one per ONT)
            s.add(Interface(id=f"odf1-if{ont_num}", device_id="odf1", name=f"if{ont_num}"))

            s.add(
                Link(
                    id=f"odf1-{ont_id}",
                    a_interface_id=f"odf1-if{ont_num}",
                    b_interface_id=f"{ont_id}-if0",
                )
            )
        s.commit()

        # 7. Provision in correct order
        print("[PROVISION] Provisioning devices...")
        core_device = s.get(Device, "core1")
        if core_device:
            provision_device(s, core_device)
        s.commit()

        olt_device = s.get(Device, "olt1")
        if olt_device:
            provision_device(s, olt_device)
        s.commit()

        # Provision all ONTs
        for ont_num in range(1, 65):
            ont_id = f"ont1_{ont_num}"
            ont = s.get(Device, ont_id)
            if ont:
                try:
                    provision_device(s, ont)
                except Exception as e:
                    print(f"Warning: Could not provision {ont_id}: {e}")
        s.commit()

        # CRITICAL: Final commit before context exit!
        s.commit()

    # Return device count OUTSIDE session context
    with get_session() as s:
        device_count = s.exec(select(Device)).all()
        provisioned_count = [d for d in device_count if d.provisioned]
        print(
            f"[OK] Topology ready: {len(device_count)} devices ({len(provisioned_count)} provisioned)"
        )
        return len(device_count)


@pytest.fixture(scope="function")
def go_engine_process(topology_64_clean):
    """Start Go engine subprocess and wait for ready."""
    go_bin = ROOT / "engine-go" / "bin" / "traffic-engine.exe"

    if not go_bin.exists():
        pytest.fail(f"Go binary not found: {go_bin}")

    env = {
        **os.environ,
        "DATABASE_URL": "postgresql://unoc:unocpw@localhost:5432/unocdb",
        "PORT": "8080",
        "GO_ENV": "test",
    }

    print(f"[GO] Starting Go engine: {go_bin}")
    proc = subprocess.Popen(
        [str(go_bin)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for health check (max 5s)
    base_url = "http://localhost:8080"
    for i in range(50):
        try:
            resp = requests.get(f"{base_url}/health", timeout=1)
            if resp.status_code == 200:
                print("[GO] Engine ready!")
                break
        except (requests.ConnectionError, requests.Timeout):
            pass
        time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("Go engine did not become ready in 5s")

    yield base_url

    # Cleanup
    print("[GO] Stopping engine...")
    proc.terminate()
    try:
        stdout, stderr = proc.communicate(timeout=3)
        print("\n=== GO STDOUT ===")
        print(stdout)
        if stderr:
            print("\n=== GO STDERR ===")
            print(stderr)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.mark.perf
def test_go_engine_64_ont_load(go_engine_process):
    """
    HGO-010-A: Measure BFS performance with 64 ONTs.

    Expected:
    - First tick: <30s (BFS warming up)
    - Subsequent ticks: <5s (BFS cached or optimized)

    If first tick >30s → BFS bottleneck confirmed, needs optimization.
    """
    base_url = go_engine_process
    tick_url = f"{base_url}/api/v1/tick"
    snapshot_url = f"{base_url}/api/v1/snapshot"

    print("\n=== WARMUP PHASE (10 ticks) ===")
    warmup_times = []

    for i in range(1, 11):
        start = time.perf_counter()

        try:
            resp = requests.post(tick_url, json={}, timeout=60)  # 1 min timeout
            resp.raise_for_status()
        except requests.Timeout:
            pytest.fail(f"Tick {i} timed out after 60s!")
        except requests.RequestException as e:
            pytest.fail(f"Tick {i} failed: {e}")

        elapsed = time.perf_counter() - start
        warmup_times.append(elapsed)

        # Verify topology on first tick
        if i == 1:
            snap_resp = requests.get(snapshot_url, timeout=2)
            snap_resp.raise_for_status()
            snapshot = snap_resp.json()
            device_count = len(snapshot.get("device_metrics", []))

            if device_count < 60:
                pytest.fail(f"Expected ~68 devices, got {device_count}")

            print(f"Tick 1: {elapsed*1000:.1f}ms (devices: {device_count})")
        else:
            print(f"Tick {i}: {elapsed*1000:.1f}ms")

    # Analysis
    avg_warmup = sum(warmup_times) / len(warmup_times)
    p50_warmup = sorted(warmup_times)[len(warmup_times) // 2]
    p95_warmup = sorted(warmup_times)[int(len(warmup_times) * 0.95)]

    print("\nWarmup Results:")
    print(f"  Avg:  {avg_warmup*1000:.1f}ms")
    print(f"  p50:  {p50_warmup*1000:.1f}ms")
    print(f"  p95:  {p95_warmup*1000:.1f}ms")
    print(f"  Max:  {max(warmup_times)*1000:.1f}ms")

    # BFS bottleneck check
    if warmup_times[0] > 30.0:
        print("\n⚠️  BOTTLENECK CONFIRMED: First tick >30s @ 64 ONTs")
        print("    → BFS optimization REQUIRED before scaling")
    elif warmup_times[0] > 10.0:
        print("\n⚠️  PERFORMANCE WARNING: First tick >10s @ 64 ONTs")
        print("    → May not scale to 1000 devices")
    else:
        print("\n✅ First tick OK @ 64 ONTs")

    # Measurement phase (if warmup passed)
    if p95_warmup < 5.0:
        print("\n=== MEASUREMENT PHASE (100 ticks) ===")
        measurement_times = []

        for i in range(1, 101):
            start = time.perf_counter()
            resp = requests.post(tick_url, json={}, timeout=30)
            resp.raise_for_status()
            elapsed = time.perf_counter() - start
            measurement_times.append(elapsed)

            if i % 20 == 0:
                print(f"Tick {i}: {elapsed*1000:.1f}ms")

        # Statistics
        avg_measure = sum(measurement_times) / len(measurement_times)
        p50_measure = sorted(measurement_times)[len(measurement_times) // 2]
        p95_measure = sorted(measurement_times)[int(len(measurement_times) * 0.95)]

        print("\nMeasurement Results (100 ticks):")
        print(f"  Avg:  {avg_measure*1000:.1f}ms")
        print(f"  p50:  {p50_measure*1000:.1f}ms")
        print(f"  p95:  {p95_measure*1000:.1f}ms")
        print(f"  Max:  {max(measurement_times)*1000:.1f}ms")

        # Extrapolation to 200 devices (if linear)
        # 64 ONTs → 198 ONTs = 3.1× more ONTs
        # If O(N²): 3.1² = 9.6× slower
        extrap_p95_200 = p95_measure * 9.6
        print("\nExtrapolated to 200 devices (O(N²) assumption):")
        print(f"  p95: {extrap_p95_200*1000:.1f}ms")

        if extrap_p95_200 < 0.5:
            print("  ✅ GO for 200-device test")
        else:
            print("  ❌ NO-GO: Would exceed 500ms target")
