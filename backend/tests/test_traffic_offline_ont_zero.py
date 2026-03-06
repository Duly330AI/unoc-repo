from __future__ import annotations

import pytest

from backend.db import get_session, init_db
from backend.events import get_event_history, reset_events
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status, Tariff
from backend.services.traffic_engine import TrafficEngine


@pytest.fixture(autouse=True)
def _reset_env_db_events(monkeypatch: pytest.MonkeyPatch):
    init_db()
    reset_events()
    yield
    reset_events()


def test_offline_ont_due_to_no_signal_generates_zero_and_no_event():
    """
    Create ONT with tariff but force optical NO_SIGNAL so effective status is DOWN.
    TrafficEngineV2 must skip generation for this device and not emit deviceMetricsUpdated for it.
    """
    init_db()
    with get_session() as s:
        # Minimal upstream path: ONT <-> OLT (so access link exists if needed)
        s.add(
            Device(id="olt1", name="olt1", type=DeviceType.OLT, status=Status.UP, provisioned=True)
        )
        s.add(Interface(id="olt1-if0", device_id="olt1", name="if0"))
        # ONT with NO_SIGNAL
        s.add(
            Device(
                id="ont1",
                name="ont1",
                type=DeviceType.ONT,
                status=Status.UP,
                provisioned=True,
                signal_status=Device.SignalStatus.NO_SIGNAL,
            )
        )
        s.add(Interface(id="ont1-if0", device_id="ont1", name="if0"))
        s.add(
            Link(
                id="l_ont1",
                a_interface_id="ont1-if0",
                b_interface_id="olt1-if0",
                status=Status.UP,
                kind=LinkType.FIBER,
            )
        )
        # Tariff assigned to ONT
        t = Tariff(name="Plan 100/20", max_down_mbps=100.0, max_up_mbps=20.0)
        s.add(t)
        s.commit()
        s.refresh(t)
        d = s.get(Device, "ont1")
        assert d is not None
        d.tariff_id = t.id
        s.add(d)
        s.commit()

    reset_events()
    eng = TrafficEngine()
    eng.random_seed = 99
    eng.run_tick()

    # ONT should not be in generated set (skipped entirely)
    assert "ont1" not in eng._debug_last_generated
    # Aggregates should not include ONT
    assert eng._debug_last_aggregates.get("ont1", 0.0) == 0.0

    # deviceMetricsUpdated may exist for other devices; ensure ont1 is not included
    dev_evts = [e for e in get_event_history() if e.type == "deviceMetricsUpdated"]
    if dev_evts:
        for evt in dev_evts:
            payload = getattr(evt, "payload", {}) or {}
            devices = payload.get("devices", [])
            assert all(it.get("id") != "ont1" for it in devices if isinstance(it, dict))
