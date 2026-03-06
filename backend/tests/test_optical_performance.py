"""Performance validation for Optical Compute Service (Day 16 Phase 5).

Benchmarks Go service performance vs Python baseline:
- Single ONT path resolution: Target < 50ms (Python: 40s = 800× speedup)
- Batch 64 ONTs recompute: Target < 3s (Python: 42min = 840× speedup)

NOTE: Requires Go optical-service running on port 50051.
"""

import time

import pytest

from backend.clients.go_services.optical_client import OpticalClient


@pytest.fixture
def optical_client():
    """Provide OpticalClient instance for benchmarks."""
    client = OpticalClient()

    # Verify Go service is available
    health = client.health()
    if not health.get("available") or health.get("backend") != "go":
        pytest.skip("Go optical-service not available for performance test")

    return client


def test_single_ont_path_performance(optical_client):
    """Benchmark single ONT path resolution (target: < 50ms)."""
    ont_id = "test_ont_perf_single"

    # Warm-up call (first call may be slower due to gRPC channel setup)
    optical_client.get_path(ont_id=ont_id)

    # Actual benchmark (10 iterations)
    durations = []
    for _ in range(10):
        start = time.perf_counter()
        result = optical_client.get_path(ont_id=ont_id)
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)

        # Validate response
        assert isinstance(result, dict), "Result must be dict"
        assert result.get("backend") == "go", "Must use Go backend"

    # Calculate statistics
    avg_ms = sum(durations) / len(durations)
    min_ms = min(durations)
    max_ms = max(durations)

    print("\n=== Single ONT Path Performance ===")
    print(f"Average: {avg_ms:.2f}ms")
    print(f"Min: {min_ms:.2f}ms")
    print(f"Max: {max_ms:.2f}ms")
    print("Target: < 50ms")
    print(f"Result: {'✅ PASS' if avg_ms < 50 else '❌ FAIL'}")

    # Assert performance target
    assert avg_ms < 50, f"Average duration {avg_ms:.2f}ms exceeds 50ms target"


def test_batch_recompute_performance(optical_client):
    """Benchmark batch ONT recompute (target: < 3000ms for 64 ONTs)."""
    # Simulate 64 ONT IDs (empty for now - just measures gRPC overhead)
    device_ids = [f"ont_{i}" for i in range(64)]

    # Warm-up call
    optical_client.recompute_paths(link_ids=[], device_ids=[])

    # Actual benchmark (3 iterations)
    durations = []
    for _ in range(3):
        start = time.perf_counter()
        result = optical_client.recompute_paths(link_ids=[], device_ids=device_ids)
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)

        # Validate response
        assert isinstance(result, dict), "Result must be dict"
        assert result.get("backend") == "go", "Must use Go backend"

    # Calculate statistics
    avg_ms = sum(durations) / len(durations)
    min_ms = min(durations)
    max_ms = max(durations)

    print("\n=== Batch 64 ONTs Recompute Performance ===")
    print(f"Average: {avg_ms:.2f}ms")
    print(f"Min: {min_ms:.2f}ms")
    print(f"Max: {max_ms:.2f}ms")
    print("Target: < 3000ms (3s)")
    print(f"Result: {'✅ PASS' if avg_ms < 3000 else '❌ FAIL'}")

    # Assert performance target
    assert avg_ms < 3000, f"Average duration {avg_ms:.2f}ms exceeds 3000ms (3s) target"


def test_health_check_performance(optical_client):
    """Benchmark health check latency (baseline for gRPC overhead)."""
    # Warm-up
    optical_client.health()

    # Benchmark (20 iterations)
    durations = []
    for _ in range(20):
        start = time.perf_counter()
        health = optical_client.health()
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)

        assert health.get("backend") == "go", "Must use Go backend"

    avg_ms = sum(durations) / len(durations)
    min_ms = min(durations)
    max_ms = max(durations)

    print("\n=== Health Check Performance (gRPC Baseline) ===")
    print(f"Average: {avg_ms:.2f}ms")
    print(f"Min: {min_ms:.2f}ms")
    print(f"Max: {max_ms:.2f}ms")

    # Health check should be very fast (< 10ms typical)
    assert avg_ms < 20, f"Health check too slow: {avg_ms:.2f}ms"
