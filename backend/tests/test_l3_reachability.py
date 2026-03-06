from __future__ import annotations

import pytest
from sqlmodel import Session

from backend.db import get_session
from backend.models import (
    VRF,
    AdminStatus,
    Device,
    DeviceType,
    Interface,
    InterfaceAddress,
    Neighbor,
    Route,
    Status,
)
from backend.services.dependency_resolver import has_l3_reachability_to_anchor
from backend.services.status_service import evaluate_device_status


@pytest.fixture(autouse=True)
def _strict_mode_env(monkeypatch):
    monkeypatch.setenv("UNOC_L3_STATUS_STRICT", "1")
    yield


def _mk_dev(s: Session, id: str, t: DeviceType, provisioned: bool = True, vrf: VRF | None = None):
    d = Device(id=id, name=id, type=t, provisioned=provisioned, vrf_id=(vrf.id if vrf else None))
    s.add(d)
    s.commit()
    return d


def _mk_if(s: Session, dev: Device, name: str, admin: AdminStatus = AdminStatus.UP):
    iface = Interface(id=f"{dev.id}-{name}", device_id=dev.id, name=name, admin_status=admin)
    s.add(iface)
    s.commit()
    return iface


def _addr(s: Session, iface: Interface, ip: str, prefix_len: int, vrf: VRF):
    from typing import cast

    rid = cast(int, vrf.id)
    s.add(InterfaceAddress(interface_id=iface.id, ip=ip, prefix_len=prefix_len, vrf_id=rid))
    s.commit()


def _nbr(s: Session, iface: Interface, ip: str, mac: str = "00:11:22:33:44:55"):
    s.add(Neighbor(interface_id=iface.id, ip_address=ip, mac_address=mac))
    s.commit()


def _route_default(s: Session, vrf: VRF, iface: Interface, next_hop: str):
    from typing import cast

    rid = cast(int, vrf.id)
    s.add(Route(vrf_id=rid, prefix="0.0.0.0/0", next_hop=next_hop, interface_id=iface.id))
    s.commit()


def test_l3_reachability_multihop_chain():
    with get_session() as s:
        # VRF and devices
        vrf = VRF(name="default")
        s.add(vrf)
        s.commit()
        s.refresh(vrf)

        gw = _mk_dev(s, "gw", DeviceType.BACKBONE_GATEWAY, provisioned=True, vrf=vrf)
        core = _mk_dev(s, "core", DeviceType.CORE_ROUTER, provisioned=True, vrf=vrf)
        edge = _mk_dev(s, "edge", DeviceType.EDGE_ROUTER, provisioned=True, vrf=vrf)

        # Interfaces
        gw_if = _mk_if(s, gw, "if0")
        core_u = _mk_if(s, core, "uplink")
        edge_u = _mk_if(s, edge, "uplink")

        # Wire links
        from backend.models import Link

        s.add(Link(id="l1", a_interface_id=edge_u.id, b_interface_id=core_u.id))
        s.add(Link(id="l2", a_interface_id=core_u.id, b_interface_id=gw_if.id))
        s.commit()

        # Assign IPs and neighbors
        _addr(s, core_u, "10.0.0.2", 31, vrf)
        _addr(s, edge_u, "10.0.0.1", 31, vrf)
        _addr(s, gw_if, "10.0.0.3", 31, vrf)
        # Neighbors for default next-hops
        _nbr(s, edge_u, "10.0.0.2")
        _nbr(s, core_u, "10.0.0.3")

        # Default routes on edge and core towards next hops
        _route_default(s, vrf, edge_u, "10.0.0.2")
        _route_default(s, vrf, core_u, "10.0.0.3")

        assert has_l3_reachability_to_anchor(s, edge) is True
        assert has_l3_reachability_to_anchor(s, core) is True

        # Active device status should be UP due to L3 reachability
        assert evaluate_device_status(edge) == Status.UP
        assert evaluate_device_status(core) == Status.UP


def test_l3_reachability_egress_admin_down():
    with get_session() as s:
        vrf = VRF(name="default")
        s.add(vrf)
        s.commit()
        s.refresh(vrf)

        gw = _mk_dev(s, "gw", DeviceType.BACKBONE_GATEWAY, provisioned=True, vrf=vrf)
        core = _mk_dev(s, "core", DeviceType.CORE_ROUTER, provisioned=True, vrf=vrf)

        core_u = _mk_if(s, core, "uplink", admin=AdminStatus.DOWN)
        gw_if = _mk_if(s, gw, "if0")

        from backend.models import Link

        s.add(Link(id="l1", a_interface_id=core_u.id, b_interface_id=gw_if.id))
        s.commit()

        _addr(s, core_u, "10.0.0.2", 31, vrf)
        _addr(s, gw_if, "10.0.0.3", 31, vrf)
        _nbr(s, core_u, "10.0.0.3")
        _route_default(s, vrf, core_u, "10.0.0.3")

        assert has_l3_reachability_to_anchor(s, core) is False
        assert evaluate_device_status(core) == Status.DOWN


def test_l3_missing_default_route_causes_down():
    with get_session() as s:
        vrf = VRF(name="default")
        s.add(vrf)
        s.commit()
        s.refresh(vrf)

        gw = _mk_dev(s, "gw", DeviceType.BACKBONE_GATEWAY, provisioned=True, vrf=vrf)
        edge = _mk_dev(s, "edge", DeviceType.EDGE_ROUTER, provisioned=True, vrf=vrf)

        edge_u = _mk_if(s, edge, "uplink")
        gw_if = _mk_if(s, gw, "if0")

        from backend.models import Link

        s.add(Link(id="l1", a_interface_id=edge_u.id, b_interface_id=gw_if.id))
        s.commit()

        _addr(s, edge_u, "10.0.0.2", 31, vrf)
        _addr(s, gw_if, "10.0.0.3", 31, vrf)
        # Intentionally do not create default route or neighbor

        assert has_l3_reachability_to_anchor(s, edge) is False
        assert evaluate_device_status(edge) == Status.DOWN
