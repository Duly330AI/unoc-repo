from fastapi import APIRouter, Depends

from backend.api.deps import health_payload, metadata_payload
from backend.api.schemas import HealthResponse, MetadataResponse
from backend.events import get_event_counts

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def get_health(
    payload: HealthResponse = Depends(health_payload),  # noqa: B008
) -> HealthResponse:
    # FastAPI dependency injection uses Depends in parameter defaults by design.
    return payload


@router.get("/metadata", response_model=MetadataResponse)
async def get_metadata(
    payload: MetadataResponse = Depends(metadata_payload),  # noqa: B008
) -> MetadataResponse:
    # FastAPI dependency injection uses Depends in parameter defaults by design.
    return payload


@router.get("/metrics/events")
def get_event_metrics():
    return {"events": get_event_counts()}
