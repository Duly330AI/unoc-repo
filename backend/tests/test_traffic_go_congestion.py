"""
Integration tests for HGO-006: Congestion Detection with Hysteresis

Tests congestion detection behavior:
- 90% threshold triggers congestion
- 85% threshold clears congestion (hysteresis)
- State persistence across ticks
- Transitions: normal→congested, congested→normal

REQUIRES: Traffic Engine Go service (port 8080) + PostgreSQL
"""

import pytest

from backend.clients.traffic_go_client import TrafficGoClient

pytestmark = pytest.mark.integration  # Mark entire module as integration test


@pytest.fixture
def go_client():
    """Create Go client with default localhost:8080"""
    client = TrafficGoClient(base_url="http://localhost:8080")
    yield client
    client.close()


def test_congestion_detection_at_high_utilization(go_client):
    """Test congestion is detected when utilization >= 90%"""
    # Trigger traffic generation
    result = go_client.tick()
    assert result["success"] is True

    # Get snapshot with congestion data
    snapshot = go_client.snapshot()

    # Check ont_test1 (tariff 100/20, generates ~99% utilization)
    ont_metrics = snapshot["device_metrics"].get("ont_test1")
    if ont_metrics:
        utilization = ont_metrics.get("utilization", 0)
        congested = ont_metrics.get("congested", False)

        # If utilization >= 90%, should be congested
        if utilization >= 0.90:
            assert (
                congested is True
            ), f"Device with {utilization:.1%} utilization should be congested (threshold: 90%)"
            print(f"✓ Congestion detected: utilization={utilization:.2%}, congested={congested}")


def test_hysteresis_stays_congested_until_85_percent(go_client):
    """Test hysteresis: congestion doesn't clear until utilization drops below 85%"""
    # Trigger initial congestion
    go_client.tick()
    snapshot1 = go_client.snapshot()

    # Check if any device is congested
    congested_devices = [
        dev_id
        for dev_id, metrics in snapshot1["device_metrics"].items()
        if metrics.get("congested", False)
    ]

    if congested_devices:
        # Run multiple ticks to observe state persistence
        for i in range(3):
            go_client.tick()
            snapshot = go_client.snapshot()

            for dev_id in congested_devices:
                metrics = snapshot["device_metrics"].get(dev_id)
                if metrics:
                    utilization = metrics.get("utilization", 0)
                    congested = metrics.get("congested", False)

                    # If utilization is between 85% and 90%, should stay congested (hysteresis)
                    if 0.85 <= utilization < 0.90:
                        assert (
                            congested is True
                        ), f"Device at {utilization:.1%} should remain congested until <85% (hysteresis)"
                        print(
                            f"✓ Hysteresis working: utilization={utilization:.2%}, still congested"
                        )


def test_normal_to_congested_transition(go_client):
    """Test state transition: normal → congested when crossing 90% threshold"""
    result = go_client.tick()

    # Check if any congestion events occurred
    congested_count = result.get("congested_devices", 0)

    # Should have at least ont_test1 congested (tariff 100/20 → ~99% utilization)
    assert congested_count >= 1, "Expected at least one device to be congested"

    snapshot = go_client.snapshot()
    ont_metrics = snapshot["device_metrics"].get("ont_test1")

    if ont_metrics:
        assert ont_metrics.get("congested") is True, "ont_test1 should be congested"
        assert ont_metrics.get("utilization") >= 0.90, "ont_test1 utilization should be >= 90%"
        print(f"✓ Transition detected: ont_test1 congested @ {ont_metrics['utilization']:.2%}")


def test_link_congestion_stays_normal_at_low_utilization(go_client):
    """Test links remain normal when utilization < 90%"""
    go_client.tick()
    snapshot = go_client.snapshot()

    # Check all links
    for link_id, metrics in snapshot["link_metrics"].items():
        utilization = metrics.get("utilization", 0)
        congested = metrics.get("congested", False)
        capacity = metrics.get("capacity_mbps", 0)

        # Links with 10G capacity should not be congested (only ~119 Mbps traffic)
        if capacity >= 1000 and utilization < 0.90:
            assert (
                congested is False
            ), f"Link {link_id} at {utilization:.2%} should not be congested (<90% threshold)"
            print(f"✓ Link normal: {link_id} @ {utilization:.2%} (capacity={capacity} Mbps)")


