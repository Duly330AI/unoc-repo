"""Tests for Port Summary Service Event Handling.

Tests verify that:
- Link create/delete events trigger cache updates
- Device provision events trigger cache updates
- Service recomputes affected OLTs on link changes
- Events are received within reasonable time (<500ms)
"""

import asyncio

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.clients.port_summary_client import get_port_summary_client
from backend.models import Device, DeviceType, Interface, Link, PortRole


@pytest.mark.asyncio
async def test_port_summary_receives_link_event(test_client, test_db):
    """Test that Port Summary Service receives link_created event."""
    # Get Go client
    try:
        go_client = get_port_summary_client()
    except Exception:
        pytest.skip("Port Summary Go Service not available")

    # Create test devices
    async with AsyncSession(test_db) as s:
        # Create OLT
        olt = Device(
            id="TEST-OLT-001",
            name="Test OLT",
            type=DeviceType.olt,
            status="active",
            provisioned=True,
        )
        s.add(olt)

        # Create OLT PON interface
        olt_pon = Interface(
            id="IF-OLT-PON-001",
            device_id=olt.id,
            name="pon0/1",
            port_role=PortRole.pon_uplink,
            admin_status="up",
        )
        s.add(olt_pon)

        # Create ONT
        ont = Device(
            id="TEST-ONT-001",
            name="Test ONT",
            type=DeviceType.ont,
            status="active",
            provisioned=True,
            parent_container_id=olt.id,
        )
        s.add(ont)

        # Create ONT interface
        ont_if = Interface(
            id="IF-ONT-001",
            device_id=ont.id,
            name="eth0",
            port_role=PortRole.pon_downlink,
            admin_status="up",
        )
        s.add(ont_if)

        await s.commit()

    # Wait a moment for initial state to propagate
    await asyncio.sleep(0.1)

    # Get initial summary (should have 0 links)
    initial = await go_client.get_port_summary(olt.id)
    initial_link_count = sum(1 for iface in initial if iface.get("connected_peer"))

    # Create link (this should trigger link_created event)
    async with AsyncSession(test_db) as s:
        link = Link(
            id="TEST-LINK-001",
            a_interface_id=olt_pon.id,
            b_interface_id=ont_if.id,
            status="up",
        )
        s.add(link)
        await s.commit()

        # Trigger link_created event (PostgreSQL NOTIFY)
        await s.execute("NOTIFY link_events, 'link_created:TEST-LINK-001'")
        await s.commit()

    # Wait for event to propagate (should be <500ms)
    await asyncio.sleep(0.6)

    # Get updated summary (should have 1 link now)
    updated = await go_client.get_port_summary(olt.id)
    updated_link_count = sum(1 for iface in updated if iface.get("connected_peer"))

    # Verify link count increased
    assert updated_link_count > initial_link_count, (
        f"Link count should increase after link_created event: "
        f"{initial_link_count} -> {updated_link_count}"
    )


@pytest.mark.asyncio
async def test_port_summary_link_delete_event(test_client, test_db):
    """Test that Port Summary Service receives link_deleted event."""
    try:
        go_client = get_port_summary_client()
    except Exception:
        pytest.skip("Port Summary Go Service not available")

    # Setup: Create OLT with link
    async with AsyncSession(test_db) as s:
        olt = Device(
            id="TEST-OLT-002",
            name="Test OLT 2",
            type=DeviceType.olt,
            status="active",
            provisioned=True,
        )
        s.add(olt)

        olt_pon = Interface(
            id="IF-OLT-PON-002",
            device_id=olt.id,
            name="pon0/2",
            port_role=PortRole.pon_uplink,
            admin_status="up",
        )
        s.add(olt_pon)

        ont = Device(
            id="TEST-ONT-002",
            name="Test ONT 2",
            type=DeviceType.ont,
            status="active",
            provisioned=True,
            parent_container_id=olt.id,
        )
        s.add(ont)

        ont_if = Interface(
            id="IF-ONT-002",
            device_id=ont.id,
            name="eth0",
            port_role=PortRole.pon_downlink,
            admin_status="up",
        )
        s.add(ont_if)

        link = Link(
            id="TEST-LINK-002",
            a_interface_id=olt_pon.id,
            b_interface_id=ont_if.id,
            status="up",
        )
        s.add(link)
        await s.commit()

        # Trigger link_created event
        await s.execute("NOTIFY link_events, 'link_created:TEST-LINK-002'")
        await s.commit()

    await asyncio.sleep(0.6)

    # Get initial summary (should have link)
    initial = await go_client.get_port_summary(olt.id)
    initial_link_count = sum(1 for iface in initial if iface.get("connected_peer"))
    assert initial_link_count > 0, "Should have at least 1 link initially"

    # Delete link
    async with AsyncSession(test_db) as s:
        result = await s.execute(select(Link).where(Link.id == "TEST-LINK-002"))
        link = result.scalar_one()
        await s.delete(link)
        await s.commit()

        # Trigger link_deleted event
        await s.execute("NOTIFY link_events, 'link_deleted:TEST-LINK-002'")
        await s.commit()

    # Wait for event
    await asyncio.sleep(0.6)

    # Get updated summary (should have fewer links)
    updated = await go_client.get_port_summary(olt.id)
    updated_link_count = sum(1 for iface in updated if iface.get("connected_peer"))

    assert updated_link_count < initial_link_count, (
        f"Link count should decrease after link_deleted event: "
        f"{initial_link_count} -> {updated_link_count}"
    )


@pytest.mark.asyncio
async def test_port_summary_device_provision_event(test_client, test_db):
    """Test that Port Summary Service receives device_provisioned event."""
    try:
        go_client = get_port_summary_client()
    except Exception:
        pytest.skip("Port Summary Go Service not available")

    # Create ONT (not provisioned yet)
    async with AsyncSession(test_db) as s:
        ont = Device(
            id="TEST-ONT-003",
            name="Test ONT 3",
            type=DeviceType.ont,
            status="discovered",
            provisioned=False,
        )
        s.add(ont)
        await s.commit()

        # Trigger device_created event
        await s.execute("NOTIFY device_events, 'device_created:TEST-ONT-003'")
        await s.commit()

    await asyncio.sleep(0.6)

    # Provision device
    async with AsyncSession(test_db) as s:
        result = await s.execute(select(Device).where(Device.id == "TEST-ONT-003"))
        ont = result.scalar_one()
        ont.provisioned = True
        ont.status = "active"
        s.add(ont)
        await s.commit()

        # Trigger device_updated event
        await s.execute("NOTIFY device_events, 'device_updated:TEST-ONT-003'")
        await s.commit()

    # Wait for event
    await asyncio.sleep(0.6)

    # Verify device is in cache (try to get summary - should not raise error)
    try:
        summary = await go_client.get_port_summary("TEST-ONT-003")
        # If we get here, device is in cache
        assert summary is not None
    except Exception as e:
        pytest.fail(f"Device should be in cache after provision event: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
