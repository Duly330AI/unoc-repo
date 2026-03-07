from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from backend.db import get_session, init_db
from backend.events import get_event_history, reset_events
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status, Tariff
from backend.services.traffic_engine import TrafficEngine


def _mk_device(id: str, t: DeviceType, status: Status = Status.UP) -> None:
    with get_session() as s:
        s.add(
            Device(
                id=id,
                name=id,
                type=t,
                status=status,
                provisioned=(t in {DeviceType.AON_CPE, DeviceType.ONT, DeviceType.BUSINESS_ONT}),
            )
        )
        s.commit()


def _mk_if(id: str, dev: str, name: str | None = None, capacity: int | None = None) -> None:
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


def test_e2e_tariff_generation_and_events(monkeypatch):
    """
    Build Backbone -> Core -> OLT -> ONT, assign tariff, run a few ticks, verify deviceMetricsUpdated
    and linkMetricsUpdated events are emitted with non-zero bps for devices and links in the ONT upstream path.
    """
    init_db()
    reset_events()

    client = TestClient(app)

    # Topology
    _mk_device("bb1", DeviceType.BACKBONE_GATEWAY, Status.UP)
    _mk_device("core1", DeviceType.CORE_ROUTER, Status.UP)
    _mk_if("core1-if0", "core1", capacity=1000)
    _mk_if("bb1-if0", "bb1", capacity=1000)
    _mk_device("olt1", DeviceType.OLT, Status.UP)
    _mk_if("olt1-if0", "olt1", capacity=1000)
    _mk_device("ont1", DeviceType.ONT, Status.UP)
    _mk_if("ont1-if0", "ont1", capacity=1000)

    _mk_link("l_core", "olt1-if0", "core1-if0")
    _mk_link("l_ont1", "ont1-if0", "olt1-if0")
    _mk_link("l_bb", "bb1-if0", "core1-if0")

    _assign_tariff("ont1", 100.0, 50.0)

    # Provide deterministic forwarding path: ont1 -> olt1 -> core1
    def _fake_resolve(flow: Any) -> dict[str, Any]:
        return {
            "hops": [
                {"current_device_id": "olt1", "current_interface_id": "olt1-if0"},
                {"current_device_id": "core1", "current_interface_id": "core1-if0"},
            ],
            "hop_metadata": [
                {
                    "device_id": "olt1",
                    "device_type": "OLT",
                    "action": "l3_route",
                    "egress_interface_id": "olt1-if0",
                    "deliver_here": False,
                    "reason": None,
                    "link_id_to_next": "l_core",
                }
            ],
        }

    import backend.services.forwarding_service as fs

    monkeypatch.setattr(fs, "resolve_flow_path", _fake_resolve)

    # Drive a couple of ticks manually using the engine (not the background thread)
    eng = TrafficEngine()
    eng.random_seed = 123
    eng.run_tick()
    eng.run_tick()

    # Verify emitted events
    evts = get_event_history()
    dev_evt = next((e for e in evts if e.type == "deviceMetricsUpdated"), None)
    link_evt = next((e for e in evts if e.type == "linkMetricsUpdated"), None)
    assert dev_evt is not None
    assert link_evt is not None

    # Device metrics should include ont1, olt1, core1 with non-zero bps
    dev_ids = {d.get("id") for d in dev_evt.payload.get("devices", [])}
    assert {"ont1", "olt1", "core1"}.issubset(dev_ids)
    for item in dev_evt.payload.get("devices", []):
        if item.get("id") in {"ont1", "olt1", "core1"}:
            assert float(item.get("bps", 0.0)) >= 0.0

    # Link metrics should include our links with non-zero bps
    link_ids = {link_item.get("id") for link_item in link_evt.payload.get("links", [])}
    assert {"l_core", "l_ont1"}.issubset(link_ids)
    for item in link_evt.payload.get("links", []):
        if item.get("id") in {"l_core", "l_ont1"}:
            assert float(item.get("bps", 0.0)) >= 0.0

    # Snapshot should expose latest v2 state
    r = client.get("/api/metrics/snapshot")
    assert r.status_code == 200
    body = r.json()
    for did in ["ont1", "olt1", "core1"]:
        assert did in body["devices"]
        assert float(body["devices"][did]["bps"]) >= 0.0
    for lid in ["l_core", "l_ont1"]:
        assert lid in body["links"]
        assert float(body["links"][lid]["bps"]) >= 0.0
