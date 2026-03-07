from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db
from backend.main import app
from backend.models import BridgeDomain, Interface, MacAddressEntry
from backend.services.l2_service import process_frame


def ensure_switch(device_id: str = "swl2") -> None:
    client = TestClient(app)
    r = client.post(
        "/api/devices",
        json={"id": device_id, "name": device_id, "type": "EDGE_ROUTER"},
    )
    assert r.status_code in (200, 201)


def test_learning_creates_entry():
    init_db()
    ensure_switch("swl2a")
    with get_session() as s:
        bd = s.exec(
            select(BridgeDomain).where(
                (BridgeDomain.device_id == "swl2a") & (BridgeDomain.name == "default")
            )
        ).first()
        assert bd is not None
        # create two ports in BD
        s.add(Interface(id="swl2a-eth1", device_id="swl2a", name="eth1", bridge_domain_id=bd.id))
        s.add(Interface(id="swl2a-eth2", device_id="swl2a", name="eth2", bridge_domain_id=bd.id))
        s.commit()

    # Send frame with new src MAC on eth1
    res = process_frame(
        device_id="swl2a",
        ingress_interface_id="swl2a-eth1",
        frame={"source_mac": "00:aa:bb:cc:dd:ee", "destination_mac": "ff:ff:ff:ff:ff:ff"},
    )
    assert res["action"] == "flood"  # broadcast floods

    with get_session() as s:
        entry = s.exec(
            select(MacAddressEntry).where(MacAddressEntry.mac_address == "00:aa:bb:cc:dd:ee")
        ).first()
        assert entry is not None
        assert entry.interface_id == "swl2a-eth1"


def test_forward_to_known_destination():
    init_db()
    ensure_switch("swl2b")
    with get_session() as s:
        bd = s.exec(
            select(BridgeDomain).where(
                (BridgeDomain.device_id == "swl2b") & (BridgeDomain.name == "default")
            )
        ).first()
        assert bd is not None
        s.add(Interface(id="swl2b-eth1", device_id="swl2b", name="eth1", bridge_domain_id=bd.id))
        s.add(Interface(id="swl2b-eth2", device_id="swl2b", name="eth2", bridge_domain_id=bd.id))
        s.commit()

    # Learn destination MAC on eth2 first
    process_frame(
        device_id="swl2b",
        ingress_interface_id="swl2b-eth2",
        frame={"source_mac": "00:11:22:33:44:55", "destination_mac": "ff:ff:ff:ff:ff:ff"},
    )

    # Now send to known destination from eth1 -> should forward to eth2
    res = process_frame(
        device_id="swl2b",
        ingress_interface_id="swl2b-eth1",
        frame={"source_mac": "de:ad:be:ef:00:01", "destination_mac": "00:11:22:33:44:55"},
    )
    assert res["action"] == "forward"
    assert res["egress_interface_id"] == "swl2b-eth2"


def test_unknown_unicast_floods():
    init_db()
    ensure_switch("swl2c")
    with get_session() as s:
        bd = s.exec(
            select(BridgeDomain).where(
                (BridgeDomain.device_id == "swl2c") & (BridgeDomain.name == "default")
            )
        ).first()
        assert bd is not None
        s.add(Interface(id="swl2c-eth1", device_id="swl2c", name="eth1", bridge_domain_id=bd.id))
        s.add(Interface(id="swl2c-eth2", device_id="swl2c", name="eth2", bridge_domain_id=bd.id))
        s.add(Interface(id="swl2c-eth3", device_id="swl2c", name="eth3", bridge_domain_id=bd.id))
        s.commit()

    # Unknown destination from eth1 should flood to eth2 and eth3
    res = process_frame(
        device_id="swl2c",
        ingress_interface_id="swl2c-eth1",
        frame={"source_mac": "de:ad:be:ef:00:02", "destination_mac": "66:66:66:66:66:66"},
    )
    assert res["action"] == "flood"
    egress = set(res["egress_interface_ids"])  # type: ignore[index]
    assert egress == {"swl2c-eth2", "swl2c-eth3"}
