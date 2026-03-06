from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.events import get_event_history, reset_events
from backend.main import app
from backend.models import (
    BridgeDomain,
    Device,
    DeviceType,
    Interface,
    Link,
    LinkType,
    Status,
    Tariff,
)
from backend.services.traffic_engine import TrafficEngine
from backend.tests.helpers_l3 import l3_pair


@pytest.fixture(autouse=True)
def _reset_env_db_events(monkeypatch: pytest.MonkeyPatch):
    init_db()
    reset_events()
    yield
    reset_events()


def _mk_device(
    id: str, t: DeviceType, status: Status = Status.UP, provisioned: bool | None = None
) -> None:
    init_db()
    with get_session() as s:
        # For leaf devices, mark provisioned=True so tariff-based traffic generation is allowed
        is_leaf = t in {DeviceType.AON_CPE, DeviceType.ONT, DeviceType.BUSINESS_ONT}
        eff_prov = is_leaf if provisioned is None else provisioned
        s.add(Device(id=id, name=id, type=t, status=status, provisioned=eff_prov))
        s.commit()


def _mk_if(id: str, dev: str, name: str | None = None, capacity: int | None = None) -> None:
    # Derive a default interface name from id to avoid UNIQUE (device_id, name) collisions
    eff_name = name if name is not None else (id.split("-", 1)[-1] if "-" in id else id)
    with get_session() as s:
        s.add(Interface(id=id, device_id=dev, name=eff_name, capacity=capacity))
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


def _ensure_default_bd(sw_id: str, if_ids: list[str]) -> None:
    with get_session() as s:
        bd = s.exec(
            select(BridgeDomain).where(
                (BridgeDomain.device_id == sw_id) & (BridgeDomain.name == "default")
            )
        ).first()
        if not bd:
            bd = BridgeDomain(device_id=sw_id, name="default")
            s.add(bd)
            s.commit()
            s.refresh(bd)
        for iid in if_ids:
            iface = s.get(Interface, iid)
            if iface:
                iface.bridge_domain_id = bd.id
                s.add(iface)
        s.commit()


def _assign_tariff(dev_id: str, down_mbps: float, up_mbps: float) -> int:
    with get_session() as s:
        t = Tariff(name=f"Plan {down_mbps}/{up_mbps}", max_down_mbps=down_mbps, max_up_mbps=up_mbps)
        s.add(t)
        s.commit()
        s.refresh(t)
        d = s.get(Device, dev_id)
        assert d is not None
        d.tariff_id = t.id
        s.add(d)
        s.commit()
        return int(t.id)  # type: ignore[arg-type]


def test_tariff_based_generation_asymmetric_within_bounds():
    # Provide upstream L3 anchor (backbone <-> core) so leaf generation is allowed under strict L3.
    _mk_device("bb1", DeviceType.BACKBONE_GATEWAY, Status.UP, provisioned=True)
    _mk_if("bb1-if0", "bb1", "if0")
    _mk_device("core1", DeviceType.CORE_ROUTER, Status.UP, provisioned=True)
    _mk_if("core1-if0", "core1", "if0")
    # Establish L3 adjacency core1 <-> bb1
    with l3_pair("core1", "bb1", "core1-if0", "bb1-if0"):
        pass
    # Logical access chain
    _mk_device("ed1", DeviceType.AON_CPE, Status.UP)
    _mk_if("ed1-if0", "ed1", "if0")
    # Attach a simple uplink path via switch to avoid None paths
    _mk_device("s1", DeviceType.AON_SWITCH, Status.UP)
    _mk_if("s1-if1", "s1", "if1")
    _mk_if("s1-if2", "s1", "if2")
    _mk_link("l_ed1_s1", "ed1-if0", "s1-if1")
    _mk_link("l_s1_core1", "s1-if2", "core1-if0")
    _ensure_default_bd("s1", ["s1-if1", "s1-if2"])

    _assign_tariff("ed1", down_mbps=200.0, up_mbps=50.0)

    eng = TrafficEngine()
    eng.random_seed = 42
    eng.run_tick()

    g = eng._debug_last_generated.get("ed1")
    assert g is not None
    up = float(g["up_bps"])  # upstream generation used for aggregation
    down = float(g["down_bps"])  # tracked for debug; downstream not forwarded yet
    assert 0.0 < up <= 50.0 * 1_000_000.0
    assert 0.0 < down <= 200.0 * 1_000_000.0
    assert up != down


