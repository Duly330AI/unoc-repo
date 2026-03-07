from backend import events
from backend.db import get_session, init_db
from backend.models import (
    AdminStatus,
    Device,
    DeviceType,
    Interface,
    InterfaceAddress,
    Link,
    Neighbor,
    Route,
    Status,
)
from backend.services import status_propagation_store as propagation_store
from backend.services.status_recompute import recompute_devices_status
from backend.services.status_service import evaluate_device_status


def test_core_router_degrades_when_single_uplink_forced_down():
    """Provision a minimal topology core<->edge and force the only uplink link DOWN.

    Expect the edge router (non-backbone) to lose upstream L3 and transition to DOWN.
    (Routers map lack of upstream L3 to DOWN in current semantics.)
    """
    init_db()
    events.reset_events()
    with get_session() as s:
        # Create core (backbone gateway acts as anchor) and edge router
        core = Device(
            id="core1",
            name="core1",
            type=DeviceType.BACKBONE_GATEWAY,
            status=Status.UP,
            provisioned=True,
        )
        edge = Device(
            id="edge1",
            name="edge1",
            type=DeviceType.CORE_ROUTER,
            status=Status.UP,
            vrf_id=1,
            provisioned=True,
        )
        # Minimal management interfaces
        # Create simple management interfaces (admin up)
        core_if = Interface(
            id="core1-if0", device_id=core.id, name="if0", admin_status=AdminStatus.UP
        )
        edge_if = Interface(
            id="edge1-if0", device_id=edge.id, name="if0", admin_status=AdminStatus.UP
        )
        # Provide IP addresses in same VRF to satisfy L3 path checks
        core_if_ip = InterfaceAddress(
            interface_id=core_if.id, ip="10.0.0.1", prefix_len=30, vrf_id=1
        )
        edge_if_ip = InterfaceAddress(
            interface_id=edge_if.id, ip="10.0.0.2", prefix_len=30, vrf_id=1
        )
        link = Link(
            id="core1__edge1",
            a_interface_id=core_if.id,
            b_interface_id=edge_if.id,
            status=Status.UP,
        )
        # Provide default route on edge pointing to core interface IP via its interface
        default_route = Route(
            vrf_id=1,
            prefix="0.0.0.0/0",
            next_hop="10.0.0.1",
            interface_id=edge_if.id,
            admin_distance=1,
            metric=0,
        )
        # Neighbor entry to satisfy next-hop resolution (optional fast-path)
        neighbor = Neighbor(
            interface_id=edge_if.id, ip_address="10.0.0.1", mac_address="aa:bb:cc:dd:ee:ff"
        )
        s.add_all(
            [core, edge, core_if, edge_if, core_if_ip, edge_if_ip, link, default_route, neighbor]
        )
        s.commit()
        # Initial recompute to populate stores
        recompute_devices_status(s, baseline_status={}, topo_version=1)
        assert evaluate_device_status(edge) == Status.UP
        # Force link DOWN via admin override on link
        link.admin_override_status = Status.DOWN
        s.add(link)
        s.commit()
        # Re-run recompute
        recompute_devices_status(s, baseline_status={}, topo_version=2)
        # Edge router should now be DOWN due to no passable uplink
        edge_refreshed = s.get(Device, edge.id)
        if edge_refreshed is None:
            raise AssertionError("Edge device missing after recompute")
        assert evaluate_device_status(edge_refreshed) == Status.DOWN
        # Optional: ensure propagation store no longer marks edge reachable upstream
        # propagation_store only tracks reachability set membership; ensure edge not marked up
        assert propagation_store.is_up(edge.id) in (False, None)
