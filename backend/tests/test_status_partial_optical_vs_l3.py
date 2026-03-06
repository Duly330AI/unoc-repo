from fastapi.testclient import TestClient

from backend.db import get_session
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status
from backend.services.provisioning_service import provision_device
from backend.services.status_recompute import recompute_devices_status
from backend.tests.helpers_l3 import l3_pair

client = TestClient(app)


def _dev(i: str, t: DeviceType) -> Device:
    return Device(id=i, name=i, type=t)


def _iface(d: Device, name: str = "if0") -> Interface:
    return Interface(id=f"{d.id}-{name}", device_id=d.id, name=name)


def _link(a: Device, b: Device, kind: LinkType = LinkType.FIBER) -> Link:
    # Order link id deterministically (DB uniqueness)
    a_id, b_id = sorted([a.id, b.id])
    return Link(
        id=f"{a_id}__{b_id}",
        a_interface_id=f"{a.id}-if0",
        b_interface_id=f"{b.id}-if0",
        kind=kind,
        status=Status.UP,
    )


def test_ont_remains_down_when_l3_lost_but_optical_signal_ok(monkeypatch):
    """Phase 1 Step 4 test:
    Ensure ONT effective status is DOWN when upstream routed L3 path disappears
    even though the optical segment/path to OLT remains physically UP.

    Topology: BACKBONE_GATEWAY(bb) -- CORE_ROUTER(core) -- OLT(olt) -- ODF(odf) -- ONT(ont)
    Steps:
      1. Build full chain, provision core & olt & ont (after optical links) -> ONT should be UP initially.
      2. Force backbone DOWN (admin override) -> recompute -> ONT should transition to DOWN because
         unified upstream helper reports upstream_l3_ok False (optical links still UP).
    """
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    with get_session() as s:
        # Build devices
        bb = _dev("bbP", DeviceType.BACKBONE_GATEWAY)
        core = _dev("coreP", DeviceType.CORE_ROUTER)
        olt = _dev("oltP", DeviceType.OLT)
        odf = _dev("odfP", DeviceType.ODF)
        ont = _dev("ontP", DeviceType.ONT)
        for d in (bb, core, olt, odf, ont):
            s.add(d)
            s.add(_iface(d))
        # Links (logical + optical)
        s.add(_link(bb, core))  # logical backbone <-> core
        s.add(_link(core, olt))  # logical core <-> olt
        s.add(_link(olt, odf))  # optical
        s.add(_link(odf, ont))  # optical
        s.commit()
        # Establish L3 adjacency core <-> backbone (VRF, /31, neighbor, default route)
        with l3_pair("coreP", "bbP", "coreP-if0", "bbP-if0"):
            pass
        # Provision upstream chain (backbone acts as non-provisioned anchor). Provision core and OLT, then ONT.
        provision_device(s, core)
        provision_device(s, olt)
        provision_device(s, ont)
        s.commit()
        recompute_devices_status(s)

    # Baseline: ONT should be UP (all upstream + optical ok)
    r1 = client.get("/api/devices/ontP")
    assert r1.status_code == 200
    # ONT becomes UP because collapsed optical path + upstream core->backbone adjacency exists
    assert r1.json()["status"] == "UP"

    # Force backbone DOWN -> break routed L3 path while optical fiber links remain UP
    with get_session() as s:
        bbm = s.get(Device, "bbP")
        assert bbm is not None
        bbm.admin_override_status = Status.DOWN
        s.add(bbm)
        s.commit()
        recompute_devices_status(s)

    r2 = client.get("/api/devices/ontP")
    assert r2.status_code == 200
    body2 = r2.json()
    # Unified strict model: ONT should transition DOWN when upstream L3 anchor lost
    assert body2["status"] == "DOWN"
    # Diagnostics must reflect upstream_l3_ok False
    diag = client.get("/api/debug/status-diagnostics").json()["devices"]["ontP"]
    assert diag["upstream_l3_ok"] is False
    assert any(rc for rc in diag["reason_codes"])  # at least one reason
