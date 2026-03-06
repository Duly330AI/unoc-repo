from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from backend.api.schemas import (
    PingRequest,
    PingResponse,
    TracerouteHop,
    TracerouteRequest,
    TracerouteResponse,
)
from backend.db import get_session, init_db
from backend.models import Device, Link
from backend.services.pathfinding import PATHFINDING_STORE, DeviceRecord, LinkRecord

router = APIRouter(tags=["tools"], prefix="/tools")


def _device_exists(device_id: str) -> bool:
    with get_session() as s:
        return s.get(Device, device_id) is not None


def _shortest_logical_path(src_id: str, dst_id: str) -> list[str] | None:
    """Return a plausible device-id path using the logical graph if available.

    This is a deterministic skeleton: uses current devices/links snapshot and an
    unweighted shortest path on the logical graph. Returns None if either node
    is missing or path not found.
    """
    init_db()
    with get_session() as s:
        devices = s.exec(select(Device)).all()
        links = s.exec(select(Link)).all()
    d_recs = [DeviceRecord(id=d.id, type=d.type) for d in devices]
    l_recs = [
        LinkRecord(
            id=link.id,
            a_device_id=(
                link.a_interface_id[:-4]
                if link.a_interface_id.endswith("-if0")
                else link.a_interface_id
            ),
            b_device_id=(
                link.b_interface_id[:-4]
                if link.b_interface_id.endswith("-if0")
                else link.b_interface_id
            ),
            kind=link.kind,
        )
        for link in links
    ]
    _, lg = PATHFINDING_STORE.get_logical_graph(d_recs, l_recs, relaxed=False)
    if src_id not in lg or dst_id not in lg:
        return None
    try:
        import networkx as nx

        return nx.shortest_path(lg, source=src_id, target=dst_id)
    except Exception:
        return None


@router.post("/ping", response_model=PingResponse)
def post_ping(payload: PingRequest) -> PingResponse:  # type: ignore[override]
    src = payload.source_device_id
    dst = payload.target_device_id or payload.target_ip or ""
    if not src or not dst:
        raise HTTPException(status_code=422, detail="INVALID_REQUEST")
    if not _device_exists(src):
        raise HTTPException(status_code=404, detail="source device not found")
    # Minimal behavior: if target_device_id provided and exists, compute path; else unreachable
    target_id: str | None = payload.target_device_id
    if target_id and not _device_exists(target_id):
        raise HTTPException(status_code=404, detail="target device not found")

    hops: list[str] = []
    outcome = "unreachable"
    if target_id:
        path = _shortest_logical_path(src, target_id)
        if path:
            hops = path
            outcome = "success"
    # rtt_ms intentionally None in skeleton
    return PingResponse(outcome=outcome, hops=hops, rtt_ms=None)


@router.post("/traceroute", response_model=TracerouteResponse)
def post_traceroute(payload: TracerouteRequest) -> TracerouteResponse:  # type: ignore[override]
    src = payload.source_device_id
    dst = payload.target_device_id or payload.target_ip or ""
    if not src or not dst:
        raise HTTPException(status_code=422, detail="INVALID_REQUEST")
    if not _device_exists(src):
        raise HTTPException(status_code=404, detail="source device not found")
    target_id: str | None = payload.target_device_id
    if target_id and not _device_exists(target_id):
        raise HTTPException(status_code=404, detail="target device not found")

    hops: list[TracerouteHop] = []
    outcome = "unreachable"
    final: str | None = None
    if target_id:
        path = _shortest_logical_path(src, target_id)
        if path:
            limited = path[: max(1, int(payload.max_hops))]
            hops = [
                TracerouteHop(hop=i + 1, device_id=dev_id, rtt_ms=None, success=True)
                for i, dev_id in enumerate(limited)
            ]
            final = limited[-1]
            outcome = "reached" if final == target_id else "ttl_exceeded"
    return TracerouteResponse(outcome=outcome, hops=hops, final_device_id=final)
