"""Ensure client-supplied kind is ignored and server derives it.

The create_link endpoint derives kind from classification (routed_p2p -> P2P else FIBER).
This test crafts a payload attempting to set a different kind and asserts response kind follows server rule.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, DeviceType, Interface, LinkType


def _mk_dev(id: str, type_: DeviceType):
    with get_session() as s:
        d = Device(id=id, name=id, type=type_)
        s.add(d)
        s.commit()
        # ensure default interface exists
        iface = Interface(id=f"{id}-if0", device_id=id, name="if0")
        s.add(iface)
        s.commit()


def test_link_kind_override_blocked():
    init_db()
    _mk_dev("core1", DeviceType.CORE_ROUTER)
    _mk_dev("edge1", DeviceType.EDGE_ROUTER)
    client = TestClient(app)
    # Attempt to force MGMT kind (invalid for this classification) – endpoint should derive FIBER or P2P
    resp = client.post(
        "/api/links",
        json={
            "id": "core1__edge1",
            "a_interface_id": "core1-if0",
            "b_interface_id": "edge1-if0",
            "kind": "MGMT",  # should be ignored
            "status": "UP",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["kind"] in {LinkType.FIBER.value, LinkType.P2P.value}
    assert data["kind"] != "MGMT"
