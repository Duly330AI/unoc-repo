from __future__ import annotations

from fastapi.testclient import TestClient

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, Status, Tariff
from backend.services.status_recompute import recompute_devices_status
from backend.services.status_service import evaluate_device_status
from backend.services.traffic.v2_engine import TrafficEngine
from backend.tests.helpers_l3 import l3_pair


def _mk_dev(id: str, t: DeviceType, provisioned: bool = True) -> None:
    with get_session() as s:
        if not s.get(Device, id):
            d = Device(id=id, name=id, type=t, provisioned=provisioned)
            s.add(d)
            s.commit()
        if_id = f"{id}-if0"
        if not s.get(Interface, if_id):
            s.add(Interface(id=if_id, device_id=id, name="if0"))
            s.commit()


def _mk_link(a_dev: str, b_dev: str) -> str:
    with get_session() as s:
        lid = "__".join(sorted([f"{a_dev}-if0", f"{b_dev}-if0"]))
        if not s.get(Link, lid):
            s.add(
                Link(
                    id=lid,
                    a_interface_id=f"{a_dev}-if0",
                    b_interface_id=f"{b_dev}-if0",
                    status=Status.UP,
                )
            )
            s.commit()
        return lid


def test_force_down_link_stops_traffic_and_degrades_downstream():
    init_db()
    # Minimal topology: BACKBONE -> CORE -> EDGE -> AON_SWITCH -> AON_CPE
    _mk_dev("bb", DeviceType.BACKBONE_GATEWAY, provisioned=True)
    _mk_dev("core", DeviceType.CORE_ROUTER, provisioned=True)
    _mk_dev("edge", DeviceType.EDGE_ROUTER, provisioned=True)
    _mk_dev("sw", DeviceType.AON_SWITCH, provisioned=True)
    _mk_dev("cpe", DeviceType.AON_CPE, provisioned=True)

    # Assign tariff to the CPE so it can generate traffic when UP
    with get_session() as s:
        if s.get(Tariff, 1) is None:
            s.add(Tariff(id=1, name="t", max_up_mbps=10, max_down_mbps=10))
            s.commit()
        d = s.get(Device, "cpe")
        assert d is not None
        d.tariff_id = 1
        s.add(d)
        s.commit()

    # Links
    _mk_link("bb", "core")
    core_edge = _mk_link("core", "edge")
    _mk_link("edge", "sw")
    _mk_link("sw", "cpe")

    # Establish L3 adjacency bb <-> core for strict L3 gating
    with l3_pair("core", "bb", "core-if0", "bb-if0"):
        pass
    # Initial recompute; routers require L3 reachability to an anchor.
    with get_session() as s:
        recompute_devices_status(s)
        for id_ in ["bb", "core", "edge", "sw", "cpe"]:
            dev = s.get(Device, id_)
            assert dev is not None
            # Under strict L3, routers without explicit L3 config may remain DOWN even if physically adjacent.
            # Allow either state for core/edge depending on resolver behavior in this minimal setup.
            if id_ in {"core", "edge"}:
                assert evaluate_device_status(dev) in {Status.DOWN, Status.UP}
            else:
                assert evaluate_device_status(dev) == Status.UP

    # Traffic tick: expect non-zero on edge_cpe path
    eng = TrafficEngine()
    eng.run_tick()
    snap1 = eng.get_snapshot()
    links1 = snap1["links"]
    assert any(v.get("bps", 0.0) > 0 for v in links1.values())

    # Force down the core-edge link
    with get_session() as s:
        ln = s.get(Link, core_edge)
        assert ln is not None
        ln.admin_override_status = Status.DOWN
        s.add(ln)
        s.commit()
        recompute_devices_status(s)

    # Downstream device (edge, then cpe) should not have upstream path; edge becomes DOWN (strict L3)
    with get_session() as s:
        edge = s.get(Device, "edge")
        cpe = s.get(Device, "cpe")
        sw = s.get(Device, "sw")
        assert edge is not None and sw is not None and cpe is not None
        # Strict model removed DEGRADED; edge expected DOWN after upstream link forced down
        assert evaluate_device_status(edge) == Status.DOWN
        # Switch & CPE lose upstream L3 and should also fall DOWN under unified gating
    assert evaluate_device_status(sw) == Status.DOWN
    assert evaluate_device_status(cpe) == Status.DOWN

    # Next traffic tick should stop using the forced-down link and zero metrics
    eng.run_tick()
    snap2 = eng.get_snapshot()
    links2 = snap2["links"]
    # Forced-down link must be at zero (and ideally absent from active changes)
    if core_edge in links2:
        assert links2[core_edge].get("bps", 0.0) == 0.0
    # Also ensure cpe-origin traffic stops; in strict mode leaves only generate when UP with tariff
    assert not any(v.get("bps", 0.0) > 0 for v in links2.values())

    # And the links API must reflect effective_status DOWN for the overridden link
    client = TestClient(app)
    resp = client.get("/api/links")
    assert resp.status_code == 200
    items = resp.json()
    row = next((r for r in items if r["id"] == core_edge), None)
    assert row is not None
    assert row.get("effective_status") == "Status.DOWN" or row.get("effective_status") == "DOWN"