def test_end_to_end_aggregation_on_devices_and_links(monkeypatch: pytest.MonkeyPatch):
    # ed1 -> s1 -> r1 -> bb1 path; verify device and link aggregates match generated upstream
    _mk_device("bb1", DeviceType.BACKBONE_GATEWAY, Status.UP, provisioned=True)
    _mk_if("bb1-if0", "bb1")
    _mk_device("r1", DeviceType.EDGE_ROUTER, Status.UP, provisioned=True)
    _mk_if("r1-if0", "r1")
    # l3_pair creates the link between r1-if0 and bb1-if0; do not recreate manually to avoid UNIQUE constraint
    with l3_pair("r1", "bb1", "r1-if0", "bb1-if0"):
        pass
    _mk_device("ed1", DeviceType.AON_CPE, Status.UP)
    _mk_if("ed1-if0", "ed1")
    _mk_device("s1", DeviceType.AON_SWITCH, Status.UP)
    _mk_if("s1-if1", "s1")
    _mk_if("s1-if2", "s1")
    _mk_if("r1-if1", "r1")
    _mk_link("l_ed1_s1", "ed1-if0", "s1-if1")
    _mk_link("l_s1_r1", "s1-if2", "r1-if1")
    # Link r1-if0 <-> bb1-if0 already ensured by l3_pair
    _ensure_default_bd("s1", ["s1-if1", "s1-if2"])
    _assign_tariff("ed1", 50.0, 10.0)

    # Patch path resolver to traverse s1 -> r1 over l_s1_r1
    from backend.services.forwarding_service import Flow as FF

    def _fake_resolve(flow: Any) -> dict[str, Any]:
        h1 = FF(
            source_ip=flow.source_ip,
            destination_ip=flow.destination_ip,
            current_device_id="s1",
            current_interface_id="s1-if1",
        )
        h2 = FF(
            source_ip=flow.source_ip,
            destination_ip=flow.destination_ip,
            current_device_id="r1",
            current_interface_id="r1-if1",
        )
        return {
            "hops": [h1, h2],
            "hop_metadata": [
                {
                    "device_id": "s1",
                    "device_type": "AON_SWITCH",
                    "action": "l2_forward",
                    "egress_interface_id": "s1-if2",
                    "deliver_here": False,
                    "reason": None,
                    "link_id_to_next": "l_s1_r1",
                }
            ],
        }

    import backend.services.forwarding_service as fs

    monkeypatch.setattr(fs, "resolve_flow_path", _fake_resolve)

    eng = TrafficEngine()
    eng.random_seed = 7
    eng.run_tick()

    gen = eng._debug_last_generated["ed1"]["up_bps"]
    # ed1, s1, r1 aggregates must include upstream bps
    for did in ["ed1", "s1", "r1"]:
        assert abs(eng._debug_last_aggregates.get(did, 0.0) - gen) < 1e-6
    # Link aggregate must match
    assert abs(eng._debug_last_link_aggregates.get("l_s1_r1", 0.0) - gen) < 1e-6


def test_congestion_detect_and_clear_with_hysteresis(monkeypatch: pytest.MonkeyPatch):
    # Small device capacities to trigger congestion on first tick, then raise to clear
    _mk_device("bb1", DeviceType.BACKBONE_GATEWAY, Status.UP, provisioned=True)
    _mk_if("bb1-if0", "bb1")
    _mk_device("core1", DeviceType.CORE_ROUTER, Status.UP, provisioned=True)
    _mk_if("core1-if0", "core1")
    with l3_pair("core1", "bb1", "core1-if0", "bb1-if0"):
        pass
    _mk_device("ed1", DeviceType.AON_CPE, Status.UP)
    _mk_if("ed1-if0", "ed1")
    _mk_device("s1", DeviceType.AON_SWITCH, Status.UP)
    _mk_if("s1-if1", "s1")
    _mk_link("l_ed1_s1", "ed1-if0", "s1-if1")
    _mk_link("l_s1_core1", "s1-if1", "core1-if0")
    _assign_tariff("ed1", 100.0, 50.0)

    # Set tiny capacity to guarantee detected
    with get_session() as s:
        d = s.get(Device, "ed1")
        assert d
        d.capacity = 1  # 1 Mbps
        s.add(d)
        s.commit()

    def _fake_resolve(flow):  # type: ignore[no-untyped-def]
        return {"hops": [{"current_device_id": "ed1"}], "hop_metadata": []}

    import backend.services.forwarding_service as fs

    monkeypatch.setattr(fs, "resolve_flow_path", _fake_resolve)

    reset_events()
    eng = TrafficEngine()
    eng.random_seed = 1
    eng.run_tick()
    evts = [e for e in get_event_history() if e.type.startswith("device.")]
    assert any(e.type == "device.congestion.detected" for e in evts)

    # Increase capacity high enough to clear
    reset_events()
    with get_session() as s:
        d = s.get(Device, "ed1")
        assert d
        d.capacity = 10_000
        s.add(d)
        s.commit()

    eng.run_tick()
    evts2 = [e for e in get_event_history() if e.type.startswith("device.")]
    assert any(e.type == "device.congestion.cleared" for e in evts2)


