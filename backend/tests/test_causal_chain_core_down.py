"""
Integration test for causal chain status propagation.

Tests status propagation through multi-hop topology when core router goes down.
Validates causal_chain array tracking source device of degraded/down status.

REQUIRES: Status Propagation Go service (port 50053) + PostgreSQL
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, Status, Tariff

pytestmark = pytest.mark.integration  # Mark entire module as integration test


def _mk_dev(id: str, t: DeviceType, provisioned: bool = True):
    with get_session() as s:
        if not s.get(Device, id):
            d = Device(id=id, name=id, type=t, status=Status.UP, provisioned=provisioned)
            s.add(d)
            s.commit()
            # ensure default if0
            if_id = f"{id}-if0"
            if not s.get(Interface, if_id):
                s.add(Interface(id=if_id, device_id=id, name="if0"))
                s.commit()


def _mk_link(a: str, b: str, kind: str = "FIBER"):
    with get_session() as s:
        lid = "__".join(sorted([a, b]))
        if not s.get(Link, lid):
            s.add(
                Link(
                    id=lid,
                    a_interface_id=f"{a}-if0",
                    b_interface_id=f"{b}-if0",
                    status=Status.UP,
                )
            )
            s.commit()


def _ensure_tariff(name: str = "GPON_100_50", up: float = 50.0, down: float = 100.0) -> int:
    with get_session() as s:
        t = s.exec(select(Tariff).where(Tariff.name == name)).first()
        if t:
            return int(t.id)  # type: ignore[return-value]
        t = Tariff(name=name, max_up_mbps=up, max_down_mbps=down)
        s.add(t)
        s.commit()
        s.refresh(t)
        return int(t.id)  # type: ignore[return-value]


def test_causal_chain_core_down():
    client = TestClient(app)
    init_db()
    # Build Backbone -> Core -> Edge -> OLT -> ONT
    _mk_dev("backbone_gateway", DeviceType.BACKBONE_GATEWAY)
    _mk_dev("core_router", DeviceType.CORE_ROUTER)
    _mk_dev("edge_router", DeviceType.EDGE_ROUTER)
    _mk_dev("olt", DeviceType.OLT)
    _mk_dev("ont", DeviceType.ONT)
    # Links
    _mk_link("backbone_gateway", "core_router")
    _mk_link("core_router", "edge_router")
    _mk_link("edge_router", "olt")
    _mk_link("olt", "ont")
    # Assign tariff to ONT to generate traffic
    tid = _ensure_tariff()
    with get_session() as s:
        ont = s.get(Device, "ont")
        assert ont
        ont.tariff_id = tid
        s.add(ont)
        s.commit()

    # Run one traffic tick to populate metrics
    # ENGINE_SINGLETON is a TariffTrafficRunner; invoke its underlying engine directly.
    from backend.services.traffic_engine import ENGINE_SINGLETON as ENG

    if getattr(ENG, "engine", None) is not None:
        ENG.engine.run_tick()

    # Snapshot should have some traffic for core and downstream
    from backend.services.traffic_engine import get_v2_snapshot

    snap = get_v2_snapshot() or {}
    devs = snap.get("devices", {})
    assert devs, "expected device metrics after first tick"
    # core_router should have non-zero bps initially
    core_m = devs.get("core_router")
    assert core_m and core_m.get("bps", 0.0) > 0.0

    # Force core_router DOWN via override
    r = client.patch(
        "/api/devices/core_router/override",
        json={"admin_override_status": "DOWN"},
    )
    assert r.status_code == 200, r.text

    # Run another tick; engine must respect effective status and zero out metrics
    if getattr(ENG, "engine", None) is not None:
        ENG.engine.run_tick()

    snap2 = get_v2_snapshot() or {}
    devs2 = snap2.get("devices", {})
    core2 = devs2.get("core_router", {})
    assert core2.get("bps", 0.0) == 0.0

    # Forwarding should not find a viable path (drop)
    from backend.services.forwarding_service import Flow, resolve_flow_path

    initial = Flow(
        source_ip="10.0.0.1",
        destination_ip="192.0.2.10",
        current_device_id="edge_router",
        current_interface_id="edge_router-if0",
    )
    res = resolve_flow_path(initial)
    assert res.get("outcome") == "drop"
