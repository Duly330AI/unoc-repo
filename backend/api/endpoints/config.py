# ruff: noqa: I001
from fastapi import APIRouter

from backend.api.schemas import AppConfigResponse, MetricsConfig
from backend.constants.metrics import EPSILON_METRICS_DELTA, UTILIZATION_BUCKETS
from backend.core.config import get_settings

router = APIRouter(tags=["config"], prefix="/config")


@router.get("", response_model=AppConfigResponse)
def get_app_config() -> AppConfigResponse:  # type: ignore[override]
    settings = get_settings()
    return AppConfigResponse(
        metrics=MetricsConfig(
            EPSILON_METRICS_DELTA=EPSILON_METRICS_DELTA,
            UTILIZATION_BUCKETS=UTILIZATION_BUCKETS,
        ),
        flags={
            "CONTAINER_PROXY_LINKING": settings.container_proxy_linking,
        },
    )
