from sqlmodel import Session

from backend.api.endpoints.links import create_link
from backend.api.endpoints.physical import get_allowed_media_by_link
from backend.api.schemas import LinkCreate
from backend.db import engine, init_db, reset_db
from backend.models import Device, DeviceType, Interface
from backend.services.seed_service import ensure_physical_media


def setup_function(_: object):
    reset_db()
    init_db()
    # Ensure PhysicalMedium rows exist for lookups
    with Session(engine) as s:
        ensure_physical_media(s)
        s.commit()


def _add_dev(session: Session, did: str, dtype: DeviceType) -> None:
    d = Device(id=did, name=did, type=dtype)
    session.add(d)
    session.add(Interface(id=f"{did}-if0", device_id=did, name="if0"))


def _payload(a: str, b: str) -> LinkCreate:
    ordered = sorted([a, b])
    lid = f"{ordered[0]}__{ordered[1]}"
    return LinkCreate(id=lid, a_interface_id=f"{a}-if0", b_interface_id=f"{b}-if0")


def test_allowed_media_core_edge_router_router_smf_only():
    with Session(engine) as s:
        _add_dev(s, "core1", DeviceType.CORE_ROUTER)
        _add_dev(s, "edge1", DeviceType.EDGE_ROUTER)
        s.commit()
    lr = create_link(_payload("core1", "edge1"))
    rows = get_allowed_media_by_link(lr.id)
    codes = {r["code"] for r in rows}
    assert codes.issuperset({"SMF_G652D", "SMF_G657A1", "SMF_G657A2"})
    # No copper on routed_p2p
    assert "CAT6A_UTP" not in codes


def test_allowed_media_olt_edge_smf_only():
    with Session(engine) as s:
        _add_dev(s, "olt1", DeviceType.OLT)
        _add_dev(s, "edge1", DeviceType.EDGE_ROUTER)
        s.commit()
    lr = create_link(_payload("olt1", "edge1"))
    rows = get_allowed_media_by_link(lr.id)
    codes = {r["code"] for r in rows}
    assert codes.issuperset({"SMF_G652D", "SMF_G657A1", "SMF_G657A2"})
    assert "CAT6A_UTP" not in codes
