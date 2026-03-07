import pytest

from backend.db import get_session, init_db
from backend.events import get_event_history, reset_events
from backend.models import Device, DeviceType, Interface, Link, Status, Tariff
from backend.services.traffic_engine import TrafficEngine
from backend.tests.helpers_l3 import l3_pair


@pytest.fixture(autouse=True)
def _reset_db_events():
    init_db()
    reset_events()
    yield
    reset_events()


def _mk_dev(did: str, dtype: DeviceType, cap_mbps: int | None = None):
    with get_session() as s:
        d = Device(
            id=did,
            name=did,
            type=dtype,
            status=Status.UP,
            capacity=cap_mbps,
            provisioned=(dtype in {DeviceType.AON_CPE, DeviceType.ONT, DeviceType.BUSINESS_ONT}),
        )
        s.add(d)
        s.add(Interface(id=f"{did}-if0", device_id=did, name="if0"))
        s.commit()


def _mk_link(a_if: str, b_if: str):
    with get_session() as s:
        s.add(
            Link(id=f"{a_if}__{b_if}", a_interface_id=a_if, b_interface_id=b_if, status=Status.UP)
        )
        s.commit()


def test_device_congestion_detected_and_cleared(monkeypatch: pytest.MonkeyPatch):
    # Topology: leaf -> agg
    # Add backbone + core for strict L3 gating
    _mk_dev("bb", DeviceType.BACKBONE_GATEWAY, cap_mbps=1000)
    _mk_dev("core", DeviceType.CORE_ROUTER, cap_mbps=1000)
    _mk_dev("leaf", DeviceType.AON_CPE, cap_mbps=50)  # 50 Mbps device capacity
    _mk_dev("agg", DeviceType.AON_SWITCH, cap_mbps=1000)
    _mk_link("leaf-if0", "agg-if0")
    _mk_link("agg-if0", "core-if0")
    _mk_link("core-if0", "bb-if0")
    with l3_pair("core", "bb", "core-if0", "bb-if0"):
        pass

    # Tariff so leaf participates
    with get_session() as s:
        t = Tariff(name="Plan 100/10", max_down_mbps=100, max_up_mbps=10)
        s.add(t)
        s.commit()
        s.refresh(t)
        leaf = s.get(Device, "leaf")
        assert leaf
        leaf.tariff_id = t.id
        s.add(leaf)
        s.commit()

    # Force high utilization > capacity on device by monkeypatching generated values
    eng = TrafficEngine()

    def fake_run_tick_over():
        # minimal emulate of aggregates and metrics
        eng.tick_seq += 1
        eng._debug_last_aggregates = {"leaf": 200 * 1_000_000.0}  # 200 Mbps
        # Emit metric event first
        from backend import events as ev

        ev.publish(
            ev.Event(
                type="deviceMetricsUpdated",
                payload={
                    "devices": [{"id": "leaf", "bps": 200 * 1_000_000.0, "utilization": 4.0}],
                    "tick": eng.tick_seq,
                },
            )
        )
        # Run only congestion post-step
        # Trigger detection path using current device_changes shape
        # Simulate internal structures used in run_tick by calling a minimal shim
        pass

    # Instead of patching internals, directly run a real tick but patch capacities to be tiny
    with get_session() as s:
        leaf = s.get(Device, "leaf")
        assert leaf
        leaf.capacity = 1  # 1 Mbps capacity to ensure congestion on generated flows
        s.add(leaf)
        s.commit()

    # Make forwarding trivial (loopback hop)
    def _fake_resolve(flow):  # type: ignore[no-untyped-def]
        return {"hops": [{"current_device_id": "leaf"}], "hop_metadata": []}

    import backend.services.forwarding_service as fs

    monkeypatch.setattr(fs, "resolve_flow_path", _fake_resolve)

    # Run two ticks and observe detected then cleared when capacity increased
    eng.random_seed = 1
    eng.run_tick()
    evts = [e for e in get_event_history() if e.type.startswith("device.")]
    assert any(e.type == "device.congestion.detected" for e in evts)

    reset_events()
    with get_session() as s:
        leaf = s.get(Device, "leaf")
        assert leaf
        leaf.capacity = 10_000  # raise capacity to clear
        s.add(leaf)
        s.commit()

    eng.run_tick()
    evts2 = [e for e in get_event_history() if e.type.startswith("device.")]
    assert any(e.type == "device.congestion.cleared" for e in evts2)


def test_no_congestion_events_when_below_capacity(monkeypatch: pytest.MonkeyPatch):
    _mk_dev("bb2", DeviceType.BACKBONE_GATEWAY, cap_mbps=1000)
    _mk_dev("core2", DeviceType.CORE_ROUTER, cap_mbps=1000)
    _mk_dev("leaf2", DeviceType.AON_CPE, cap_mbps=10_000)
    _mk_dev("agg2", DeviceType.AON_SWITCH, cap_mbps=10_000)
    _mk_link("leaf2-if0", "agg2-if0")
    _mk_link("agg2-if0", "core2-if0")
    _mk_link("core2-if0", "bb2-if0")
    with l3_pair("core2", "bb2", "core2-if0", "bb2-if0"):
        pass

    with get_session() as s:
        t = Tariff(name="Plan 50/10", max_down_mbps=50, max_up_mbps=10)
        s.add(t)
        s.commit()
        s.refresh(t)
        d = s.get(Device, "leaf2")
        assert d
        d.tariff_id = t.id
        s.add(d)
        s.commit()

    def _fake_resolve(flow):  # type: ignore[no-untyped-def]
        return {"hops": [{"current_device_id": "leaf2"}], "hop_metadata": []}

    import backend.services.forwarding_service as fs

    monkeypatch.setattr(fs, "resolve_flow_path", _fake_resolve)

    reset_events()
    eng = TrafficEngine()
    eng.random_seed = 2
    eng.run_tick()

    evts = [e for e in get_event_history() if e.type.endswith("congestion.detected")]
    assert not evts
