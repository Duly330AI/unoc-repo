from __future__ import annotations

from pytest import approx

from backend.db import get_session, reset_db
from backend.events import get_event_history, reset_events
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status
from backend.services.metrics_service import METRICS


def test_link_metrics_branching_topology_aggregation_and_emission():
    # Fresh DB and event bus
    reset_db()
    reset_events()
    # Reset metrics state for isolation
    METRICS._last.clear()
    METRICS._last_links.clear()

    # Topology:
    #   ont1 --(l_ont1)--> olt --(l_core)--> core
    #   ont2 --(l_ont2)--> /
    # Both leaves push 100 Mbps each; core link should see 200 Mbps aggregate.
    with get_session() as s:
        s.add(Device(id="core", name="core", type=DeviceType.CORE_ROUTER, status=Status.UP))
        s.add(Device(id="olt", name="olt", type=DeviceType.OLT, status=Status.UP))
        s.add(Device(id="ont1", name="ont1", type=DeviceType.ONT, status=Status.UP))
        s.add(Device(id="ont2", name="ont2", type=DeviceType.ONT, status=Status.UP))

        # Interfaces with capacities (Mbps)
        s.add(Interface(id="core-if0", device_id="core", name="if0", capacity=1000))
        s.add(Interface(id="olt-if0", device_id="olt", name="if0", capacity=1000))
        s.add(Interface(id="ont1-if0", device_id="ont1", name="if0", capacity=1000))
        s.add(Interface(id="ont2-if0", device_id="ont2", name="if0", capacity=1000))

        # Links
        s.add(
            Link(
                id="l_core",
                a_interface_id="olt-if0",
                b_interface_id="core-if0",
                kind=LinkType.FIBER,
                status=Status.UP,
            )
        )
        s.add(
            Link(
                id="l_ont1",
                a_interface_id="ont1-if0",
                b_interface_id="olt-if0",
                kind=LinkType.FIBER,
                status=Status.UP,
            )
        )
        s.add(
            Link(
                id="l_ont2",
                a_interface_id="ont2-if0",
                b_interface_id="olt-if0",
                kind=LinkType.FIBER,
                status=Status.UP,
            )
        )
        s.commit()

    # 100 Mbps each leaf (values in bps)
    METRICS.process_tick([("ont1", 100 * 1_000_000.0), ("ont2", 100 * 1_000_000.0)], tick=1)

    # Find linkMetricsUpdated event
    evts = [e for e in get_event_history() if e.type == "linkMetricsUpdated"]
    assert evts, "Expected linkMetricsUpdated event"
    payload = evts[-1].payload
    links = payload.get("links") or []
    m: dict[str, dict] = {d["id"]: d for d in links}

    # Expect three links reported
    assert set(m.keys()) == {"l_core", "l_ont1", "l_ont2"}

    # Core link carries sum (200 Mbps)
    assert m["l_core"]["bps"] == approx(200 * 1_000_000.0)
    assert m["l_core"]["utilization"] == approx(0.2, rel=1e-6)

    # Leaf links carry their respective 100 Mbps
    assert m["l_ont1"]["bps"] == approx(100 * 1_000_000.0)
    assert m["l_ont1"]["utilization"] == approx(0.1, rel=1e-6)
    assert m["l_ont2"]["bps"] == approx(100 * 1_000_000.0)
    assert m["l_ont2"]["utilization"] == approx(0.1, rel=1e-6)
