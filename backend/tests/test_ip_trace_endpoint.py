"""Tests for IP trace endpoint - L3 path visualization."""

from backend.api.endpoints.devices_helpers_ip_trace import get_device_ip_trace_impl
from backend.db import get_session, init_db
from backend.models import VRF, Device, DeviceType, Interface, InterfaceAddress


def test_ip_trace_backbone_gateway():
    """Test IP trace for backbone gateway (trivial case - already at destination)."""
    init_db()

    with get_session() as session:
        # Create backbone gateway
        gateway = Device(
            id="backbone_gw",
            name="Backbone Gateway",
            type=DeviceType.BACKBONE_GATEWAY,
        )
        session.add(gateway)

        # Gateway interface
        gw_if = Interface(
            id="backbone_gw-wan",
            device_id="backbone_gw",
            name="wan0",
        )
        session.add(gw_if)

        # Gateway IP
        gw_ip = InterfaceAddress(
            interface_id="backbone_gw-wan",
            ip="192.168.0.1",
            prefix_len=30,
        )
        session.add(gw_ip)

        session.commit()

        # Test IP trace
        result = get_device_ip_trace_impl(session, "backbone_gw")

        # Assertions
        assert result["device_id"] == "backbone_gw"
        assert result["device_name"] == "Backbone Gateway"
        assert result["reachable"] is True
        assert result["reason"] is None

        # Check own IP
        assert len(result["own_ips"]) == 1
        assert result["own_ips"][0]["ip"] == "192.168.0.1/30"
        assert result["own_ips"][0]["interface"] == "wan0"

        # Path should only contain gateway itself
        assert len(result["path_to_gateway"]) == 1
        assert result["path_to_gateway"][0]["device_id"] == "backbone_gw"
        assert result["path_to_gateway"][0]["hop"] == 1


def test_ip_trace_unreachable_device():
    """Test IP trace for device without VRF/routes (unreachable)."""
    init_db()

    with get_session() as session:
        # Create VRF
        vrf = VRF(name="default")
        session.add(vrf)
        session.flush()

        # Create isolated device (has VRF but no default route)
        device = Device(
            id="isolated_device",
            name="Isolated Device",
            type=DeviceType.CORE_ROUTER,
            vrf_id=vrf.id,
        )
        session.add(device)
        session.commit()

        # Test IP trace
        result = get_device_ip_trace_impl(session, "isolated_device")

        # Assertions
        assert result["device_id"] == "isolated_device"
        assert result["reachable"] is False
        assert result["reason"] == "no_default_route"

        # Path should only contain the starting device
        assert len(result["path_to_gateway"]) == 1
        assert result["path_to_gateway"][0]["device_id"] == "isolated_device"


def test_ip_trace_device_not_found():
    """Test IP trace for non-existent device."""
    init_db()

    with get_session() as session:
        # Try to trace non-existent device
        try:
            get_device_ip_trace_impl(session, "nonexistent_device")
            assert False, "Should have raised LookupError"
        except LookupError as e:
            assert "not found" in str(e).lower()
