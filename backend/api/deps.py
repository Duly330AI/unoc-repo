"""Common dependency callables for FastAPI routes."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.core.config import get_settings

from .schemas import HealthResponse, MetadataResponse


def health_payload() -> HealthResponse:
    return HealthResponse(status="ok")


def metadata_payload() -> MetadataResponse:
    s = get_settings()
    return MetadataResponse(
        app=s.app_name,
        version="0.0.0",  # placeholder until semver
        specRevision="r4",
        debug=s.debug,
        timestamp=datetime.now(UTC).isoformat(),
    )
