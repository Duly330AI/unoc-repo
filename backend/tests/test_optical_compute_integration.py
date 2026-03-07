"""Integration tests for Optical Compute Service (Day 16 Week 3).

Tests Python gRPC client → Go Optical Service → Database flow.
Validates health checks, single ONT path resolution, and batch recompute.

Performance Target:
- Single ONT path: < 50ms (Python baseline: 40s = 800× speedup)
- Batch 64 ONTs: < 3s (Python baseline: 42min = 840× speedup)

REQUIRES: Optical PathFinder Go service (port 50051) + PostgreSQL
"""

import pytest

from backend.clients.go_services.optical_client import OpticalClient

pytestmark = pytest.mark.integration  # Mark entire module as integration test


@pytest.fixture
def optical_client():
    """Provide OpticalClient instance for tests."""
    return OpticalClient()


def test_optical_health_check_python_fallback(optical_client):
    """Test health check endpoint returns correct structure (Python fallback)."""
    health = optical_client.health()

    # Validate response structure
    assert isinstance(health, dict), "Health response must be dict"
    assert "status" in health, "Health must include 'status' field"
    assert "backend" in health, "Health must include 'backend' field"
    assert "available" in health, "Health must include 'available' field"

    # Python fallback should return backend='python'
    assert health["backend"] in [
        "python",
        "go",
    ], f"Backend must be 'python' or 'go', got: {health['backend']}"
    assert health["status"] in [
        "healthy",
        "degraded",
    ], f"Status must be 'healthy' or 'degraded', got: {health['status']}"


def test_get_path_python_fallback_no_ont(optical_client):
    """Test get_path() with nonexistent ONT returns path_exists=False (Python fallback)."""
    result = optical_client.get_path(ont_id="nonexistent_ont_9999")

    # Should return dict with path_exists=False for nonexistent ONT
    assert isinstance(result, dict), f"Expected dict, got: {type(result)}"
    assert "path_exists" in result, "Result must include 'path_exists' field"
    assert (
        result["path_exists"] is False
    ), f"Expected path_exists=False, got: {result['path_exists']}"
    assert result["ont_id"] == "nonexistent_ont_9999", "ONT ID must match input"


def test_recompute_paths_python_fallback_empty(optical_client):
    """Test recompute_paths() with empty inputs returns status=success (Python fallback)."""
    result = optical_client.recompute_paths(link_ids=[], device_ids=[])

    # Validate response structure
    assert isinstance(result, dict), "Result must be dict"
    assert "status" in result, "Result must include 'status' field"
    assert result["status"] == "success", f"Expected status='success', got: {result['status']}"
    assert "backend" in result, "Result must include 'backend' field"


# NOTE: Full integration tests with Go service running are in separate suite
# (test_optical_compute_go_integration.py) and require:
# 1. Go optical-service.exe running on port 50051
# 2. PostgreSQL database with test topology
# 3. Performance benchmarking setup
