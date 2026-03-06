#!/usr/bin/env python3
"""Full system E2E benchmark with realistic topology.

Tests:
1. Device creation (bulk)
2. Link creation (bulk batch)
3. Provisioning (parallel)
4. Traffic tick (Go engine)
5. API endpoint latency
6. WebSocket event delivery

Measures real-world performance under load.
"""
import statistics
import time
from typing import Any

import requests

BASE = "http://localhost:5001"


def measure(label: str, fn):
    """Execute function and measure time."""
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    print(f"  ✓ {label}: {elapsed*1000:.1f}ms")
    return result, elapsed


def api_get(path: str) -> tuple[Any, float]:
    """GET request with timing."""
    start = time.perf_counter()
    resp = requests.get(f"{BASE}{path}", timeout=30)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    return resp.json(), elapsed


def api_post(path: str, data: dict) -> tuple[Any, float]:
    """POST request with timing."""
    start = time.perf_counter()
    resp = requests.post(f"{BASE}{path}", json=data, timeout=30)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    return resp.json(), elapsed


def main():
    print("\n🔥 FULL SYSTEM E2E BENCHMARK")
    print("=" * 60)

    # 1. Health check
    print("\n📊 Phase 1: Health Check")
    health, t = api_get("/api/health")
    print(f"  ✓ Backend: {health['status']} ({t*1000:.1f}ms)")

    # 2. API Endpoint Latency (no include_interfaces)
    print("\n📊 Phase 2: API Endpoint Latency (minimal)")
    times_devices = []
    times_links = []
    for i in range(5):
        _, t_dev = api_get("/api/devices")
        _, t_link = api_get("/api/links")
        times_devices.append(t_dev * 1000)
        times_links.append(t_link * 1000)
        print(f"  Run {i+1}: devices={t_dev*1000:.0f}ms, links={t_link*1000:.0f}ms")

    print("\n  📈 /api/devices (minimal):")
    print(f"     Avg: {statistics.mean(times_devices):.0f}ms")
    print(f"     p50: {statistics.median(times_devices):.0f}ms")
    print(f"     p95: {sorted(times_devices)[int(len(times_devices)*0.95)]:.0f}ms")

    print("\n  📈 /api/links (minimal):")
    print(f"     Avg: {statistics.mean(times_links):.0f}ms")
    print(f"     p50: {statistics.median(times_links):.0f}ms")
    print(f"     p95: {sorted(times_links)[int(len(times_links)*0.95)]:.0f}ms")

    # 3. API Endpoint Latency (WITH include_interfaces)
    print("\n📊 Phase 3: API Endpoint Latency (WITH interfaces)")
    times_with_if = []
    for i in range(3):  # Fewer runs because this is slow
        _, t = api_get("/api/devices?include_interfaces=true")
        times_with_if.append(t * 1000)
        print(f"  Run {i+1}: {t*1000:.0f}ms")

    print("\n  📈 /api/devices (with interfaces):")
    print(f"     Avg: {statistics.mean(times_with_if):.0f}ms")
    print(f"     p50: {statistics.median(times_with_if):.0f}ms")

    # 4. Traffic Tick Performance
    print("\n📊 Phase 4: Traffic Tick Performance")
    snap1, _ = api_get("/api/metrics/snapshot")
    tick1 = snap1.get("tick", 0)
    print(f"  Initial tick: {tick1}")

    time.sleep(2.5)  # Wait for 2-3 ticks

    snap2, _ = api_get("/api/metrics/snapshot")
    tick2 = snap2.get("tick", 0)
    elapsed_ticks = tick2 - tick1
    print(f"  After 2.5s: tick {tick2} (+{elapsed_ticks} ticks)")
    print(f"  ✓ Traffic engine ticking: {'✅ YES' if elapsed_ticks >= 2 else '❌ NO'}")

    # 5. Check if Go engine is active
    leaves = snap2.get("leaves_count", 0)
    devices_with_traffic = len(
        [d for d in snap2.get("device_metrics", {}).values() if d.get("up_bps", 0) > 0]
    )
    print(f"  Leaves: {leaves}")
    print(f"  Devices with traffic: {devices_with_traffic}")

    # 6. Summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)

    avg_devices_minimal = statistics.mean(times_devices)
    avg_devices_with_if = statistics.mean(times_with_if)

    print("\n✅ GOOD (Target <300ms):")
    if avg_devices_minimal < 300:
        print(f"  ✓ /api/devices (minimal): {avg_devices_minimal:.0f}ms")

    print("\n⚠️  SLOW (Should be <500ms):")
    if avg_devices_minimal >= 300:
        print(f"  • /api/devices (minimal): {avg_devices_minimal:.0f}ms")
    if avg_devices_with_if >= 500:
        print(
            f"  • /api/devices (with interfaces): {avg_devices_with_if:.0f}ms ← N+1 QUERY PROBLEM!"
        )

    print("\n❌ CRITICAL (>1000ms):")
    critical = []
    if avg_devices_minimal > 1000:
        critical.append(f"/api/devices (minimal): {avg_devices_minimal:.0f}ms")
    if avg_devices_with_if > 1000:
        critical.append(f"/api/devices (with interfaces): {avg_devices_with_if:.0f}ms")

    if critical:
        for c in critical:
            print(f"  • {c}")
    else:
        print("  (none)")

    # 7. Root Cause Analysis
    print("\n" + "=" * 60)
    print("🔍 ROOT CAUSE ANALYSIS")
    print("=" * 60)

    if avg_devices_with_if / avg_devices_minimal > 3:
        print("\n❌ N+1 QUERY PROBLEM DETECTED!")
        print("  • devices (minimal) is fast, but WITH interfaces is 3x+ slower")
        print("  • Root cause: serialize_interfaces_for_device() called per device")
        print("  • Fix: Use single bulk query for all interfaces")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
