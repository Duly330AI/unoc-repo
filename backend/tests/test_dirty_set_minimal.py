from __future__ import annotations

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link
from backend.services.graph_index import Change, GraphIndex


def _mk_dev(dev_id: str, t: DeviceType = DeviceType.EDGE_ROUTER) -> None:
    init_db()
    with get_session() as s:
        if s.get(Device, dev_id) is None:
            s.add(Device(id=dev_id, name=dev_id, type=t))
            s.commit()


def _mk_if(dev_id: str, if_id: str) -> None:
    init_db()
    with get_session() as s:
        if s.get(Interface, if_id) is None:
            s.add(Interface(id=if_id, device_id=dev_id, name=if_id))
            s.commit()


def _mk_link(link_id: str, a_if: str, b_if: str) -> None:
    init_db()
    with get_session() as s:
        if s.get(Link, link_id) is None:
            s.add(Link(id=link_id, a_interface_id=a_if, b_interface_id=b_if))
            s.commit()


def test_dirty_set_locality_and_determinism():
    # Build a small graph: a-b-c (line) and x-y (separate region)
    init_db()
    for d in ["a", "b", "c", "x", "y"]:
        _mk_dev(d)
    for dev, iface in [("a", "a0"), ("b", "b0"), ("c", "c0"), ("x", "x0"), ("y", "y0")]:
        _mk_if(dev, f"{iface}")
    _mk_link("l_ab", "a0", "b0")
    _mk_link("l_bc", "b0", "c0")
    _mk_link("l_xy", "x0", "y0")

    gi = GraphIndex()
    gi.build()

    # Change localized to l_ab should stay in region of (a,b,c)
    ds1 = gi.dirty_set_for_change(Change(links_updated={"l_ab"}))
    assert {"a", "b"}.issubset(ds1.devices)
    assert ds1.region_id is not None and ds1.region_id.startswith("r:")

    # Deterministic: same change yields identical dirty set contents (as sets) and region
    ds1b = gi.dirty_set_for_change(Change(links_updated={"l_ab"}))
    assert ds1.devices == ds1b.devices
    assert ds1.links == ds1b.links
    assert ds1.region_id == ds1b.region_id

    # Separate region change does not pull in (a,b,c)
    ds2 = gi.dirty_set_for_change(Change(links_updated={"l_xy"}))
    assert {"x", "y"}.issubset(ds2.devices)
    assert not ({"a", "b", "c"} & ds2.devices)

    # Device-only change coalesces neighbors one hop
    ds3 = gi.dirty_set_for_change(Change(devices_updated={"b"}))
    assert {"a", "b", "c"}.issubset(ds3.devices)
