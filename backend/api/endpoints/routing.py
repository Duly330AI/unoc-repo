from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import VRF, Device, Interface, Route
from backend.services import recompute_coalescer
from backend.services.pathfinding import PATHFINDING_STORE

router = APIRouter(tags=["routing"], prefix="/devices")


class RouteIn(BaseModel):
    vrf_id: int
    prefix: str
    next_hop: str | None = None
    interface_id: str | None = None
    admin_distance: int = Field(default=1, ge=1)
    metric: int = Field(default=0, ge=0)


class RouteOut(BaseModel):
    id: int
    vrf_id: int
    prefix: str
    next_hop: str | None
    interface_id: str | None
    admin_distance: int
    metric: int

    @classmethod
    def from_model(cls, r: Route) -> RouteOut:
        return cls(
            id=r.id,  # type: ignore[arg-type]
            vrf_id=r.vrf_id,
            prefix=r.prefix,
            next_hop=r.next_hop,
            interface_id=r.interface_id,
            admin_distance=r.admin_distance,
            metric=r.metric,
        )


@router.post("/{device_id}/routing/vrfs/{vrf_id}/routes", response_model=RouteOut, status_code=201)
def add_static_route(device_id: str, vrf_id: int, payload: RouteIn):
    """Add a static route into the device's VRF RIB.

    Note: For this phase, we just persist a Route row keyed by vrf_id.
    Device linkage is implicit by VRF assignment on the Device record.
    """
    init_db()
    if payload.vrf_id != vrf_id:
        raise HTTPException(status_code=400, detail="VRF_ID_MISMATCH")
    with get_session() as s:
        d = s.get(Device, device_id)
        if not d:
            raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
        vrf = s.get(VRF, vrf_id)
        if not vrf:
            raise HTTPException(status_code=404, detail="VRF_NOT_FOUND")
        # If interface is provided, ensure it exists and belongs to the device
        if payload.interface_id:
            i = s.get(Interface, payload.interface_id)
            if not i:
                raise HTTPException(status_code=404, detail="INTERFACE_NOT_FOUND")
            if i.device_id != device_id:
                raise HTTPException(status_code=400, detail="INTERFACE_NOT_ON_DEVICE")
        # For default route, require explicit next_hop and interface_id
        if payload.prefix == "0.0.0.0/0":
            if not payload.next_hop:
                raise HTTPException(status_code=400, detail="DEFAULT_ROUTE_REQUIRES_NEXT_HOP")
            if not payload.interface_id:
                raise HTTPException(status_code=400, detail="DEFAULT_ROUTE_REQUIRES_INTERFACE")
        # For now, allow routes regardless of device.vrf_id; multiple VRFs can exist per system.
        r = Route(
            vrf_id=vrf_id,
            prefix=payload.prefix,
            next_hop=payload.next_hop,
            interface_id=payload.interface_id,
            admin_distance=payload.admin_distance,
            metric=payload.metric,
        )
        s.add(r)
        try:
            s.commit()
        except Exception as e:  # pragma: no cover (unique constraint detail may vary)
            s.rollback()
            raise HTTPException(status_code=409, detail="ROUTE_ALREADY_EXISTS") from e
        s.refresh(r)
        # Topology-affecting for L3 visibility: bump version and schedule status recompute
        PATHFINDING_STORE.bump_version()
        recompute_coalescer.schedule(scope="routing", key=str(vrf_id))
        return RouteOut.from_model(r)


@router.get("/{device_id}/routing/vrfs/{vrf_id}/routes", response_model=list[RouteOut])
def list_routes(device_id: str, vrf_id: int):
    """List the static routes (RIB) for a VRF."""
    init_db()
    with get_session() as s:
        d = s.get(Device, device_id)
        if not d:
            raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
        vrf = s.get(VRF, vrf_id)
        if not vrf:
            raise HTTPException(status_code=404, detail="VRF_NOT_FOUND")
        routes = s.exec(select(Route).where(Route.vrf_id == vrf_id)).all()
        return [RouteOut.from_model(r) for r in routes]


@router.delete(
    "/{device_id}/routing/vrfs/{vrf_id}/routes/{route_id}",
    status_code=204,
)
def delete_static_route(device_id: str, vrf_id: int, route_id: int):
    """Delete a static route from the device's VRF RIB."""
    init_db()
    with get_session() as s:
        d = s.get(Device, device_id)
        if not d:
            raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
        vrf = s.get(VRF, vrf_id)
        if not vrf:
            raise HTTPException(status_code=404, detail="VRF_NOT_FOUND")
        r = s.get(Route, route_id)
        if not r or r.vrf_id != vrf_id:
            raise HTTPException(status_code=404, detail="ROUTE_NOT_FOUND")
        s.delete(r)
        s.commit()
        PATHFINDING_STORE.bump_version()
        recompute_coalescer.schedule(scope="routing", key=str(vrf_id))
        return None
