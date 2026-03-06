from __future__ import annotations

import pytest

from backend.db import get_session
from backend.models import AdminStatus, Device, DeviceType, Interface, Link
from backend.services.dependency_resolver import has_l3_reachability_to_anchor
from backend.tests.helpers_l3 import (
    add_default_route,
    add_interface_address,
    add_neighbor,
    assign_device_vrf,
    ensure_vrf,
    l3_pair,
)


@pytest.fixture(autouse=True)
def _strict_mode_env(monkeypatch):
    # Ensure strict L3 gating behavior consistent with the rest of the suite
    monkeypatch.setenv("UNOC_L3_STATUS_STRICT", "1")
    yield


def test_helpers_vrf_idempotence_and_l3_pair_happy_path():
    # ensure_vrf returns stable id across calls; l3_pair configures a simple edge→gw reachability
    vrf_id_1 = ensure_vrf("test-mgmt")
    vrf_id_2 = ensure_vrf("test-mgmt")
    assert vrf_id_1 == vrf_id_2

    with get_session() as s:
        # Create devices (edge router and a backbone anchor)
        edge = Device(id="edge-h1", name="edge-h1", type=DeviceType.EDGE_ROUTER)
        gw = Device(id="gw-h1", name="gw-h1", type=DeviceType.BACKBONE_GATEWAY)
        s.add(edge)
        s.add(gw)
        s.commit()

    # Assign VRF to both devices
    assign_device_vrf("edge-h1", vrf_id_1)
    assign_device_vrf("gw-h1", vrf_id_1)

    # Build L3 adjacency and default route using helper (auto-neighbor + link + admin-up)
    with l3_pair(
        "edge-h1",
        "gw-h1",
        "edge-h1-if0",
        "gw-h1-if0",
        vrf_name="test-mgmt",
        ptp_cidr="192.0.2.0/31",
    ) as (_vrf_id, edge_ip, gw_ip):
        assert _vrf_id == vrf_id_1
        with get_session() as s:
            # Verify reachability resolves to the anchor
            edge_dev = s.get(Device, "edge-h1")
            assert edge_dev is not None
            assert has_l3_reachability_to_anchor(s, edge_dev) is True


def test_loop_guard_prevents_infinite_recursion_and_returns_false():
    # Create a routing loop between two routers (A <-> B) with default routes pointing at each other
    vrf_id = ensure_vrf("loop-test")
    with get_session() as s:
        a = Device(id="rA", name="rA", type=DeviceType.EDGE_ROUTER)
        b = Device(id="rB", name="rB", type=DeviceType.CORE_ROUTER)
        s.add(a)
        s.add(b)
        s.commit()

    assign_device_vrf("rA", vrf_id)
    assign_device_vrf("rB", vrf_id)

    # Interfaces and link
    with get_session() as s:
        ia = Interface(id="rA-u", device_id="rA", name="u", admin_status=AdminStatus.UP)
        ib = Interface(id="rB-u", device_id="rB", name="u", admin_status=AdminStatus.UP)
        s.add(ia)
        s.add(ib)
        s.add(Link(id="lnk-loop", a_interface_id="rA-u", b_interface_id="rB-u"))
        s.commit()

    # Addresses on a /31 point-to-point
    add_interface_address("rA-u", "198.51.100.1", 31, vrf_id)
    add_interface_address("rB-u", "198.51.100.0", 31, vrf_id)

    # Neighbors so next-hops resolve at L2
    add_neighbor("rA-u", "198.51.100.0", "00:00:00:00:00:0b")
    add_neighbor("rB-u", "198.51.100.1", "00:00:00:00:00:0a")

    # Default routes forming a loop (no backbone anchor present)
    add_default_route(vrf_id, next_hop="198.51.100.0", interface_id="rA-u")
    add_default_route(vrf_id, next_hop="198.51.100.1", interface_id="rB-u")

    with get_session() as s:
        a_dev = s.get(Device, "rA")
        b_dev = s.get(Device, "rB")
        assert a_dev and b_dev
        # Loop guard should prevent recursion and return False (no anchor)
        assert has_l3_reachability_to_anchor(s, a_dev) is False
        assert has_l3_reachability_to_anchor(s, b_dev) is False


def test_direct_neighbor_fallback_without_neighbor_entry():
    # Validate fallback path: no explicit Neighbor entry, but next_hop matches peer interface IP
    vrf_id = ensure_vrf("fallback-test")
    with get_session() as s:
        edge = Device(id="edge-fb", name="edge-fb", type=DeviceType.EDGE_ROUTER)
        gw = Device(id="gw-fb", name="gw-fb", type=DeviceType.BACKBONE_GATEWAY)
        s.add_all([edge, gw])
        s.commit()

    assign_device_vrf("edge-fb", vrf_id)
    assign_device_vrf("gw-fb", vrf_id)

    # Interfaces and link (UP)
    with get_session() as s:
        ie = Interface(id="edge-fb-u", device_id="edge-fb", name="u", admin_status=AdminStatus.UP)
        ig = Interface(id="gw-fb-u", device_id="gw-fb", name="u", admin_status=AdminStatus.UP)
        s.add_all([ie, ig])
        s.add(Link(id="lnk-fb", a_interface_id="edge-fb-u", b_interface_id="gw-fb-u"))
        s.commit()

    # Assign addresses to each side of the link (/31), but DO NOT create Neighbor entries
    add_interface_address("edge-fb-u", "203.0.113.1", 31, vrf_id)
    add_interface_address("gw-fb-u", "203.0.113.0", 31, vrf_id)

    # Default route on edge pointing to gateway IP (203.0.113.0) without neighbor
    add_default_route(vrf_id, next_hop="203.0.113.0", interface_id="edge-fb-u")

    # Fallback should detect directly-connected peer IP via the link and still succeed
    with get_session() as s:
        edge_dev = s.get(Device, "edge-fb")
        assert edge_dev is not None
        assert has_l3_reachability_to_anchor(s, edge_dev) is True
