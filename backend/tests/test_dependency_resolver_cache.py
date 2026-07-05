from __future__ import annotations

from sqlmodel import Session

from backend.db import get_session
from backend.models import Device, DeviceType, Link, Status
from backend.services.dependency_resolver import has_upstream_l3_or_anchor
from backend.services.event_store_runtime import projection_write_context
from backend.services.pathfinding import PATHFINDING_STORE


def _mk_device(s: Session, did: str, dtype: DeviceType, provisioned: bool = True) -> Device:
    d = Device(id=did, name=did, type=dtype, status=Status.UP, provisioned=provisioned)
    s.add(d)
    return d


def _mk_link(s: Session, a_dev: str, b_dev: str) -> Link:
    a_if = f"{a_dev}-if0"
    b_if = f"{b_dev}-if0"
    # Create endpoint interfaces if missing
    from backend.models import Interface

    if s.get(Interface, a_if) is None:
        s.add(Interface(id=a_if, device_id=a_dev, name="if0"))
    if s.get(Interface, b_if) is None:
        s.add(Interface(id=b_if, device_id=b_dev, name="if0"))
    ln = Link(id=f"{a_dev}__{b_dev}", a_interface_id=a_if, b_interface_id=b_if, status=Status.UP)
    s.add(ln)
    return ln


def test_upstream_cache_hit_and_invalidation():
    # Build a tiny topology: edge -> core (both provisioned)
    with projection_write_context(), get_session() as s:
        core = _mk_device(s, "core1", DeviceType.BACKBONE_GATEWAY)
        edge = _mk_device(s, "edge1", DeviceType.EDGE_ROUTER)
        _mk_link(s, edge.id, core.id)
        # Minimal L3 setup: shared VRF, addresses, neighbor, and default route from edge to core
        from backend.models import VRF, InterfaceAddress, Neighbor, Route

        vrf = VRF(name="v1")
        s.add(vrf)
        s.flush()
        assert vrf.id is not None
        core.vrf_id = vrf.id
        edge.vrf_id = vrf.id
        # Assign IPs on the peer interfaces
        s.add(
            InterfaceAddress(
                interface_id=f"{core.id}-if0", ip="10.0.0.1", prefix_len=30, vrf_id=vrf.id
            )
        )
        s.add(
            InterfaceAddress(
                interface_id=f"{edge.id}-if0", ip="10.0.0.2", prefix_len=30, vrf_id=vrf.id
            )
        )
        # Neighbor on edge towards core IP
        s.add(
            Neighbor(
                interface_id=f"{edge.id}-if0",
                ip_address="10.0.0.1",
                mac_address="00:11:22:33:44:55",
            )
        )
        # Default route on edge via its if0 to next hop = core IP
        s.add(
            Route(
                id=1,
                vrf_id=vrf.id,
                prefix="0.0.0.0/0",
                interface_id=f"{edge.id}-if0",
                next_hop="10.0.0.1",
                admin_distance=1,
                metric=1,
            )
        )
        s.commit()

        # First call populates cache
        r1 = has_upstream_l3_or_anchor(s, edge)
        assert r1.ok and r1.anchor == core.id

        # Second call should hit cache; we can't directly inspect internal cache,
        # but repeated result equality on identical inputs/topo_version is expected.
        r2 = has_upstream_l3_or_anchor(s, edge)
        assert r2.ok and r2.anchor == core.id

        # Now change topology version to invalidate cache
        PATHFINDING_STORE.bump_version()

        # After invalidation, compute again; still True but recomputed under new version
        r3 = has_upstream_l3_or_anchor(s, edge)
        assert r3.ok and r3.anchor == core.id


def test_logical_graph_snapshot_reused_until_topology_version_changes(monkeypatch):
    with projection_write_context(), get_session() as s:
        core = _mk_device(s, "graph_core", DeviceType.BACKBONE_GATEWAY)
        edge = _mk_device(s, "graph_edge", DeviceType.EDGE_ROUTER)
        cpe1 = _mk_device(s, "graph_cpe1", DeviceType.AON_CPE)
        cpe2 = _mk_device(s, "graph_cpe2", DeviceType.AON_CPE)
        _mk_link(s, edge.id, core.id)
        _mk_link(s, cpe1.id, edge.id)
        _mk_link(s, cpe2.id, edge.id)

        from backend.models import VRF, InterfaceAddress, Neighbor, Route

        vrf = VRF(name="graph_vrf")
        s.add(vrf)
        s.flush()
        assert vrf.id is not None
        core.vrf_id = vrf.id
        edge.vrf_id = vrf.id
        s.add(
            InterfaceAddress(
                interface_id=f"{core.id}-if0", ip="10.10.0.1", prefix_len=30, vrf_id=vrf.id
            )
        )
        s.add(
            InterfaceAddress(
                interface_id=f"{edge.id}-if0", ip="10.10.0.2", prefix_len=30, vrf_id=vrf.id
            )
        )
        s.add(
            Neighbor(
                interface_id=f"{edge.id}-if0",
                ip_address="10.10.0.1",
                mac_address="00:11:22:33:44:66",
            )
        )
        s.add(
            Route(
                id=11,
                vrf_id=vrf.id,
                prefix="0.0.0.0/0",
                interface_id=f"{edge.id}-if0",
                next_hop="10.10.0.1",
                admin_distance=1,
                metric=1,
            )
        )
        s.commit()

        PATHFINDING_STORE.bump_version()
        calls: list[int] = []
        original_get_logical_graph = PATHFINDING_STORE.get_logical_graph

        def counted_get_logical_graph(devices, links, relaxed):
            calls.append(PATHFINDING_STORE.version())
            return original_get_logical_graph(devices, links, relaxed)

        monkeypatch.setattr(PATHFINDING_STORE, "get_logical_graph", counted_get_logical_graph)

        r1 = has_upstream_l3_or_anchor(s, cpe1)
        r2 = has_upstream_l3_or_anchor(s, cpe2)
        assert r1.ok and r2.ok
        assert len(calls) == 1

        PATHFINDING_STORE.bump_version()
        r3 = has_upstream_l3_or_anchor(s, cpe1)
        assert r3.ok
        assert len(calls) == 2
