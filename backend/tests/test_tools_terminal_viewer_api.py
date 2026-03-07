from __future__ import annotations

from fastapi.testclient import TestClient

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Link


def _mk_link(a_if: str, b_if: str) -> None:
    with get_session() as s:
        if not s.get(Link, f"{a_if}__{b_if}"):
            s.add(Link(id=f"{a_if}__{b_if}", a_interface_id=a_if, b_interface_id=b_if))
            s.commit()


def test_tools_endpoints_always_available():
    init_db()
    client = TestClient(app)

    r1 = client.post("/api/tools/ping", json={"source_device_id": "a", "target_device_id": "b"})
    # With no devices present, this should be 404 for missing source device, not 404 for gating
    assert r1.status_code in (404, 422)
    r2 = client.post(
        "/api/tools/traceroute", json={"source_device_id": "a", "target_device_id": "b"}
    )
    assert r2.status_code in (404, 422)


def test_ping_and_traceroute_basic_path():
    init_db()
    client = TestClient(app)

    # Create two routers with one link
    for rid in ("ta", "tb"):
        rr = client.post("/api/devices", json={"id": rid, "name": rid, "type": "EDGE_ROUTER"})
        assert rr.status_code in (200, 201)
    # Default "if0" interfaces are auto-created by the devices endpoint for generic devices,
    # so no manual interface creation is required here.
    _mk_link("ta-if0", "tb-if0")

    # ping should succeed and return hops [ta, tb]
    pr = client.post(
        "/api/tools/ping",
        json={"source_device_id": "ta", "target_device_id": "tb"},
    )
    assert pr.status_code == 200, pr.text
    data = pr.json()
    assert data["outcome"] in {"success", "unreachable"}
    # For a directly linked pair, we expect success
    assert data["outcome"] == "success", data
    assert data["hops"][:2] == ["ta", "tb"], data

    # traceroute should produce a hop list ending at tb
    tr = client.post(
        "/api/tools/traceroute",
        json={"source_device_id": "ta", "target_device_id": "tb", "max_hops": 4},
    )
    assert tr.status_code == 200, tr.text
    tdata = tr.json()
    assert tdata["outcome"] in {"reached", "ttl_exceeded"}, tdata
    assert tdata["hops"], tdata
    assert tdata["hops"][0]["device_id"] == "ta"
    assert tdata["final_device_id"] in {"ta", "tb"}
    # In small topology path should reach tb
    assert tdata["final_device_id"] == "tb"
