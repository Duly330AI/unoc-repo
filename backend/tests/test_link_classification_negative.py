"""Negative link creation tests validating classification rules (ARCHITECTURE §3.12).

Covers invalid combinations:
 - ONT ↔ ONT (L8 peer_invalid)
 - Router/Core ↔ Passive (L7 mixed_invalid)
 - Passive ↔ Backbone/Core without OLT (implicit L7)
"""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from backend.api.endpoints.links import create_link
from backend.api.schemas import LinkCreate
from backend.db import engine, init_db, reset_db
from backend.models import Device, DeviceType, Interface


def setup_function(_: object):  # isolate each test
    reset_db()
    init_db()


def _add_dev(s: Session, id_: str, t: DeviceType) -> Device:
    d = Device(id=id_, name=id_, type=t)
    s.add(d)
    # create default -if0 interface (mirrors ensure_default_interface logic) (see ARCHITECTURE §9)
    iface = Interface(id=f"{id_}-if0", device_id=id_, name="if0")
    s.add(iface)
    return d


def _mk_payload(a_dev: str, b_dev: str) -> LinkCreate:
    # ID canonical ordering (device ids sorted) mirroring endpoint logic
    dids = sorted([a_dev, b_dev])
    link_id = f"{dids[0]}__{dids[1]}"
    return LinkCreate(id=link_id, a_interface_id=f"{a_dev}-if0", b_interface_id=f"{b_dev}-if0")


def test_ont_ont_invalid():
    with Session(engine) as s:
        _add_dev(s, "ont1", DeviceType.ONT)
        _add_dev(s, "ont2", DeviceType.ONT)
        s.commit()
    payload = _mk_payload("ont1", "ont2")
    with pytest.raises(HTTPException) as e:
        create_link(payload)  # classification should reject (L8)
    assert "INVALID_LINK_TYPE" in str(e.value.detail)


def test_router_passive_invalid():
    with Session(engine) as s:
        _add_dev(s, "core1", DeviceType.CORE_ROUTER)
        _add_dev(s, "odf1", DeviceType.ODF)
        s.commit()
    payload = _mk_payload("core1", "odf1")
    with pytest.raises(HTTPException) as e:
        create_link(payload)
    assert "INVALID_LINK_TYPE" in str(e.value.detail)


def test_backbone_passive_invalid():
    with Session(engine) as s:
        _add_dev(s, "bb1", DeviceType.BACKBONE_GATEWAY)
        _add_dev(s, "hop1", DeviceType.HOP)
        s.commit()
    payload = _mk_payload("bb1", "hop1")
    with pytest.raises(HTTPException):
        create_link(payload)


def test_pop_disallowed_with_edge_router():
    """POP must never participate in links (container-only invariant)."""
    with Session(engine) as s:
        _add_dev(s, "popx", DeviceType.POP)
        _add_dev(s, "edge1", DeviceType.EDGE_ROUTER)
        s.commit()
    payload = _mk_payload("popx", "edge1")
    with pytest.raises(HTTPException) as e:
        create_link(payload)
    assert "POP_LINK_DISALLOWED" in str(e.value.detail)


def test_pop_disallowed_with_olt():
    with Session(engine) as s:
        _add_dev(s, "popx", DeviceType.POP)
        _add_dev(s, "olt1", DeviceType.OLT)
        s.commit()
    payload = _mk_payload("popx", "olt1")
    with pytest.raises(HTTPException) as e:
        create_link(payload)
    assert "POP_LINK_DISALLOWED" in str(e.value.detail)


def test_pop_disallowed_with_aon_switch():
    with Session(engine) as s:
        _add_dev(s, "popx", DeviceType.POP)
        _add_dev(s, "aon1", DeviceType.AON_SWITCH)
        s.commit()
    payload = _mk_payload("aon1", "popx")  # ordering agnostic
    with pytest.raises(HTTPException) as e:
        create_link(payload)
    assert "POP_LINK_DISALLOWED" in str(e.value.detail)
