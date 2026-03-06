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
    a_id, b_id = sorted([a.id, b.id])
    return Link(
        id=f"{a_id}__{b_id}",
        a_interface_id=f"{a.id}-if0",
        b_interface_id=f"{b.id}-if0",
        kind=kind,
        status=Status.UP,
    )


def test_passive_inline_isolated_then_valid_chain(monkeypatch):
    """Passive device should be DOWN when isolated and become UP only when:
    - It has at least two neighbors forming a chain between an upstream active (OLT) with L3
    - and a downstream terminator (ONT).
    Topology stages:
      Stage1: ODF alone -> DOWN
      Stage2: OLT -- ODF (no terminator) -> still DOWN
      Stage3: OLT -- ODF -- ONT (after provisioning & upstream core path) -> ODF UP
    """
    monkeypatch.setenv("UNOC_DEV_FEATURES", "1")
    # Device IDs (avoid storing detached ORM instances across sessions)
    ids = {
        "bb": "bbPas",
        "core": "corePas",
        "olt": "oltPas",
        "odf": "odfPas",
        "ont": "ontPas",
    }
    with get_session() as s:
        # Seed devices
        for dev_id, d_type in [
            (ids["bb"], DeviceType.BACKBONE_GATEWAY),
            (ids["core"], DeviceType.CORE_ROUTER),
            (ids["olt"], DeviceType.OLT),
            (ids["odf"], DeviceType.ODF),
            (ids["ont"], DeviceType.ONT),
        ]:
            d = _dev(dev_id, d_type)
            s.add(d)
            s.add(_iface(d))
        # Add backbone<->core link first
        bb = s.get(Device, ids["bb"])
        core = s.get(Device, ids["core"])
        s.add(_link(bb, core))  # type: ignore[arg-type]
        provision_device(s, core)  # type: ignore[arg-type]
        s.commit()

    # Stage1: isolated ODF
    with get_session() as s:
        recompute_devices_status(s)
    r_iso = client.get("/api/devices/odfPas")
    assert r_iso.status_code == 200
    assert r_iso.json()["status"] == "DOWN"

    # Stage2: add core<->olt and olt<->odf (still no terminator) -> ODF should remain DOWN
    with get_session() as s:
        core = s.get(Device, ids["core"])
        olt = s.get(Device, ids["olt"])
        odf = s.get(Device, ids["odf"])
        s.add(_link(core, olt))  # type: ignore[arg-type]
        provision_device(s, olt)  # type: ignore[arg-type]
        s.add(_link(olt, odf))  # type: ignore[arg-type]
        s.commit()
    recompute_devices_status(s)
    r_stage2 = client.get("/api/devices/odfPas")
    assert r_stage2.status_code == 200
    assert r_stage2.json()["status"] == "DOWN"  # still no downstream terminator

    # Stage3: add ONT downstream, provision ONT -> ODF should become UP
    with get_session() as s:
        odf = s.get(Device, ids["odf"])
        ont = s.get(Device, ids["ont"])
        s.add(_link(odf, ont))  # type: ignore[arg-type]
        provision_device(s, ont)  # type: ignore[arg-type]
        s.commit()
    recompute_devices_status(s)
    r_stage3 = client.get("/api/devices/odfPas")
    assert r_stage3.status_code == 200
    assert r_stage3.json()["status"] == "UP"
