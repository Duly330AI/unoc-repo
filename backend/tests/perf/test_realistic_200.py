"""Realistic combined load test: Status recompute + Traffic generation.

Measures end-to-end performance for a realistic 200-device topology with:
- Full L3 chain (provisioning, VRFs, neighbors, routes)
- Traffic generation (tariffs assigned to CPE devices)
- Status evaluation (ACTIVE devices with upstream L3 gating)

PERF-005 validation: After PERF-001 through PERF-005 optimizations,
we expect significant improvements in both status and traffic operations.

Usage:
    pytest -q backend/tests/perf/test_realistic_200.py

Environment:
    UNOC_PERF_PROFILE=1  # Enable profiling with cProfile
"""

from __future__ import annotations

import os
import time

import pytest

from backend.db import get_session, init_db, reset_db
from backend.events import reset_events
from backend.models import Device, DeviceType, Tariff
from backend.services.seed_service import ensure_default_tariffs, ensure_ipam_defaults
from backend.services.status_recompute import recompute_devices_status
from backend.services.traffic.v2_engine import TrafficEngine
from backend.tests.perf.test_large_scale import (
    attach_onts,
    build_core_and_olts,
    bulk_mode,
    maybe_profile_start,
    maybe_profile_stop_and_write,
)


@pytest.mark.perf
@pytest.mark.timeout(180)
def test_realistic_200_devices_status_and_traffic():
    """Realistic 200-device test: Measure status recompute + traffic generation.

    Topology:
    - 2 BACKBONE_GATEWAY (always online anchors)
    - 2 CORE_ROUTER (connected to backbones)
    - 4 OLT (2 per core)
    - ~190 ONT (47-48 per OLT, realistic GPON split)

    Steps:
    1. Build topology with full L3 chain
    2. Provision all devices (except backbones)
    3. Assign tariffs to all ONTs
    4. Measure: Status recompute time
    5. Measure: Traffic generation time (3 ticks)
    6. Report results with profiling data
    """
    # Clean slate
    reset_db()
    init_db()
    reset_events()

    with get_session() as s:
        ensure_ipam_defaults(s)
        ensure_default_tariffs(s)
        s.commit()

    profiler = maybe_profile_start()

    # Build topology
    print("\n" + "=" * 80)
    print("BUILDING 200-DEVICE TOPOLOGY...")
    print("=" * 80)

    build_start = time.perf_counter()
    with bulk_mode():
        with get_session() as s:
            # 2 cores (each connected to 2 OLTs)
            all_olts: list[str] = []
            for i in range(2):
                _, olts = build_core_and_olts(s, i + 1, count_olts=2)
                all_olts.extend(olts)

            # 48 ONTs per OLT = 192 ONTs total
            for oid in all_olts:
                attach_onts(s, oid, count_onts=48)

            s.commit()

    build_time = time.perf_counter() - build_start
    print(f"✅ Topology built in {build_time:.2f}s")

    # Count devices
    with get_session() as s:
        total_devices = s.query(Device).count()
        onts = s.query(Device).filter(Device.type == DeviceType.ONT).count()
        olts = s.query(Device).filter(Device.type == DeviceType.OLT).count()
        routers = (
            s.query(Device)
            .filter(Device.type.in_([DeviceType.CORE_ROUTER, DeviceType.EDGE_ROUTER]))
            .count()
        )
        backbones = s.query(Device).filter(Device.type == DeviceType.BACKBONE_GATEWAY).count()

    print("\n📊 TOPOLOGY SUMMARY:")
    print(f"   Total devices: {total_devices}")
    print(f"   - BACKBONE_GATEWAY: {backbones}")
    print(f"   - CORE_ROUTER: {routers}")
    print(f"   - OLT: {olts}")
    print(f"   - ONT: {onts}")

    # Assign tariffs to all ONTs
    print("\n" + "=" * 80)
    print("ASSIGNING TARIFFS TO ONTs...")
    print("=" * 80)

    tariff_start = time.perf_counter()
    # Create ONE tariff and reuse it for all ONTs (efficient)
    with get_session() as s:
        t = Tariff(name="Residential 100/20", max_down_mbps=100.0, max_up_mbps=20.0)
        s.add(t)
        s.commit()
        s.refresh(t)
        tariff_id = t.id

        ont_devices = s.query(Device).filter(Device.type == DeviceType.ONT).all()
        for ont in ont_devices:
            ont.tariff_id = tariff_id
        s.commit()

    tariff_time = time.perf_counter() - tariff_start
    print(f"✅ Tariffs assigned in {tariff_time:.2f}s")

    # === MEASUREMENT 1: STATUS RECOMPUTE ===
    print("\n" + "=" * 80)
    print("MEASURING: STATUS RECOMPUTE (full topology)")
    print("=" * 80)

    status_start = time.perf_counter()
    with get_session() as s:
        recompute_devices_status(s, include_passive_propagation=True)
        s.commit()
    status_time = time.perf_counter() - status_start

    print(f"✅ Status recompute: {status_time:.3f}s")

    # === MEASUREMENT 2: TRAFFIC GENERATION (3 ticks) ===
    print("\n" + "=" * 80)
    print("MEASURING: TRAFFIC GENERATION (3 ticks)")
    print("=" * 80)

    tick_times = []
    eng = TrafficEngine()
    for i in range(3):
        tick_start = time.perf_counter()
        eng.run_tick()
        tick_time = time.perf_counter() - tick_start
        tick_times.append(tick_time)
        print(f"  Tick {i + 1}: {tick_time:.3f}s")

    avg_traffic = sum(tick_times) / len(tick_times)
    print(f"✅ Average traffic tick: {avg_traffic:.3f}s")

    # === RESULTS SUMMARY ===
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE RESULTS (200 devices)")
    print("=" * 80)
    print(f"Status recompute:     {status_time:.3f}s")
    print(f"Traffic tick (avg):   {avg_traffic:.3f}s")
    print(f"Traffic tick (min):   {min(tick_times):.3f}s")
    print(f"Traffic tick (max):   {max(tick_times):.3f}s")

    # === EXTRAPOLATION TO 1000 DEVICES ===
    devices_ratio = 1000 / total_devices
    projected_status = status_time * devices_ratio
    projected_traffic = avg_traffic * devices_ratio

    print("\n" + "=" * 80)
    print("🔮 EXTRAPOLATION TO 1000 DEVICES (linear scaling)")
    print("=" * 80)
    print(f"Projected status:    {projected_status:.3f}s")
    print(f"Projected traffic:   {projected_traffic:.3f}s")

    # === DECISION CRITERIA ===
    print("\n" + "=" * 80)
    print("🎯 GO/NO-GO DECISION CRITERIA")
    print("=" * 80)

    status_target = 1.0  # <1s for status at 1000 devices
    traffic_target = 2.0  # <2s for traffic at 1000 devices

    status_ok = projected_status < status_target
    traffic_ok = projected_traffic < traffic_target

    print(f"Status target:   <{status_target:.1f}s  {'✅ PASS' if status_ok else '❌ FAIL'}")
    print(f"Traffic target:  <{traffic_target:.1f}s  {'✅ PASS' if traffic_ok else '❌ FAIL'}")

    if status_ok and traffic_ok:
        print("\n🎉 SUCCESS! Option A (Python) is viable for 1000 devices!")
        print("   Recommendation: Skip PERF-006, proceed to PERF-009 (1000-device test)")
    elif status_ok or traffic_ok:
        print("\n⚠️  PARTIAL SUCCESS - One metric passing, one failing")
        if not status_ok:
            print(f"   Status needs optimization: {projected_status:.3f}s > {status_target:.1f}s")
            print("   Recommendation: Deeper status optimization before scale test")
        if not traffic_ok:
            print(
                f"   Traffic needs optimization: {projected_traffic:.3f}s > {traffic_target:.1f}s"
            )
            print("   Recommendation: Continue PERF-006 (optimize is_link_passable)")
    else:
        print("\n❌ INSUFFICIENT PERFORMANCE")
        print(
            f"   Status: {projected_status:.3f}s > {status_target:.1f}s (gap: {projected_status - status_target:.3f}s)"
        )
        print(
            f"   Traffic: {projected_traffic:.3f}s > {traffic_target:.1f}s (gap: {projected_traffic - traffic_target:.3f}s)"
        )
        print("   Recommendation: Consider Option C (Hybrid Go) or deeper optimization")

    # Save profiling data
    out = maybe_profile_stop_and_write(profiler)
    if os.getenv("UNOC_PERF_PROFILE"):
        assert out is not None and os.path.exists(out), "profiling requested but no report written"
        print(f"\n📈 Profile saved to: {out}")

    print("=" * 80)

    # Assert targets (will fail test if not met, documenting performance regression)
    # Comment out for initial run to see actual numbers
    # assert status_ok, f"Status recompute too slow: {projected_status:.3f}s > {status_target:.1f}s"
    # assert traffic_ok, f"Traffic tick too slow: {projected_traffic:.3f}s > {traffic_target:.1f}s"
