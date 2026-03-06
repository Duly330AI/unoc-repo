from __future__ import annotations

import math

from backend.db import get_session, init_db
from backend.events import get_event_history, reset_events
from backend.models import Device, DeviceType, Interface, Link, LinkType, PortRole, Status, Tariff
from backend.services.pathfinding import PATHFINDING_STORE
from backend.services.traffic.v2_engine import TrafficEngine
from backend.tests.helpers_l3 import l3_pair


def _mk_device(
    id: str, t: DeviceType, status: Status = Status.UP, provisioned: bool = False
) -> None:
    with get_session() as s:
        s.add(Device(id=id, name=id, type=t, status=status, provisioned=provisioned))
        s.commit()


def _mk_if(id: str, dev: str, name: str | None = None, port_role: PortRole | None = None) -> None:
    eff_name = name if name is not None else (id.split("-", 1)[-1] if "-" in id else id)
    with get_session() as s:
        s.add(Interface(id=id, device_id=dev, name=eff_name, port_role=port_role))
        s.commit()


def _mk_link(id: str, a_if: str, b_if: str, status: Status = Status.UP) -> None:
    with get_session() as s:
        s.add(
            Link(
                id=id,
                a_interface_id=a_if,
                b_interface_id=b_if,
                status=status,
                kind=LinkType.FIBER,
            )
        )
        s.commit()


def _assign_tariff(dev_id: str, down_mbps: float, up_mbps: float) -> None:
    with get_session() as s:
        t = Tariff(name=f"Plan {down_mbps}/{up_mbps}", max_down_mbps=down_mbps, max_up_mbps=up_mbps)
        s.add(t)
        s.commit()
        s.refresh(t)
        d = s.get(Device, dev_id)
        assert d is not None
        d.tariff_id = t.id
        d.provisioned = True
        s.add(d)
        s.commit()


def test_segment_congestion_lifecycle(monkeypatch):
    # Fresh DB/events per test
    init_db()
    reset_events()

    # Build minimal OLT -> ODF -> ONT with an upstream CORE anchor and backbone L3 chain
    _mk_device("bb1", DeviceType.BACKBONE_GATEWAY, Status.UP, provisioned=True)
    _mk_if("bb1-if0", "bb1", name="if0")
    _mk_device("core1", DeviceType.CORE_ROUTER, Status.UP, provisioned=True)
    _mk_if("core1-if0", "core1", name="if0")
    with l3_pair("core1", "bb1", "core1-if0", "bb1-if0"):
        pass

    _mk_device("olt1", DeviceType.OLT, Status.UP, provisioned=True)
    _mk_if("olt1-if0", "olt1", name="if0")
    # Add a PON interface and use it for OLT<->ODF link (required under Phase 1 rules)
    _mk_if("olt1-pon0", "olt1", name="pon0", port_role=PortRole.PON)

    _mk_device("odf1", DeviceType.ODF, Status.UP)
    _mk_if("odf1-if0", "odf1", name="if0")

    _mk_device("ont1", DeviceType.ONT, Status.UP, provisioned=True)
    _mk_if("ont1-if0", "ont1", name="if0")

    # Links: core<->olt (uplink), olt(pon0)<->odf, odf<->ont
    _mk_link("core1__olt1" if "core1" < "olt1" else "olt1__core1", "core1-if0", "olt1-if0")
    _mk_link("odf1__olt1" if "odf1" < "olt1" else "olt1__odf1", "olt1-pon0", "odf1-if0")
    _mk_link("odf1__ont1" if "odf1" < "ont1" else "ont1__odf1", "ont1-if0", "odf1-if0")
    # Invalidate optical path cache after direct DB writes so resolve_optical_path rebuilds
    PATHFINDING_STORE.bump_version()

    # Assign a very high tariff so demand can exceed GPON capacity (2.5G/1.25G)
    _assign_tariff("ont1", down_mbps=10000.0, up_mbps=10000.0)

    # Force deterministic generation: tick 0 -> 1.0, tick >=1 -> 0.0
    import backend.services.traffic.v2_engine as v2e

    def _fixed_rand(seed: int, tick: int, key: str) -> float:  # noqa: ARG001
        return 1.0 if tick == 0 else 0.0

    monkeypatch.setattr(v2e, "deterministic_rand01", _fixed_rand)

    eng = TrafficEngine()
    eng.random_seed = 123

    # Tick 0: expect detected congestion on the single segment
    eng.run_tick()
    snap0 = eng.get_snapshot()
    segments0 = snap0.get("segments") or {}
    assert len(segments0) == 1
    seg_id, seg0 = next(iter(segments0.items()))
    assert seg0["subscribers_count"] == 1
    # Capacity defaults (GPON 2.5G/1.25G) unless PortProfile overrides
    assert seg0["capacity_down_bps"] >= 2.0e9
    assert seg0["capacity_up_bps"] >= 1.0e9
    # Demand should exceed capacity -> congested True
    assert seg0["demand_up_bps"] >= seg0["capacity_up_bps"]
    assert seg0["congested"] is True
    # Event emitted
    hist = get_event_history()
    assert any(
        e.type == "segment.congestion.detected" and e.payload.get("id") == seg_id for e in hist
    )

    # Tick 1: drop demand to 0 -> hysteresis clear -> cleared event
    reset_events()
    eng.run_tick()
    snap1 = eng.get_snapshot()
    seg1 = (snap1.get("segments") or {}).get(seg_id)
    assert seg1 is not None
    assert math.isclose(float(seg1["demand_up_bps"]), 0.0, rel_tol=0.0, abs_tol=1e-6)
    assert seg1["congested"] is False
    hist2 = get_event_history()
    assert any(
        e.type == "segment.congestion.cleared" and e.payload.get("id") == seg_id for e in hist2
    )
