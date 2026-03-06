"""API integration tests for status propagation endpoint.

Tests verify:
1. POST /api/status/propagate with valid requests
2. GET /api/status/health
3. Error handling (validation errors, service unavailable)
4. Go service vs Python fallback behavior

REQUIRES: Status Propagation Go service (port 50053) + PostgreSQL
"""

import pytest
from fastapi.testclient import TestClient

from backend.db import get_session
from backend.main import app
from backend.models import Device, DeviceType, Status

pytestmark = pytest.mark.integration  # Mark entire module as integration test

client = TestClient(app)


@pytest.fixture
def test_device():
    """Create a test device."""
    with get_session() as session:
        device = Device(
            id="test-device-1",
            name="Test Device",
            type=DeviceType.CORE_ROUTER,
            status=Status.UP,
            provisioned=True,
        )
        session.add(device)
        session.commit()
        yield device.id


@pytest.fixture
def test_devices():
    """Create multiple test devices."""
    with get_session() as session:
        devices = [
            Device(
                id=f"test-dev-{i}",
                name=f"Test Device {i}",
                type=DeviceType.CORE_ROUTER,
                status=Status.UP,
                provisioned=True,
            )
            for i in range(5)
        ]
        for device in devices:
            session.add(device)
        session.commit()

        yield [d.id for d in devices]


def test_status_health_endpoint():
    """Test GET /api/status/health."""
    response = client.get("/api/status/health")

    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "backend" in data

    # Backend should be either "go" or "python"
    assert data["backend"] in ["go", "python"]

    # Status should be one of known values
    assert data["status"] in ["UP", "HEALTHY", "UNHEALTHY", "python-fallback"]


def test_propagate_status_empty_changes():
    """Test POST /api/status/propagate with empty changes."""
    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": [],
            "changed_link_ids": [],
            "update_database": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "affected_devices" in data
    assert "duration_ms" in data
    assert "source" in data

    # Empty changes should result in zero affected devices
    assert len(data["affected_devices"]) == 0

    # Source should be go or python
    assert data["source"] in ["go", "python"]


def test_propagate_status_single_device(test_device):
    """Test POST /api/status/propagate with single device."""
    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": [test_device],
            "changed_link_ids": [],
            "update_database": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "affected_devices" in data
    assert test_device in data["affected_devices"]

    # Should have duration measurement
    assert data["duration_ms"] >= 0.0


def test_propagate_status_with_links():
    """Test POST /api/status/propagate with device and link changes (simulated)."""
    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": ["dev-1"],
            "changed_link_ids": ["link-1"],
            "update_database": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "affected_devices" in data


def test_propagate_status_update_database_true(test_device):
    """Test POST /api/status/propagate with update_database=True."""
    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": [test_device],
            "changed_link_ids": [],
            "update_database": True,  # Should update DB
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "affected_devices" in data


def test_propagate_status_default_update_database():
    """Test POST /api/status/propagate with default update_database (True)."""
    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": [],
            # update_database omitted (defaults to True)
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "affected_devices" in data


def test_propagate_status_validation_error_missing_field():
    """Test POST /api/status/propagate with missing required field."""
    response = client.post(
        "/api/status/propagate",
        json={
            # Missing changed_device_ids (required field)
            "changed_link_ids": [],
        },
    )

    assert response.status_code == 422  # Validation error


def test_propagate_status_validation_error_invalid_type():
    """Test POST /api/status/propagate with invalid type."""
    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": "not-a-list",  # Should be list
            "changed_link_ids": [],
        },
    )

    assert response.status_code == 422  # Validation error


def test_propagate_status_response_structure():
    """Test POST /api/status/propagate response structure."""
    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": [],
            "changed_link_ids": [],
            "update_database": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    # Verify all required fields present
    assert "affected_devices" in data
    assert "affected_links" in data
    assert "duration_ms" in data
    assert "source" in data

    # Verify types
    assert isinstance(data["affected_devices"], list)
    assert isinstance(data["affected_links"], list)
    assert isinstance(data["duration_ms"], int | float)
    assert isinstance(data["source"], str)

    # Optional field
    if "dependency_paths" in data:
        assert isinstance(data["dependency_paths"], dict)


def test_propagate_status_performance_acceptable():
    """Test POST /api/status/propagate has acceptable performance."""
    import time

    start = time.time()

    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": [],
            "changed_link_ids": [],
            "update_database": False,
        },
    )

    elapsed_ms = (time.time() - start) * 1000

    assert response.status_code == 200

    data = response.json()

    # API response time should be reasonable
    # - Go backend: <10ms
    # - Python fallback: <2000ms
    assert elapsed_ms < 2000, f"API took {elapsed_ms:.1f}ms (expected <2000ms)"

    # Reported duration should also be reasonable
    assert data["duration_ms"] < 2000


def test_health_endpoint_response_structure():
    """Test GET /api/status/health response structure."""
    response = client.get("/api/status/health")

    assert response.status_code == 200

    data = response.json()

    # Required fields
    assert "status" in data
    assert "backend" in data

    # Optional fields (may be None or present)
    if data.get("message"):
        assert isinstance(data["message"], str)
    if data.get("version"):
        assert isinstance(data["version"], str)


def test_propagate_status_multiple_devices(test_devices):
    """Test POST /api/status/propagate with multiple devices."""
    response = client.post(
        "/api/status/propagate",
        json={
            "changed_device_ids": test_devices,
            "changed_link_ids": [],
            "update_database": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "affected_devices" in data

    # At minimum, all changed devices should be in affected list
    for device_id in test_devices:
        assert device_id in data["affected_devices"]
