"""
Integration test for metrics snapshot endpoint.

Tests GET /api/metrics/snapshot endpoint that provides full traffic/status snapshot.
Validates shape, device/link metrics, and traffic tick increments.

REQUIRES: Traffic Engine Go service (port 8080) + PostgreSQL
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status
from backend.services.metrics_service import METRICS

pytestmark = pytest.mark.integration  # Mark entire module as integration test


def _mk_device(id: str, t: DeviceType, status: Status = Status.UP) -> None:
    init_db()
    with get_session() as s:
        s.add(Device(id=id, name=id, type=t, status=status))
        s.commit()


def test_metrics_snapshot_basic_shape_and_tick():
    client = TestClient(app)
    # Create a small topology with core anchor and links for link snapshot
    _mk_device("core1", DeviceType.CORE_ROUTER, Status.UP)
    _mk_device("olt1", DeviceType.OLT, Status.UP)
    _mk_device("ont1", DeviceType.ONT, Status.UP)
    # interfaces and links
    with get_session() as s:
        s.add(Interface(id="core1-if0", device_id="core1", name="if0", capacity=1000))
        s.add(Interface(id="olt1-if0", device_id="olt1", name="if0", capacity=1000))
        s.add(Interface(id="ont1-if0", device_id="ont1", name="if0", capacity=1000))
        s.add(
            Link(
                id="l_core",
                a_interface_id="olt1-if0",
                b_interface_id="core1-if0",
                status=Status.UP,
                kind=LinkType.FIBER,
            )
        )
        s.add(
            Link(
                id="l_ont1",
                a_interface_id="ont1-if0",
                b_interface_id="olt1-if0",
                status=Status.UP,
                kind=LinkType.FIBER,
            )
        )
        s.commit()

    # Process a tick with traffic on the leaf
    METRICS.process_tick([("ont1", 50.0 * 1_000_000.0)], tick=7)

    r = client.get("/api/metrics/snapshot")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert body["lastTick"] == 7
    assert "devices" in body and isinstance(body["devices"], dict)
    # Should include devices
    assert "ont1" in body["devices"]
    assert "olt1" in body["devices"]
    # ont1 has non-zero bps, utilization may be clamped if capacity is undefined
    ont = body["devices"]["ont1"]
    assert ont["bps"] > 0
    # Allow either int or float JSON number
    assert isinstance(ont["utilization"], (int, float))  # noqa: UP038
    # Upstream propagation means OLT and CORE carry the leaf traffic along the path
    olt = body["devices"]["olt1"]
    assert olt["bps"] > 0
    assert isinstance(olt["utilization"], int | float)
    assert "core1" in body["devices"]
    core = body["devices"]["core1"]
    assert core["bps"] > 0
    assert isinstance(core["utilization"], int | float)

    # Links snapshot present
    assert "links" in body and isinstance(body["links"], dict)
    # Expect both links populated with metrics
    assert "l_core" in body["links"]
    assert "l_ont1" in body["links"]
    l_ont1 = body["links"]["l_ont1"]
    l_core = body["links"]["l_core"]
    assert l_ont1["bps"] > 0
    assert l_core["bps"] > 0
    # With 1000 Mbps capacity, 50 Mbps traffic → 0.05 utilization on leaf link
    assert isinstance(l_ont1["utilization"], int | float)
