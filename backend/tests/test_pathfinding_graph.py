"""Tests for pathfinding graph layer (TASK-034A).

Focus: membership + synthetic relaxed edges + version bump invalidation.
"""

from backend.services.pathfinding import (
    PATHFINDING_STORE,
    DeviceRecord,
    LinkRecord,
    build_logical_graph,
    build_optical_graph,
)


def sample_devices():
    return [
        DeviceRecord(id="core1", type="CORE_ROUTER"),
        DeviceRecord(id="edge1", type="EDGE_ROUTER"),
        DeviceRecord(id="olt1", type="OLT"),
        DeviceRecord(id="aon1", type="AON_SWITCH"),
        DeviceRecord(id="ont1", type="ONT"),
        DeviceRecord(id="split1", type="SPLITTER"),  # passive optical inline
    ]


def sample_links():
    return [
        LinkRecord(id="l1", a_device_id="olt1", b_device_id="split1", kind="optical_segment"),
        LinkRecord(
            id="l2",
            a_device_id="split1",
            b_device_id="ont1",
            kind="optical_termination",
        ),
        LinkRecord(id="l3", a_device_id="core1", b_device_id="edge1", kind="routed_p2p"),
        LinkRecord(id="l4", a_device_id="edge1", b_device_id="olt1", kind="access_edge"),
    ]


def test_optical_graph_nodes_and_edges():
    g = build_optical_graph(sample_devices(), sample_links())
    # Node membership
    assert set(g.nodes()) == {"olt1", "split1", "ont1"}  # only optical relevant nodes
    # Edge membership
    assert {tuple(sorted(e)) for e in g.edges()} == {
        ("olt1", "split1"),
        ("ont1", "split1"),
    }


def test_logical_graph_relaxed_edges():
    # Without relaxed
    g1 = build_logical_graph(sample_devices(), sample_links(), relaxed=False)
    assert set(g1.nodes()) >= {"core1", "edge1", "olt1", "aon1", "ont1"}
    # Collapsed optical edge now added even when relaxed=False (ONT -> OLT)
    ont_edges = [e for e in g1.edges(data=True) if set(e[:2]) == {"ont1", "olt1"}]
    assert ont_edges and ont_edges[0][2].get("synthetic") is True

    # With relaxed -> OLT should connect to core1 via synthetic edge (since no direct path)
    g2 = build_logical_graph(sample_devices(), sample_links(), relaxed=True)
    synthetic_edges = [e for e in g2.edges(data=True) if e[2].get("synthetic")]
    # In relaxed mode we should still have the collapsed optical edge plus relaxed OLT/Core edge
    assert any({e[0], e[1]} == {"olt1", "core1"} for e in synthetic_edges)
    assert any({e[0], e[1]} == {"ont1", "olt1"} for e in synthetic_edges)


def test_store_version_and_invalidation():
    devices = sample_devices()
    links = sample_links()
    v0, g0 = PATHFINDING_STORE.get_optical_graph(devices, links)
    # bump version & ensure graph object instance invalidated
    PATHFINDING_STORE.bump_version()
    v1, g1 = PATHFINDING_STORE.get_optical_graph(devices, links)
    assert v1 == v0 + 1
    assert g0 is not g1
