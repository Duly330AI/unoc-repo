from fastapi.testclient import TestClient
from sqlmodel import select

from backend.db import get_session, init_db, reset_db
from backend.main import app
from backend.models import PhysicalMedium
from backend.services.optical_path_resolver import resolve_optical_path
from backend.services.seed_service import ensure_physical_media

client = TestClient(app)


def _mk_dev(id: str, t: str, parent: str | None = None, insertion: float | None = None):
    payload = {"id": id, "name": id, "type": t, "status": "UP"}
    if parent:
        payload["parent_container_id"] = parent
    r = client.post("/api/devices", json=payload)
    assert r.status_code == 201, r.text
    if insertion is not None:
        # set insertion loss
        r2 = client.put(f"/api/devices/{id}", json={"insertion_loss_db": insertion})
        assert r2.status_code == 200


def _pm_id(code: str = "SMF_G652D") -> int:
    init_db()
    with get_session() as s:
        ensure_physical_media(s)
        s.commit()
        pm = s.exec(select(PhysicalMedium).where(PhysicalMedium.code == code)).first()
        assert pm is not None, "PhysicalMedium seeding missing"
        return int(pm.id)  # type: ignore[arg-type]


def _mk_link(a: str, b: str, length_km: float | None = None, fiber_type: str | None = None):
    lid = f"{a}__{b}"
    payload = {
        "id": lid,
        "a_interface_id": f"{a}-if0",
        "b_interface_id": f"{b}-if0",
        "kind": "FIBER",
        "status": "UP",
        "physical_medium_id": _pm_id("SMF_G652D"),
    }
    if length_km is not None:
        payload["length_km"] = float(length_km)
    r = client.post("/api/links", json=payload)
    assert r.status_code == 201, r.text


def test_simple_single_path():
    reset_db()
    _mk_dev("pop", "POP")
    _mk_dev("olt", "OLT", parent="pop")
    _mk_dev("odf", "ODF")
    _mk_dev("ont", "ONT")
    _mk_link("olt", "odf", length_km=5.0, fiber_type="SMF_G652D")
    _mk_link("odf", "ont", length_km=5.0, fiber_type="SMF_G652D")
    res = resolve_optical_path("ont")
    assert res is not None
    assert res.olt_id == "olt"
    # 10km total * 0.35 dB/km = 3.5 dB
    assert abs(res.total_attenuation_db - 3.5) < 1e-6
    assert len(res.segments) == 2


def test_lowest_attenuation_selected():
    reset_db()
    _mk_dev("pop", "POP")
    _mk_dev("olt", "OLT", parent="pop")
    _mk_dev("odf", "ODF")
    _mk_dev("ont", "ONT")
    # Under Phase 1 rules, ODF and ONT have a single upstream each. Validate attenuation math
    # on a single valid path: olt -> odf (1.1km) -> ont (0.0km)
    _mk_link("olt", "odf", length_km=1.1, fiber_type="SMF_G652D")  # 0.385 dB
    _mk_link("odf", "ont", length_km=0.0, fiber_type="SMF_G652D")  # 0 dB
    res = resolve_optical_path("ont")
    assert res is not None
    # Total = 0.385 + 0.0 = 0.385 dB
    assert res.olt_id == "olt"
    assert abs(res.total_attenuation_db - 0.385) < 1e-6


def test_tie_breaking():
    reset_db()
    _mk_dev("pop", "POP")
    _mk_dev("oltA", "OLT", parent="pop")
    _mk_dev("odf", "ODF")
    _mk_dev("ont", "ONT")
    # Single valid path; ensure resolver returns the connected OLT deterministically
    _mk_link("oltA", "odf", length_km=1.0, fiber_type="SMF_G652D")
    _mk_link("odf", "ont", length_km=1.0, fiber_type="SMF_G652D")
    res = resolve_optical_path("ont")
    assert res is not None
    assert res.olt_id == "oltA"


def test_no_path_returns_none():
    reset_db()
    _mk_dev("pop", "POP")
    _mk_dev("olt", "OLT", parent="pop")
    _mk_dev("ont", "ONT")
    # no links created
    res = resolve_optical_path("ont")
    assert res is None
