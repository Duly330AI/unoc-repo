"""
Integration test for TrafficGoClient.

Tests Python ↔ Go communication via HTTP API.
Validates traffic generation, aggregation, and snapshot retrieval.

REQUIRES: Traffic Engine Go service (port 8080)
"""

import pytest

from backend.clients.traffic_go_client import TrafficGoClient

pytestmark = pytest.mark.integration  # Mark entire module as integration test


@pytest.fixture
def go_client():
    """Fixture: TrafficGoClient instance."""
    client = TrafficGoClient(base_url="http://localhost:8080", timeout=10.0)
    yield client
    client.close()


def test_health_check(go_client):
    """Test: GET /health returns healthy status."""
    health = go_client.health()

    assert health["status"] == "healthy", "Service should be healthy"
    assert health["database"] == "healthy", "Database connection should be healthy"
    assert "version" in health, "Version should be present"


def test_traffic_tick(go_client):
    """Test: POST /api/v1/tick generates traffic successfully."""
    result = go_client.tick()

    # Validate response structure
    assert result["success"] is True, "Tick should succeed"
    assert "tick" in result, "Tick number should be present"
    assert "leaves_count" in result, "Leaves count should be present"
    assert "devices_with_traffic" in result, "Devices count should be present"
    assert "links_with_traffic" in result, "Links count should be present"
    assert "duration_ms" in result, "Duration should be present"

    # Validate traffic was generated (ont_test1 has path to pop1)
    assert result["leaves_count"] >= 1, "At least 1 leaf should be processed (ont_test1)"
    assert result["devices_with_traffic"] >= 1, "At least 1 device should have traffic"

    # Validate performance (target: <50ms @ small topology)
    assert (
        result["duration_ms"] < 100
    ), f"Tick should be fast (<100ms), got {result['duration_ms']}ms"


def test_snapshot_retrieval(go_client):
    """Test: GET /api/v1/snapshot returns traffic metrics."""
    # First trigger a tick to generate traffic
    go_client.tick()

    # Then retrieve snapshot
    snapshot = go_client.snapshot()

    # Validate response structure
    assert "tick" in snapshot, "Tick number should be present"
    assert "timestamp" in snapshot, "Timestamp should be present"
    assert "leaves_count" in snapshot, "Leaves count should be present"
    assert "device_metrics" in snapshot, "Device metrics should be present"
    assert "link_metrics" in snapshot, "Link metrics should be present"

    # Validate metrics structure
    device_metrics = snapshot["device_metrics"]
    assert isinstance(device_metrics, dict), "Device metrics should be a dict"

    if device_metrics:
        # Check first device has required fields
        first_device = next(iter(device_metrics.values()))
        assert "up_mbps" in first_device, "Device should have up_mbps"
        assert "down_mbps" in first_device, "Device should have down_mbps"
        assert "utilization" in first_device, "Device should have utilization"

    link_metrics = snapshot["link_metrics"]
    assert isinstance(link_metrics, dict), "Link metrics should be a dict"

    if link_metrics:
        # Check first link has required fields
        first_link = next(iter(link_metrics.values()))
        assert "traffic_mbps" in first_link, "Link should have traffic_mbps"
        assert "capacity_mbps" in first_link, "Link should have capacity_mbps"
        assert "utilization" in first_link, "Link should have utilization"


def test_multiple_ticks(go_client):
    """Test: Multiple ticks increment tick counter."""
    result1 = go_client.tick()
    tick1 = result1["tick"]

    result2 = go_client.tick()
    tick2 = result2["tick"]

    assert tick2 > tick1, "Tick counter should increment"


def test_context_manager():
    """Test: TrafficGoClient works as context manager."""
    with TrafficGoClient() as client:
        health = client.health()
        assert health["status"] == "healthy"

    # Client should be closed after context exit
    # (no exception should be raised)


def test_realistic_traffic_values(go_client):
    """Test: Traffic values are realistic (match tariff bounds)."""
    # Trigger tick
    go_client.tick()

    # Get snapshot
    snapshot = go_client.snapshot()

    # ont_test1 has tariff_id=1 (Residential 100/20)
    # Max: down=100 Mbps, up=20 Mbps
    # Generated: 80-100% of max
    device_metrics = snapshot["device_metrics"]

    if "ont_test1" in device_metrics:
        ont_metrics = device_metrics["ont_test1"]

        # Down traffic should be 80-100 Mbps (80-100% of 100)
        assert (
            80.0 <= ont_metrics["down_mbps"] <= 100.0
        ), f"ont_test1 down traffic should be 80-100 Mbps, got {ont_metrics['down_mbps']}"

        # Up traffic should be 16-20 Mbps (80-100% of 20)
        assert (
            16.0 <= ont_metrics["up_mbps"] <= 20.0
        ), f"ont_test1 up traffic should be 16-20 Mbps, got {ont_metrics['up_mbps']}"


def test_aggregation_along_path(go_client):
    """Test: Traffic is aggregated along path (ont → olt → core → pop)."""
    # Trigger tick
    go_client.tick()

    # Get snapshot
    snapshot = go_client.snapshot()
    device_metrics = snapshot["device_metrics"]

    # ont_test1 should have traffic
    if "ont_test1" in device_metrics:
        ont_traffic = device_metrics["ont_test1"]["down_mbps"]

        # Intermediate devices (olt1, core1) should also have traffic
        # (aggregated from downstream ONT)
        if "olt1" in device_metrics:
            olt_traffic = device_metrics["olt1"]["down_mbps"]
            assert (
                olt_traffic >= ont_traffic * 0.9
            ), f"OLT traffic ({olt_traffic}) should be >= ONT traffic ({ont_traffic})"

        if "core1" in device_metrics:
            core_traffic = device_metrics["core1"]["down_mbps"]
            assert (
                core_traffic >= ont_traffic * 0.9
            ), f"Core traffic ({core_traffic}) should be >= ONT traffic ({ont_traffic})"
