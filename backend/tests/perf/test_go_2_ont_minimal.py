"""
HGO-010 DEBUG: Minimal 2-ONT Test (BFS Debug)

MINIMAL TOPOLOGY:
- 1 Backbone Gateway
- 1 Core Router
- 1 OLT
- 1 ODF
- 2 ONTs

Total: 6 devices, ~10 links

Purpose: Verify BFS works at all before scaling to 64/192 ONTs.

Expected: Tick completes in <1 second (BFS should be fast @ 6 devices)
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
def topology_2_ont_minimal():
    """
    Build MINIMAL topology for BFS debugging: 6 devices, 2 ONTs.

    Hierarchy:
    - 1 Backbone Gateway (anchor)
    - 1 Core Router
    - 1 OLT
    - 1 ODF
    - 2 ONTs
    """
    # Reset DB using catalog-only
    reset_script = ROOT / "scripts" / "reset_dev_db.py"
    subprocess.run(
        [sys.executable, str(reset_script), "--force", "--catalog-only"],
        check=True,
        env=os.environ,
    )

    # Re-init DB
    init_db()

    print("[BUILD] Building minimal 2-ONT topology...")

    with get_session() as s:
        # 1. Backbone Gateway (anchor, auto-online)
        backbone = Device(
            id="backbone1",
            name="Backbone-1",
            type=DeviceType.BACKBONE_GATEWAY,
            status=Status.UP,
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
        s.add(Interface(id="core1-if1", device_id="core1", name="if1"))

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

        # 4. ODF
        odf = Device(
            id="odf1",
            name="ODF-1",
            type=DeviceType.ODF,
            status=Status.UP,
            provisioned=False,
        )
        s.add(odf)
        s.add(Interface(id="odf1-if0", device_id="odf1", name="if0"))
        for i in range(1, 3):  # 2 ONT ports
            s.add(Interface(id=f"odf1-if{i}", device_id="odf1", name=f"if{i}"))

        # 5. Links: Backbone → Core → OLT → ODF
        s.add(
            Link(
                id="link-bb-core",
                src_device_id="backbone1",
                src_interface_id="backbone1-if0",
                dst_device_id="core1",
                dst_interface_id="core1-if0",
                type=LinkType.FIBER,
                status=Status.UP,
            )
        )

        s.add(
            Link(
                id="link-core-olt",
                src_device_id="core1",
                src_interface_id="core1-if1",
                dst_device_id="olt1",
                dst_interface_id="olt1-if0",
                type=LinkType.FIBER,
                status=Status.UP,
            )
        )

        s.add(
            Link(
                id="link-olt-odf",
                src_device_id="olt1",
                src_interface_id="olt1-if1",
                dst_device_id="odf1",
                dst_interface_id="odf1-if0",
                type=LinkType.FIBER,
                status=Status.UP,
            )
        )

        s.commit()

        # 6. Create 2 ONTs
        for i in range(1, 3):
            ont = Device(
                id=f"ont{i}",
                name=f"ONT-{i}",
                type=DeviceType.ONT,
                status=Status.UP,
                provisioned=False,
            )
            s.add(ont)
            s.add(Interface(id=f"ont{i}-if0", device_id=f"ont{i}", name="if0"))

            # Link: ODF → ONT
            s.add(
                Link(
                    id=f"link-odf-ont{i}",
                    src_device_id="odf1",
                    src_interface_id=f"odf1-if{i}",
                    dst_device_id=f"ont{i}",
                    dst_interface_id=f"ont{i}-if0",
                    type=LinkType.FIBER,
                    status=Status.UP,
                )
            )

        s.commit()

        # 7. Assign tariff to ONTs
        tariff = Tariff(id=1, name="Test 100/20", max_down_mbps=100, max_up_mbps=20)
        s.add(tariff)
        s.commit()

        for i in range(1, 3):
            ont_dev = s.get(Device, f"ont{i}")
            if ont_dev:
                ont_dev.tariff_id = 1
        s.commit()

        print("[OK] Assigned tariff to 2 ONTs")

        # 8. Provision devices (Core, OLT, ODF, ONTs)
        print("[PROVISION] Provisioning Core Router...")
        provision_device(s, s.get(Device, "core1"))
        s.commit()

        print("[PROVISION] Provisioning OLT...")
        provision_device(s, s.get(Device, "olt1"))
        s.commit()

        print("[PROVISION] Provisioning ODF...")
        provision_device(s, s.get(Device, "odf1"))
        s.commit()

        print("[PROVISION] Provisioning ONTs...")
        for i in range(1, 3):
            try:
                provision_device(s, s.get(Device, f"ont{i}"))
            except Exception as e:
                print(f"Warning: Could not provision ont{i}: {e}")
        s.commit()

        # Final count
        provisioned_count = s.exec(select(Device).where(Device.provisioned == True)).all()

        # CRITICAL: Final commit before session close!
        s.commit()

        print(f"[OK] Topology ready: 6 devices ({len(provisioned_count)} provisioned)")

    # Return outside session context
    return len(provisioned_count)


@pytest.fixture(scope="function")
def go_engine_process(topology_2_ont_minimal):
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
def test_go_engine_2_ont_minimal(go_engine_process):
    """
    Minimal test: 2 ONTs, verify BFS works at all.

    Expected: Tick completes in <1 second, 2 devices with traffic.
    """
    base_url = go_engine_process
    tick_url = f"{base_url}/api/v1/tick"
    snapshot_url = f"{base_url}/api/v1/snapshot"

    print("\nHGO-010 DEBUG: MINIMAL 2-ONT BFS TEST")
    print("=" * 60)

    # Single tick test
    print("[TEST] Running single tick...")
    start = time.perf_counter()
    resp = requests.post(tick_url, json={}, timeout=10)  # 10s should be plenty for 6 devices
    elapsed = time.perf_counter() - start

    assert resp.status_code == 200, f"Tick failed: {resp.status_code}"
    data = resp.json()

    # Validate response
    assert "tick" in data
    assert "timestamp" in data
    assert "success" in data
    assert data["success"] is True

    # Get snapshot
    snap_resp = requests.get(snapshot_url, timeout=2)
    assert snap_resp.status_code == 200
    snap_data = snap_resp.json()

    device_count = len(snap_data.get("device_metrics", {}))
    link_count = len(snap_data.get("link_metrics", {}))

    print(f"[OK] Tick 1: {elapsed*1000:.1f}ms (devices: {device_count}, links: {link_count})")

    # Verify: Should have 2 devices with traffic (2 ONTs)
    if device_count < 2:
        pytest.fail(f"Expected 2 devices with traffic, got {device_count}")

    print(f"[OK] BFS works! 2 ONTs generated traffic in {elapsed*1000:.1f}ms")
    print(f"[OK] Performance: {elapsed*1000:.1f}ms per tick @ 6 devices")
