from __future__ import annotations

import ipaddress

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import VRF, Prefix

router = APIRouter(tags=["ipam"], prefix="/ipam")


# ---- VRFs ----


@router.get("/vrfs", response_model=list[dict])
def list_vrfs():
    init_db()
    with get_session() as s:
        rows = s.exec(select(VRF)).all()
        return [{"id": v.id, "name": v.name} for v in rows]


@router.post("/vrfs", status_code=201, response_model=dict)
def create_vrf(payload: dict):
    init_db()
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    with get_session() as s:
        exists = s.exec(select(VRF).where(VRF.name == name)).first()
        if exists:
            raise HTTPException(status_code=409, detail="VRF already exists")
        v = VRF(name=name)
        s.add(v)
        s.commit()
        s.refresh(v)
        return {"id": v.id, "name": v.name}


@router.delete("/vrfs/{vrf_id}", status_code=204)
def delete_vrf(vrf_id: int):
    init_db()
    with get_session() as s:
        v = s.get(VRF, vrf_id)
        if not v:
            raise HTTPException(status_code=404, detail="Not found")
        s.delete(v)
        s.commit()
        return None


# ---- Prefixes ----


@router.get("/prefixes", response_model=list[dict])
def list_prefixes(vrf_id: int | None = None):
    init_db()
    with get_session() as s:
        q = select(Prefix)
        if vrf_id is not None:
            q = q.where(Prefix.vrf_id == vrf_id)
        rows = s.exec(q).all()
        return [
            {"id": p.id, "prefix": p.prefix, "vrf_id": p.vrf_id, "description": p.description}
            for p in rows
        ]


@router.post("/prefixes", status_code=201, response_model=dict)
def create_prefix(payload: dict):
    init_db()
    prefix = payload.get("prefix")
    vrf_id = payload.get("vrf_id")
    description = payload.get("description")
    if not prefix or vrf_id is None:
        raise HTTPException(status_code=422, detail="prefix and vrf_id are required")
    # Validate CIDR
    try:
        ipnet = ipaddress.ip_network(prefix)
        if ipnet.version != 4:
            raise ValueError("IPv4 only for now")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid prefix") from exc
    with get_session() as s:
        v = s.get(VRF, int(vrf_id))
        if not v:
            raise HTTPException(status_code=404, detail="VRF not found")
        exists = s.exec(
            select(Prefix).where(Prefix.vrf_id == int(vrf_id), Prefix.prefix == str(ipnet))
        ).first()
        if exists:
            raise HTTPException(status_code=409, detail="Prefix already exists in VRF")
        p = Prefix(prefix=str(ipnet), vrf_id=int(vrf_id), description=description)
        s.add(p)
        s.commit()
        s.refresh(p)
        return {"id": p.id, "prefix": p.prefix, "vrf_id": p.vrf_id, "description": p.description}


@router.delete("/prefixes/{prefix_id}", status_code=204)
def delete_prefix(prefix_id: int):
    init_db()
    with get_session() as s:
        p = s.get(Prefix, prefix_id)
        if not p:
            raise HTTPException(status_code=404, detail="Not found")
        s.delete(p)
        s.commit()
        return None


__all__ = ["router"]