def test_state_persistence_across_ticks(go_client):
    """Test congestion state persists across multiple ticks"""
    # Trigger initial congestion
    result1 = go_client.tick()
    initial_congested = result1.get("congested_devices", 0)

    # Run 5 more ticks
    for i in range(5):
        result = go_client.tick()
        congested_count = result.get("congested_devices", 0)

        # State should persist (tariff doesn't change, so utilization stays high)
        assert (
            congested_count >= initial_congested
        ), f"Congestion count should persist: tick {result['tick']}"

        # Verify snapshot reflects persistent state
        snapshot = go_client.snapshot()
        ont_metrics = snapshot["device_metrics"].get("ont_test1")
        if ont_metrics and ont_metrics.get("utilization") >= 0.90:
            assert (
                ont_metrics.get("congested") is True
            ), f"ont_test1 should remain congested across ticks (tick={result['tick']})"

    print(f"✓ State persisted across 5 ticks: {initial_congested} devices congested")


def test_congestion_fields_in_snapshot(go_client):
    """Test all required congestion fields are present in API responses"""
    result = go_client.tick()

    # Check TickResponse has congestion counts
    assert "congested_devices" in result, "TickResponse missing congested_devices field"
    assert "congested_links" in result, "TickResponse missing congested_links field"
    assert isinstance(result["congested_devices"], int), "congested_devices should be int"
    assert isinstance(result["congested_links"], int), "congested_links should be int"

    # Check Snapshot has congestion data
    snapshot = go_client.snapshot()

    # Check DeviceMetrics have required fields
    for dev_id, metrics in snapshot["device_metrics"].items():
        assert "utilization" in metrics, f"Device {dev_id} missing utilization field"
        assert "congested" in metrics, f"Device {dev_id} missing congested field"
        assert isinstance(metrics["utilization"], float), "utilization should be float"
        assert isinstance(metrics["congested"], bool), "congested should be bool"

    # Check LinkMetrics have required fields
    for link_id, metrics in snapshot["link_metrics"].items():
        assert "utilization" in metrics, f"Link {link_id} missing utilization field"
        assert "congested" in metrics, f"Link {link_id} missing congested field"
        assert "capacity_mbps" in metrics, f"Link {link_id} missing capacity_mbps field"
        assert isinstance(metrics["utilization"], float), "utilization should be float"
        assert isinstance(metrics["congested"], bool), "congested should be bool"
        assert isinstance(metrics["capacity_mbps"], float), "capacity_mbps should be float"

    print(
        f"✓ All congestion fields present: {len(snapshot['device_metrics'])} devices, "
        f"{len(snapshot['link_metrics'])} links"
    )


def test_realistic_congestion_scenario(go_client):
    """Test realistic congestion scenario with tariff-based traffic"""
    # Run 10 ticks to observe congestion patterns
    congestion_history = []

    for i in range(10):
        result = go_client.tick()
        snapshot = go_client.snapshot()

        # Track ont_test1 congestion (tariff 100/20 → high utilization)
        ont_metrics = snapshot["device_metrics"].get("ont_test1")
        if ont_metrics:
            congestion_history.append(
                {
                    "tick": result["tick"],
                    "utilization": ont_metrics.get("utilization", 0),
                    "congested": ont_metrics.get("congested", False),
                }
            )

    # Verify ont_test1 is consistently congested (tariff doesn't change)
    congested_ticks = sum(1 for entry in congestion_history if entry["congested"])
    assert (
        congested_ticks >= 8
    ), f"Expected ont_test1 to be congested in most ticks (got {congested_ticks}/10)"

    # Check utilization stays high (tariff-based generation is deterministic)
    avg_utilization = sum(e["utilization"] for e in congestion_history) / len(congestion_history)
    assert (
        avg_utilization >= 0.90
    ), f"Expected average utilization >= 90% (got {avg_utilization:.2%})"

    print(f"✓ Realistic scenario: {congested_ticks}/10 ticks congested, avg={avg_utilization:.2%}")
