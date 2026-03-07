from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.db import get_session, init_db
from backend.link_rules import allowed_media_codes_for_class, classify_link
from backend.models import Device, Interface, Link, PhysicalMedium

router = APIRouter(tags=["physical"], prefix="/physical")


@router.get("/allowed-media/by-link/{link_id}", response_model=list[dict])
def get_allowed_media_by_link(link_id: str):
    init_db()
    with get_session() as s:
        ln = s.get(Link, link_id)
        if not ln:
            raise HTTPException(status_code=404, detail="Link not found")
        a_if = s.get(Interface, ln.a_interface_id)
        b_if = s.get(Interface, ln.b_interface_id)
        if not a_if or not b_if:
            raise HTTPException(status_code=400, detail="Link interfaces missing")
        a_dev = s.get(Device, a_if.device_id)
        b_dev = s.get(Device, b_if.device_id)
        if not a_dev or not b_dev:
            raise HTTPException(status_code=400, detail="Link device endpoints missing")
        cls = classify_link(a_dev, b_dev)
        codes = allowed_media_codes_for_class(cls.link_class)
        if not codes:
            return []
        rows = [pm for pm in s.exec(select(PhysicalMedium)).all() if pm.code in codes]
        return [
            {
                "id": pm.id,
                "code": pm.code,
                "name": pm.name,
                "kind": pm.kind,
                "max_range_km": pm.max_range_km,
            }
            for pm in rows
        ]
