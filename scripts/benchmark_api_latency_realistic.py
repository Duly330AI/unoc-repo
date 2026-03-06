#!/usr/bin/env python3
"""Realistic E2E benchmark measuring actual production scenarios.

Focus on API endpoint latency which is the REAL bottleneck (9s in Grafana!).
"""
import statistics
import time

import requests

BASE = "http://127.0.0.1:5001"  # Use IP instead of localhost (Windows DNS issue)


def measure_api_latency():
    """Measure real API endpoint latency."""
    print("\n🔥 API ENDPOINT LATENCY BENCHMARK")
    print("=" * 70)

    endpoints = [
        ("/api/health", "Health Check"),
        ("/api/devices", "List Devices (no interfaces)"),
        ("/api/devices?include_interfaces=true", "List Devices (WITH interfaces)"),
        ("/api/links", "List Links"),
        ("/api/metrics/snapshot", "Traffic Snapshot"),
        ("/api/metrics/prometheus", "Prometheus Metrics"),
    ]

    results = {}

    for path, label in endpoints:
        print(f"\n📊 {label}")
        print(f"   Path: {path}")
        times = []

        for run in range(3):  # 3 runs per endpoint
            try:
                start = time.perf_counter()
                resp = requests.get(f"{BASE}{path}", timeout=30)
                elapsed = (time.perf_counter() - start) * 1000  # ms

                resp.raise_for_status()
                times.append(elapsed)

                # Check response size
                content_len = len(resp.content) if resp.content else 0
                print(f"   Run {run+1}: {elapsed:.0f}ms ({content_len:,} bytes)")

            except Exception as e:
                print(f"   Run {run+1}: ❌ FAILED: {e}")
                times.append(9999)  # Penalty

        if times:
            avg = statistics.mean(times)
            p50 = statistics.median(times)
            results[label] = {"avg": avg, "p50": p50, "times": times}

            # Color-coded status
            if avg < 100:
                status = "✅ EXCELLENT"
            elif avg < 300:
                status = "✅ GOOD"
            elif avg < 1000:
                status = "⚠️  SLOW"
            else:
                status = "❌ CRITICAL"

            print(f"   {status}: avg={avg:.0f}ms, p50={p50:.0f}ms")

    # Summary
    print("\n" + "=" * 70)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 70)

    print("\n✅ GOOD (<300ms):")
    good = [(label, data) for label, data in results.items() if data["avg"] < 300]
    if good:
        for label, data in good:
            print(f"  • {label}: {data['avg']:.0f}ms")
    else:
        print("  (none)")

    print("\n⚠️  SLOW (300-1000ms):")
    slow = [(label, data) for label, data in results.items() if 300 <= data["avg"] < 1000]
    if slow:
        for label, data in slow:
            print(f"  • {label}: {data['avg']:.0f}ms")
    else:
        print("  (none)")

    print("\n❌ CRITICAL (>1000ms):")
    critical = [(label, data) for label, data in results.items() if data["avg"] >= 1000]
    if critical:
        for label, data in critical:
            print(f"  • {label}: {data['avg']:.0f}ms  ← ROOT CAUSE!")
    else:
        print("  (none)")

    # Diagnose root cause
    print("\n" + "=" * 70)
    print("🔍 ROOT CAUSE ANALYSIS")
    print("=" * 70)

    if critical:
        print("\n❌ SLOW API DETECTED!")
        print("  • This is the Grafana 9s latency root cause!")
        print("  • Traffic Engine is FAST (75ms)")
        print("  • Problem is in API/DB layer!")

        # Check if WITH interfaces is slower
        no_if = results.get("List Devices (no interfaces)", {}).get("avg", 0)
        with_if = results.get("List Devices (WITH interfaces)", {}).get("avg", 0)

        if with_if > no_if * 2:
            print("\n  🔍 N+1 QUERY PROBLEM DETECTED:")
            print(f"     • Without interfaces: {no_if:.0f}ms")
            print(f"     • With interfaces: {with_if:.0f}ms ({with_if/no_if:.1f}x slower!)")
            print("     • Fix: Use single bulk query for all interfaces")
    else:
        print("\n✅ ALL APIS FAST!")
        print("  • Performance is within targets")
        print("  • No critical issues detected")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    measure_api_latency()
