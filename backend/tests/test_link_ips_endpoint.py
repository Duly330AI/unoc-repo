"""Tests for link IPs endpoint."""

from backend.api.endpoints.links_helpers_ips import get_link_ips_impl
from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, InterfaceAddress, Link


def test_link_ips_with_addresses():
    """Test link IPs when both interfaces have IP addresses."""
    init_db()
    with get_session() as s:
        # Create two devices
        dev_a = Device(id="dev_a", name="DeviceA", type=DeviceType.CORE_ROUTER)
        dev_b = Device(id="dev_b", name="DeviceB", type=DeviceType.CORE_ROUTER)
        s.add_all([dev_a, dev_b])

        # Create interfaces
        if_a = Interface(id="if_a", device_id="dev_a", name="eth0")
        if_b = Interface(id="if_b", device_id="dev_b", name="eth0")
        s.add_all([if_a, if_b])

        # Create link
        link = Link(id="link1", a_interface_id="if_a", b_interface_id="if_b")
        s.add(link)

        # Add IPs to both interfaces (same subnet)
        ip_a = InterfaceAddress(interface_id="if_a", ip="10.0.1.1", prefix_len=24)
        ip_b = InterfaceAddress(interface_id="if_b", ip="10.0.1.2", prefix_len=24)
        s.add_all([ip_a, ip_b])

        s.commit()

        # Get link IPs
        result = get_link_ips_impl(s, "link1")

        # Assertions
        assert result["link_id"] == "link1"

        # Check interface A
        assert result["a_interface"]["interface_id"] == "if_a"
        assert result["a_interface"]["interface_name"] == "eth0"
        assert result["a_interface"]["device_name"] == "DeviceA"
        assert len(result["a_interface"]["ips"]) == 1
        assert result["a_interface"]["ips"][0]["ip"] == "10.0.1.1"
        assert result["a_interface"]["ips"][0]["prefix_len"] == 24
        assert result["a_interface"]["ips"][0]["full"] == "10.0.1.1/24"

        # Check interface B
        assert result["b_interface"]["interface_id"] == "if_b"
        assert result["b_interface"]["interface_name"] == "eth0"
        assert result["b_interface"]["device_name"] == "DeviceB"
        assert len(result["b_interface"]["ips"]) == 1
        assert result["b_interface"]["ips"][0]["ip"] == "10.0.1.2"

        # Check common subnet detection
        assert result["common_subnet"] == "10.0.1.0/24"


def test_link_ips_no_addresses():
    """Test link IPs when interfaces have no IP addresses."""
    init_db()
    with get_session() as s:
        # Create two devices
        dev_a = Device(id="dev_c", name="DeviceC", type=DeviceType.AON_SWITCH)
        dev_b = Device(id="dev_d", name="DeviceD", type=DeviceType.AON_SWITCH)
        s.add_all([dev_a, dev_b])

        # Create interfaces without IPs
        if_a = Interface(id="if_c", device_id="dev_c", name="port1")
        if_b = Interface(id="if_d", device_id="dev_d", name="port1")
        s.add_all([if_a, if_b])

        # Create link
        link = Link(id="link2", a_interface_id="if_c", b_interface_id="if_d")
        s.add(link)

        s.commit()

        # Get link IPs
        result = get_link_ips_impl(s, "link2")

        # Assertions
        assert result["link_id"] == "link2"
        assert len(result["a_interface"]["ips"]) == 0
        assert len(result["b_interface"]["ips"]) == 0
        assert result["common_subnet"] is None  # No common subnet without IPs


def test_link_ips_link_not_found():
    """Test link IPs for non-existent link."""
    init_db()
    with get_session() as s:
        try:
            get_link_ips_impl(s, "nonexistent_link")
            assert False, "Should have raised LookupError"
        except LookupError as e:
            assert "not found" in str(e).lower()
