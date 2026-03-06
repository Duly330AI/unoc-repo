from fastapi import APIRouter

from backend.api.schemas import LayoutPositionsPatchRequest, LayoutPositionsPatchResponse
from backend.services.layout_state import LayoutPosition, db_patch, db_snapshot

router = APIRouter(tags=["layout"], prefix="/layout")


@router.patch("/positions", response_model=LayoutPositionsPatchResponse)
async def patch_layout_positions(
    req: LayoutPositionsPatchRequest,
) -> LayoutPositionsPatchResponse:
    applied = 0
    items: list[LayoutPosition] = []
    for p in req.positions:
        items.append(
            LayoutPosition(
                id=p.id,
                x=p.x,
                y=p.y,
                userPinned=p.userPinned,
                systemPinned=p.systemPinned,
            )
        )
    if items:
        version = db_patch(items)
        applied = len(items)
    else:
        version, _ = db_snapshot()
    return LayoutPositionsPatchResponse(version=version, applied=applied)


@router.get("/positions")
async def get_layout_positions():  # lightweight shape
    version, items = db_snapshot()
    return {"version": version, "positions": [p.__dict__ for p in items]}
