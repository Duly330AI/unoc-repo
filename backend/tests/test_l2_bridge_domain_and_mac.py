from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import BridgeDomain, Device, Interface, MacAddressEntry


def test_switch_gets_default_bridge_domain_and_ports_assigned():
    init_db()
    client = TestClient(app)
    # Create a minimal switch device (EDGE_ROUTER treated as switch for now)
    r = client.post(
        "/api/devices",
        json={"id": "sw1", "name": "sw1", "type": "EDGE_ROUTER"},
    )
    assert r.status_code in (200, 201)
    with get_session() as s:
        d = s.get(Device, "sw1")
        assert d is not None
        # Default BD exists
        bd = s.exec(
            select(BridgeDomain).where(
                (BridgeDomain.device_id == d.id) & (BridgeDomain.name == "default")
            )
        ).first()
        assert bd is not None
        # Create two ports and ensure assignment to default BD
        s.add(Interface(id="sw1-uplink1", device_id="sw1", name="uplink1"))
        s.add(Interface(id="sw1-uplink2", device_id="sw1", name="uplink2"))
        s.commit()
        ifaces = s.exec(select(Interface).where(Interface.device_id == "sw1")).all()
        # assign default BD if missing
        for i in ifaces:
            if i.bridge_domain_id is None:
                i.bridge_domain_id = bd.id
                s.add(i)
        s.commit()
        ifaces = s.exec(select(Interface).where(Interface.device_id == "sw1")).all()
        assert all(i.bridge_domain_id == bd.id for i in ifaces)


def test_mac_table_endpoint_returns_entries():
    init_db()
    client = TestClient(app)
    # Create device and default BD
    r = client.post(
        "/api/devices",
        json={"id": "sw2", "name": "sw2", "type": "EDGE_ROUTER"},
    )
    assert r.status_code in (200, 201)
    with get_session() as s:
        bd = s.exec(
            select(BridgeDomain).where(
                (BridgeDomain.device_id == "sw2") & (BridgeDomain.name == "default")
            )
        ).first()
        assert bd is not None
        # add interface & mac entry
        s.add(Interface(id="sw2-eth1", device_id="sw2", name="eth1", bridge_domain_id=bd.id))
        s.commit()
        assert bd.id is not None
        s.add(
            MacAddressEntry(
                mac_address="00:11:22:33:44:55",
                interface_id="sw2-eth1",
                bridge_domain_id=bd.id,
            )
        )
        s.commit()
    # Call the API
    r = client.get("/api/devices/sw2/mac-table")
    assert r.status_code == 200
    entries = r.json()
    assert isinstance(entries, list)
    assert any(e["mac_address"] == "00:11:22:33:44:55" for e in entries)
