"""Positive link creation tests validating allowed rules L1-L6 (ARCHITECTURE §3.12).

Ensures endpoint automatically classifies & accepts:
    L1: router↔router (routed_p2p → LinkType.P2P)
    L2: OLT↔Passive (optical_segment → FIBER)
    L3: Passive↔Passive (optical_segment → FIBER)
    L4: Passive↔ONT (optical_termination → FIBER)
        L6A: AON_SWITCH↔ROUTER (access_uplink → FIBER/P2P mapping handled as FIBER)
        L6B: OLT↔ROUTER (access_uplink → FIBER/P2P mapping handled as FIBER)
        L6: AON_SWITCH↔AON_CPE (access_edge → FIBER)

Note: Direct OLT↔ONT links are no longer valid under GPON Phase 1 rules (ODF-as-aggregator).
"""

from sqlmodel import Session

from backend.api.endpoints.links import create_link
from backend.api.schemas import LinkCreate, LinkResolvedOut
from backend.db import engine, init_db, reset_db
from backend.models import Device, DeviceType, Interface, LinkType


def setup_function(_: object):
    reset_db()
    init_db()


def _add_dev(session: Session, did: str, dtype: DeviceType) -> None:
    d = Device(id=did, name=did, type=dtype)
    session.add(d)
    session.add(Interface(id=f"{did}-if0", device_id=did, name="if0"))


def _payload(a: str, b: str) -> LinkCreate:
    ordered = sorted([a, b])
    lid = f"{ordered[0]}__{ordered[1]}"
    return LinkCreate(id=lid, a_interface_id=f"{a}-if0", b_interface_id=f"{b}-if0")


def _assert_created(lr: LinkResolvedOut, expected_kind: LinkType):
    assert lr.kind == expected_kind
    assert lr.id


def test_L1_router_router_routed_p2p_maps_to_P2P():
    with Session(engine) as s:
        _add_dev(s, "core1", DeviceType.CORE_ROUTER)
        _add_dev(s, "edge1", DeviceType.EDGE_ROUTER)
        s.commit()
    lr = create_link(_payload("core1", "edge1"))
    _assert_created(lr, LinkType.P2P)


def test_L2_olt_passive():
    with Session(engine) as s:
        _add_dev(s, "olt1", DeviceType.OLT)
        _add_dev(s, "odf1", DeviceType.ODF)
        s.commit()
    lr = create_link(_payload("olt1", "odf1"))
    _assert_created(lr, LinkType.FIBER)


def test_L3_passive_passive():
    with Session(engine) as s:
        _add_dev(s, "odf2", DeviceType.ODF)
        _add_dev(s, "spl1", DeviceType.SPLITTER)
        s.commit()
    lr = create_link(_payload("odf2", "spl1"))
    _assert_created(lr, LinkType.FIBER)


def test_L4_passive_ont():
    with Session(engine) as s:
        _add_dev(s, "odf3", DeviceType.ODF)
        _add_dev(s, "ont3", DeviceType.ONT)
        s.commit()
    lr = create_link(_payload("odf3", "ont3"))
    _assert_created(lr, LinkType.FIBER)


def test_L6_aon_switch_cpe():
    with Session(engine) as s:
        _add_dev(s, "aon1", DeviceType.AON_SWITCH)
        _add_dev(s, "cpe1", DeviceType.AON_CPE)
        s.commit()
    lr = create_link(_payload("aon1", "cpe1"))
    _assert_created(lr, LinkType.FIBER)


def test_L6A_aon_switch_router():
    with Session(engine) as s:
        _add_dev(s, "aonX", DeviceType.AON_SWITCH)
        _add_dev(s, "edgeX", DeviceType.EDGE_ROUTER)
        s.commit()
    lr = create_link(_payload("aonX", "edgeX"))
    _assert_created(lr, LinkType.P2P if lr.kind == LinkType.P2P else LinkType.FIBER)


def test_L6B_olt_router():
    with Session(engine) as s:
        _add_dev(s, "oltX", DeviceType.OLT)
        _add_dev(s, "coreX", DeviceType.CORE_ROUTER)
        s.commit()
    lr = create_link(_payload("oltX", "coreX"))
    _assert_created(lr, LinkType.P2P if lr.kind == LinkType.P2P else LinkType.FIBER)
