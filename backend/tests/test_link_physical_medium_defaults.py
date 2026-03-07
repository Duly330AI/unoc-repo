from __future__ import annotations

from fastapi.testclient import TestClient

from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, Status
from backend.services.seed_service import ensure_physical_media


def _mk_device(id: str, t: DeviceType, status: Status = Status.UP) -> None:
    with get_session() as s:
        s.add(Device(id=id, name=id, type=t, status=status))
        s.commit()


def _mk_if(id: str, dev: str, name: str | None = None) -> None:
    eff_name = name if name is not None else (id.split("-", 1)[-1] if "-" in id else id)
    with get_session() as s:
        s.add(Interface(id=id, device_id=dev, name=eff_name))
        s.commit()


def test_create_link_defaults_when_physical_medium_missing():
    init_db()
    with get_session() as s:
        ensure_physical_media(s)
        s.commit()

    client = TestClient(app)

    # Optical class endpoints (ODF-as-aggregator): OLT <-> ODF
    _mk_device("oltA", DeviceType.OLT)
    _mk_if("oltA-if0", "oltA")
    _mk_device("odfA", DeviceType.ODF)
    _mk_if("odfA-if0", "odfA")

    # Canonical link id uses device ids alpha order
    link_id = "odfA__oltA" if "odfA" < "oltA" else "oltA__odfA"

    # No physical_medium_id provided
    resp = client.post(
        "/api/links",
        json={
            "id": link_id,
            "a_interface_id": "oltA-if0",
            "b_interface_id": "odfA-if0",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # physical_medium_id should be set to an allowed default and length defaulted
    pm_id = body.get("physical_medium_id")
    assert isinstance(pm_id, int) and pm_id > 0
    assert isinstance(body.get("length_km"), int | float)
    assert 0.1 <= float(body["length_km"]) <= 2.1


def test_create_link_defaults_physical_medium_and_length_when_missing():
    init_db()
    with get_session() as s:
        ensure_physical_media(s)
        s.commit()

    client = TestClient(app)

    # Optical class endpoints (ODF-as-aggregator): OLT <-> ODF
    _mk_device("oltB", DeviceType.OLT)
    _mk_if("oltB-if0", "oltB")
    _mk_device("odfB", DeviceType.ODF)
    _mk_if("odfB-if0", "odfB")

    link_id = "odfB__oltB" if "odfB" < "oltB" else "oltB__odfB"

    # Provide neither fiber_type nor physical_medium_id
    resp = client.post(
        "/api/links",
        json={
            "id": link_id,
            "a_interface_id": "oltB-if0",
            "b_interface_id": "odfB-if0",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    pm_id = body.get("physical_medium_id")
    assert isinstance(pm_id, int) and pm_id > 0
    # Defaulted optical length range
    assert isinstance(body.get("length_km"), int | float)
    assert 0.1 <= float(body["length_km"]) <= 2.1

    # Determinism: creating the same link again should conflict (id), but the chosen PM would be the same if id-based
    with get_session() as s:
        ln = s.get(Link, link_id)
        assert ln is not None
        first_pm_id = int(ln.physical_medium_id or 0)
    # Delete and re-create to check deterministic PM selection for same id
    with get_session() as s:
        ln = s.get(Link, link_id)
        s.delete(ln)
        s.commit()
    resp2 = client.post(
        "/api/links",
        json={
            "id": link_id,
            "a_interface_id": "oltB-if0",
            "b_interface_id": "odfB-if0",
        },
    )
    assert resp2.status_code == 201
    body2 = resp2.json()
    assert int(body2.get("physical_medium_id") or 0) == first_pm_id
