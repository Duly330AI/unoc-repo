"""Quick test script for Go traffic engine HTTP API."""

import json

import httpx

BASE_URL = "http://localhost:8080"


def test_health():
    """Test GET /health endpoint."""
    print("\n=== Testing GET /health ===")
    response = httpx.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check passed")


def test_tick():
    """Test POST /api/v1/tick endpoint."""
    print("\n=== Testing POST /api/v1/tick ===")
    payload = {"tick": 1, "random_seed": 0xAA55AA55}
    response = httpx.post(f"{BASE_URL}/api/v1/tick", json=payload, timeout=60.0)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    assert response.status_code == 200
    assert result["success"] is True
    print(f"✅ Tick completed: {result['leaves_count']} leaves, {result['duration_ms']:.2f}ms")


def test_snapshot():
    """Test GET /api/v1/snapshot endpoint."""
    print("\n=== Testing GET /api/v1/snapshot ===")
    response = httpx.get(f"{BASE_URL}/api/v1/snapshot")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response keys: {list(result.keys())}")
    print(f"Tick: {result['tick']}")
    print(f"Devices with traffic: {len(result['device_metrics'])}")
    print(f"Links with traffic: {len(result['link_metrics'])}")
    print(f"Leaves count: {result['leaves_count']}")
    assert response.status_code == 200
    print("✅ Snapshot retrieved")


if __name__ == "__main__":
    try:
        test_health()
        test_tick()
        test_snapshot()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