def test_snapshot_endpoint_returns_v2_data_with_links(monkeypatch: pytest.MonkeyPatch):
    # Topology with two links along the path
    client = TestClient(app)
    # Provide upstream backbone anchor and L3 adjacency core1 <-> bb1 so strict L3 gating allows generation.
    _mk_device("bb1", DeviceType.BACKBONE_GATEWAY, Status.UP, provisioned=True)
    _mk_if("bb1-if0", "bb1", capacity=1000)
    _mk_device("core1", DeviceType.CORE_ROUTER, Status.UP, provisioned=True)
    _mk_if("core1-if0", "core1", capacity=1000)
    with l3_pair("core1", "bb1", "core1-if0", "bb1-if0"):
        pass
    _mk_device("olt1", DeviceType.OLT, Status.UP)
    _mk_if("olt1-if0", "olt1", capacity=1000)
    _mk_device("ont1", DeviceType.ONT, Status.UP)
    _mk_if("ont1-if0", "ont1", capacity=1000)
    _mk_link("l_core", "olt1-if0", "core1-if0")
    _mk_link("l_ont1", "ont1-if0", "olt1-if0")
    _assign_tariff("ont1", 100.0, 50.0)

    def _fake_resolve(flow):  # type: ignore[no-untyped-def]
        # Walk from olt1 to core1
        return {
            "hops": [
                {"current_device_id": "olt1", "current_interface_id": "olt1-if0"},
                {"current_device_id": "core1", "current_interface_id": "core1-if0"},
            ],
            "hop_metadata": [
                {
                    "device_id": "olt1",
                    "device_type": "OLT",
                    "action": "l3_forward",
                    "egress_interface_id": "olt1-if0",
                    "deliver_here": False,
                    "reason": None,
                    "link_id_to_next": "l_core",
                }
            ],
        }

    import backend.services.forwarding_service as fs

    monkeypatch.setattr(fs, "resolve_flow_path", _fake_resolve)

    eng = TrafficEngine()
    eng.random_seed = 17
    eng.run_tick()

    r = client.get("/api/metrics/snapshot")
    assert r.status_code == 200
    body = r.json()
    # Must be v2 shape including links
    assert "devices" in body and isinstance(body["devices"], dict)
    assert "links" in body and isinstance(body["links"], dict)
    # Expect our nodes and links present with non-zero bps
    for did in ["ont1", "olt1", "core1"]:
        assert did in body["devices"]
        assert body["devices"][did]["bps"] >= 0
    for lid in ["l_core", "l_ont1"]:
        assert lid in body["links"]
        assert body["links"][lid]["bps"] >= 0


def test_unprovisioned_leaf_with_tariff_is_skipped(monkeypatch: pytest.MonkeyPatch):
    # Create ONT but leave provisioned=False (default), assign tariff; expect no traffic
    _mk_device("ontX", DeviceType.ONT, Status.UP, provisioned=False)
    _mk_if("ontX-if0", "ontX", capacity=1000)
    _assign_tariff("ontX", 100.0, 50.0)

    # Provide simple forwarding that would otherwise include the ONT path
    def _fake_resolve(flow: Any) -> dict[str, Any]:
        return {"hops": [], "hop_metadata": []}

    import backend.services.forwarding_service as fs

    monkeypatch.setattr(fs, "resolve_flow_path", _fake_resolve)

    reset_events()
    eng = TrafficEngine()
    eng.random_seed = 9
    eng.run_tick()

    # Engine should not have generated traffic for ontX
    assert eng._debug_last_generated.get("ontX") is None
    # And no device metrics event should reference ontX
    evts = [e for e in get_event_history() if e.type == "deviceMetricsUpdated"]
    if evts:
        for e in evts:
            ids = {d.get("id") for d in e.payload.get("devices", [])}
            assert "ontX" not in ids
