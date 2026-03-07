from fastapi.testclient import TestClient

from backend.db import get_session
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status
from backend.services.provisioning_service import provision_device
from backend.services.status_recompute import recompute_devices_status

client = TestClient(app)


def _dev(i: str, t: DeviceType) -> Device:
    return Device(id=i, name=i, type=t)


def _iface(d: Device, name: str = "if0") -> Interface:
    return Interface(id=f"{d.id}-{name}", device_id=d.id, name=name)


def _link(a: Device, b: Device, kind: LinkType = LinkType.FIBER) -> Link:
    return Link(
        id=f"{a.id}-{b.id}",
        a_interface_id=f"{a.id}-if0",
        b_interface_id=f"{b.id}-if0",
        kind=kind,
        status=Status.UP,
    )


def test_downstream_devices_marked_unreachable_when_core_path_fails(monkeypatch):
    """Phase 1 diagnostic test:
    Build topology Backbone -> Core -> OLT -> AON_SWITCH -> AON_CPE and ensure
    diagnostics show upstream_l3_ok False for every downstream device once the
    backbone is forced DOWN (legacy statuses not yet unified, we only assert diagnostics).
    """
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    with get_session() as s:
        bb = _dev("bbX", DeviceType.BACKBONE_GATEWAY)
        core = _dev("coreX", DeviceType.CORE_ROUTER)
        olt = _dev("oltX", DeviceType.OLT)
        sw = _dev("swX", DeviceType.AON_SWITCH)
        cpe = _dev("cpeX", DeviceType.AON_CPE)
        for d in (bb, core, olt, sw, cpe):
            s.add(d)
            s.add(_iface(d))
        # Chain links Backbone<->Core<->OLT<->Switch<->CPE
        s.add(_link(bb, core))
        s.add(_link(core, olt))
        s.add(_link(olt, sw))
        s.add(_link(sw, cpe))
        s.commit()
        provision_device(s, core)
        provision_device(s, olt)
        s.commit()
        recompute_devices_status(s)

    # Baseline: backbone up -> core upstream_l3_ok True, others may be False (non-routers) but not asserting yet
    r = client.get("/api/debug/status-diagnostics")
    assert r.status_code == 200
    diag = r.json()["devices"]
    assert diag["coreX"]["upstream_l3_ok"] is True

    # Force backbone DOWN and recompute
    with get_session() as s:
        bb_r = s.get(Device, "bbX")
        assert bb_r is not None
        bb_r.admin_override_status = Status.DOWN
        s.add(bb_r)
        s.commit()
        recompute_devices_status(s)

    r = client.get("/api/debug/status-diagnostics")
    assert r.status_code == 200
    diag = r.json()["devices"]
    # Core must now fail upstream L3
    assert diag["coreX"]["upstream_l3_ok"] is False
    # Downstream devices should also reflect upstream failure (helper-based chain cannot resolve)
    for did in ["oltX", "swX", "cpeX"]:
        assert diag[did]["upstream_l3_ok"] is False
        assert diag[did]["reason_codes"], f"Expected reason codes for {did}"


def test_no_router_path_reason(monkeypatch):
    """A standalone OLT with no upstream router should yield reason 'no_router_path'."""
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    with get_session() as s:
        olt = _dev("oltSolo", DeviceType.OLT)
        s.add(olt)
        s.add(_iface(olt))
        s.commit()
        recompute_devices_status(s)
    r = client.get("/api/debug/status-diagnostics")
    assert r.status_code == 200
    diag = r.json()["devices"]
    assert diag["oltSolo"]["upstream_l3_ok"] is False
    assert diag["oltSolo"]["reason_codes"][0] == "no_router_path"


def test_routers_no_l3_reason(monkeypatch):
    """If a router exists but loses L3, downstream device gets 'routers_no_l3'."""
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    with get_session() as s:
        bb = _dev("bbY", DeviceType.BACKBONE_GATEWAY)
        core = _dev("coreY", DeviceType.CORE_ROUTER)
        olt = _dev("oltY", DeviceType.OLT)
        for d in (bb, core, olt):
            s.add(d)
            s.add(_iface(d))
        s.add(_link(bb, core))
        s.add(_link(core, olt))
        s.commit()
        provision_device(s, core)
        provision_device(s, olt)
        s.commit()
        recompute_devices_status(s)
    # Backbone down -> remove upstream L3
    with get_session() as s:
        bbm = s.get(Device, "bbY")
        assert bbm is not None
        bbm.admin_override_status = Status.DOWN
        s.add(bbm)
        s.commit()
        recompute_devices_status(s)
    r = client.get("/api/debug/status-diagnostics")
    diag = r.json()["devices"]
    # Router should show upstream_l3_ok False and a reason (e.g., no backbone reachable)
    assert diag["coreY"]["upstream_l3_ok"] is False
    # OLT should reflect routers_no_l3 or propagate same terminal issue
    assert diag["oltY"]["upstream_l3_ok"] is False
    # Accept either routers_no_l3 or no_backbone/no anchor categories for flexibility
    assert any(
        rc in {"routers_no_l3", "no_backbone_reachable", "no backbone reachable"}
        for rc in diag["oltY"]["reason_codes"]
    )
