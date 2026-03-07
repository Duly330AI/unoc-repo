from __future__ import annotations

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link
from backend.services.traffic.v2_engine import aggregate_dirty, prepare_dirty


def _mk_dev(session, dev_id: str, t: DeviceType = DeviceType.EDGE_ROUTER) -> Device:
    d = session.get(Device, dev_id)
    if d is None:
        d = Device(id=dev_id, name=dev_id, type=t)
        session.add(d)
        session.commit()
    return d


def _mk_iface(session, iface_id: str, dev_id: str) -> Interface:
    i = session.get(Interface, iface_id)
    if i is None:
        i = Interface(id=iface_id, name=iface_id, device_id=dev_id)
        session.add(i)
        session.commit()
    return i


def _mk_link(session, link_id: str, a_if: str, b_if: str) -> Link:
    ln = session.get(Link, link_id)
    if ln is None:
        ln = Link(id=link_id, a_interface_id=a_if, b_interface_id=b_if)
        session.add(ln)
        session.commit()
    return ln


def test_prepare_dirty_locality_endpoints_added():
    init_db()
    with get_session() as s:
        a = _mk_dev(s, "a")
        b = _mk_dev(s, "b")
        ia = _mk_iface(s, "ia", a.id)
        ib = _mk_iface(s, "ib", b.id)
        _mk_link(s, "l1", ia.id, ib.id)

        dirty = {"devices": [], "links": ["l1"], "region_id": "r:1"}
        prepared = prepare_dirty(dirty)
        # Endpoints devices are included deterministically
        assert prepared.device_ids == ["a", "b"]
        assert prepared.link_ids == ["l1"]
        assert prepared.region_id == "r:1"


def test_prepare_dirty_dedup_and_ordering():
    init_db()
    with get_session() as s:
        _mk_dev(s, "x")
        _mk_dev(s, "y")
        prepared = prepare_dirty({"devices": ["y", "x", "x"], "links": ["k", "k"]})
        assert prepared.device_ids == ["x", "y"]
        assert prepared.link_ids == ["k"]


def test_aggregate_dirty_incremental_vs_full_parity_counts():
    init_db()
    with get_session() as s:
        _mk_dev(s, "d1")
        _mk_dev(s, "d2")
        ia = _mk_iface(s, "ia", "d1")
        ib = _mk_iface(s, "ib", "d2")
        _mk_link(s, "l1", ia.id, ib.id)

        prepared = prepare_dirty({"devices": ["d2"], "links": ["l1"]})
        inc = aggregate_dirty(prepared, incremental=True)
        full = aggregate_dirty(prepared, incremental=False)

        # Incremental returns only affected ids; full returns entire universe
        assert set(inc.device_ids) <= set(full.device_ids)
        assert set(inc.link_ids) <= set(full.link_ids)

        # Deterministic ordering
        assert inc.device_ids == sorted(inc.device_ids)
        assert inc.link_ids == sorted(inc.link_ids)
        assert full.device_ids == sorted(full.device_ids)
        assert full.link_ids == sorted(full.link_ids)


def test_aggregate_dirty_idempotence_and_determinism():
    init_db()
    with get_session() as s:
        _mk_dev(s, "ra")
        _mk_dev(s, "rb")
        prepared = prepare_dirty({"devices": ["rb", "ra", "rb"]})
        a1 = aggregate_dirty(prepared)
        a2 = aggregate_dirty(prepared)
        assert a1 == a2
