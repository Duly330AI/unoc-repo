from fastapi import APIRouter
from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, Link
from backend.services.pathfinding import (
    PATHFINDING_STORE,
    DeviceRecord,
    LinkRecord,
    build_logical_graph,
    build_optical_graph,
)

router = APIRouter(tags=["topology"], prefix="/topology")


@router.get("/version")
def get_topology_version():
    """Return current topology version and basic node/edge counts."""
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
    version = PATHFINDING_STORE.version()
    # Build graphs directly from current snapshot to avoid any cached state affecting counts
    og = build_optical_graph(d_recs, l_recs)
    lg = build_logical_graph(d_recs, l_recs, relaxed=False)
    return {
        "version": version,
        "optical": {"nodes": og.number_of_nodes(), "edges": og.number_of_edges()},
        "logical": {"nodes": lg.number_of_nodes(), "edges": lg.number_of_edges()},
    }
