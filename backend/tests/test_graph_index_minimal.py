from __future__ import annotations

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link
from backend.services.graph_index import Change, GraphIndex, RegionVersionMap


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


def test_graph_index_build_and_neighbors():
    init_db()
    _mk_dev("a")
    _mk_dev("b")
    _mk_if("a", "a-if0")
    _mk_if("b", "b-if0")
    _mk_link("l1", "a-if0", "b-if0")

    gi = GraphIndex()
    gi.build()

    assert gi.neighbors_device("a") == {"b"}
    assert gi.neighbors_link("l1") == {"a", "b"}
    assert gi.region_id_of_device("a") == gi.region_id_of_device("b")


def test_dirty_set_is_local():
    init_db()
    _mk_dev("b")
    _mk_if("b", "b-if0")
    _mk_dev("c")
    _mk_if("c", "c-if0")
    _mk_link("l2", "b-if0", "c-if0")

    gi = GraphIndex()
    gi.build()
    ds = gi.dirty_set_for_change(Change(links_updated={"l2"}))
    # Dirty devices include endpoints and their neighbors (conservative one-hop)
    assert {"b", "c"}.issubset(ds.devices)
    assert ds.region_id.startswith("r")


def test_region_version_map():
    rvm = RegionVersionMap()
    assert rvm.version("r1") == 0
    assert rvm.bump("r1") == 1
    assert rvm.version("r1") == 1
