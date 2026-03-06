from __future__ import annotations

from typing import cast

from fastapi.testclient import TestClient

from backend.db import get_session, init_db
from backend.main import app
from backend.models import (
    VRF,
    Device,
    DeviceType,
    Interface,
    InterfaceAddress,
    Link,
    LinkType,
    Neighbor,
    Route,
    Status,
)


def _client() -> TestClient:
    return TestClient(app)


def _mk_basic_l3_topology():
    init_db()
    with get_session() as s:
        vrf = VRF(name="default")
        s.add(vrf)
        s.commit()
        s.refresh(vrf)

        gw = Device(id="gw", name="gw", type=DeviceType.BACKBONE_GATEWAY, provisioned=True)
        core = Device(
            id="core",
            name="core",
            type=DeviceType.CORE_ROUTER,
            provisioned=True,
            status=Status.UP,
            vrf_id=vrf.id,
        )
        s.add(gw)
        s.add(core)
        s.add(Interface(id="gw-if0", device_id="gw", name="if0", capacity=1000))
        s.add(Interface(id="core-if0", device_id="core", name="if0", capacity=1000))
        s.add(
            Link(
                id="l_core_gw",
                a_interface_id="core-if0",
                b_interface_id="gw-if0",
                status=Status.UP,
                kind=LinkType.FIBER,
            )
        )
        # Addressing and next-hop
        rid = cast(int, vrf.id)
        s.add(InterfaceAddress(interface_id="gw-if0", ip="10.0.0.1", prefix_len=30, vrf_id=rid))
        s.add(
            Neighbor(
                interface_id="core-if0", ip_address="10.0.0.1", mac_address="aa:bb:cc:dd:ee:ff"
            )
        )
        s.add(Route(vrf_id=rid, prefix="0.0.0.0/0", next_hop="10.0.0.1", interface_id="core-if0"))
        s.commit()


def test_l3_debug_endpoint_positive(monkeypatch):
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    _mk_basic_l3_topology()
    c = _client()
    r = c.get("/api/debug/l3-path/core")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["reason"] is None or body["reason"] == "none"
    # Expect chain to go from core to gw
    assert body["chain"][0] == "core"
    assert body["chain"][-1] == "gw"


def test_l3_debug_endpoint_negative_missing_default(monkeypatch):
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    init_db()
    with get_session() as s:
        vrf = VRF(name="default")
        s.add(vrf)
        s.commit()
        s.refresh(vrf)
        gw = Device(id="gw2", name="gw2", type=DeviceType.BACKBONE_GATEWAY, provisioned=True)
        edge = Device(
            id="edge2",
            name="edge2",
            type=DeviceType.EDGE_ROUTER,
            provisioned=True,
            status=Status.UP,
            vrf_id=vrf.id,
        )
        s.add(gw)
        s.add(edge)
        # No default route on edge2
        s.commit()

    c = _client()
    r = c.get("/api/debug/l3-path/edge2")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["reason"] in {"no_default_route", "no_eligible_route"}
    assert body["chain"][0] == "edge2"


def test_prometheus_series_exposed_after_calls(monkeypatch):
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    _mk_basic_l3_topology()
    c = _client()
    # Call endpoint to trigger path trace and metrics
    r = c.get("/api/debug/l3-path/core")
    assert r.status_code == 200
    # Scrape Prometheus and ensure our series exist
    m = c.get("/api/metrics/prometheus")
    assert m.status_code == 200
    text = m.text
    assert "l3_resolver_calls_total" in text
    assert "l3_resolver_duration_seconds" in text
    assert "l3_resolver_hops" in text
