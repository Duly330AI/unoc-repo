"""Tests for transiting IPs endpoint (passive devices like splitters)."""

from backend.api.endpoints.devices_helpers_transiting_ips import (
    get_device_transiting_ips_impl,
)
from backend.db import get_session, init_db
from backend.models import Device, DeviceType


def test_transiting_ips_splitter_is_passive():
    """Test that splitter is correctly identified as passive device."""
    init_db()
    with get_session() as s:
        # Create splitter (passive device)
        splitter = Device(
            id="test_splitter",
            name="TestSplitter",
            type=DeviceType.SPLITTER,
        )
        s.add(splitter)
        s.commit()

        # Get transiting IPs
        result = get_device_transiting_ips_impl(s, "test_splitter")

        # Assertions
        assert result["device_id"] == "test_splitter"
        assert result["device_name"] == "TestSplitter"
        assert result["device_type"] == "SPLITTER"
        assert result["is_passive"] is True  # Splitter is passive
        assert "transiting_ips" in result
        assert "ip_pools" in result


def test_transiting_ips_olt_is_active():
    """Test that OLT is correctly identified as active device (NOT passive)."""
    init_db()
    with get_session() as s:
        # Create OLT (active device with electronics)
        olt = Device(
            id="test_olt",
            name="TestOLT",
            type=DeviceType.OLT,
        )
        s.add(olt)
        s.commit()

        # Get transiting IPs
        result = get_device_transiting_ips_impl(s, "test_olt")

        # Assertions
        assert result["device_id"] == "test_olt"
        assert result["device_name"] == "TestOLT"
        assert result["device_type"] == "OLT"
        assert result["is_passive"] is False  # OLT is ACTIVE (has OLT-Card, IPs)


def test_transiting_ips_device_not_found():
    """Test transiting IPs for non-existent device."""
    init_db()
    with get_session() as s:
        try:
            get_device_transiting_ips_impl(s, "nonexistent_device")
            assert False, "Should have raised LookupError"
        except LookupError as e:
            assert "not found" in str(e).lower()
