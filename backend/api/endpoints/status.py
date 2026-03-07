"""Status propagation API endpoint.

Provides REST API for triggering status propagation across network topology.

Endpoints:
- POST /api/status/propagate: Trigger causal chain propagation

Performance:
- Go service (if available): ~66μs for 200 devices
- Python fallback: ~2000ms for 200 devices

The endpoint automatically uses Go service if available, falls back to Python.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.clients.go_services.status_client import get_status_client

router = APIRouter()


# Request/Response Models


class StatusPropagateRequest(BaseModel):
    """Request model for status propagation."""

    changed_device_ids: list[str] = Field(
        description="List of device IDs that changed status",
        examples=[["device-1", "device-2"]],
    )
    changed_link_ids: list[str] | None = Field(
        default=None,
        description="Optional list of link IDs that changed status",
        examples=[["link-1", "link-2"]],
    )
    update_database: bool = Field(
        default=True,
        description="Whether to update device statuses in database",
    )


class StatusPropagateResponse(BaseModel):
    """Response model for status propagation."""

    affected_devices: list[str] = Field(description="List of device IDs affected by propagation")
    affected_links: list[str] = Field(
        default=[],
        description="List of link IDs affected by propagation (future use)",
    )
    duration_ms: float = Field(description="Duration of propagation in milliseconds")
    source: str = Field(
        description="Source of propagation (go or python)",
        examples=["go", "python"],
    )
    dependency_paths: dict[str, list[str]] | None = Field(
        default=None,
        description="Dependency paths for affected devices (optional)",
    )


class StatusHealthResponse(BaseModel):
    """Response model for status service health check."""

    status: str = Field(description="Health status", examples=["UP", "HEALTHY", "UNHEALTHY"])
    backend: str = Field(description="Backend type", examples=["go", "python"])
    message: str | None = Field(default=None, description="Health message")
    version: str | None = Field(default=None, description="Service version (if Go)")


# Endpoints


@router.post(
    "/propagate",
    response_model=StatusPropagateResponse,
    status_code=status.HTTP_200_OK,
    summary="Propagate status changes across topology",
    description="""
    Trigger causal chain propagation for changed devices/links.
    
    The endpoint automatically uses the Go Status Propagation Service if available
    (66μs for 200 devices), falling back to Python implementation if Go unavailable
    (2000ms for 200 devices).
    
    **Propagation Logic:**
    - Builds dependency graph from device links
    - BFS traversal from changed devices
    - Recomputes status for affected devices
    - Optionally updates database (if update_database=True)
    
    **Returns:**
    - List of affected device IDs
    - Duration in milliseconds
    - Source backend (go or python)
    - Optional dependency paths
    """,
    responses={
        200: {
            "description": "Status propagation successful",
            "content": {
                "application/json": {
                    "example": {
                        "affected_devices": ["device-1", "device-2", "device-3"],
                        "affected_links": [],
                        "duration_ms": 0.15,
                        "source": "go",
                        "dependency_paths": {
                            "device-1": ["device-1"],
                            "device-2": ["device-1", "device-2"],
                            "device-3": ["device-1", "device-2", "device-3"],
                        },
                    }
                }
            },
        },
        503: {
            "description": "Service unavailable (both Go and Python failed)",
            "content": {
                "application/json": {
                    "example": {"detail": "Status propagation service unavailable: <error message>"}
                }
            },
        },
    },
)
async def propagate_status(request: StatusPropagateRequest) -> StatusPropagateResponse:
    """
    Propagate status changes across network topology.

    Args:
        request: Status propagation request with changed device/link IDs

    Returns:
        StatusPropagateResponse with affected devices and metadata

    Raises:
        HTTPException(503): If both Go and Python propagation fail
    """
    client = get_status_client()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Status propagation service unavailable: client initialization failed",
        )

    try:
        result = client.propagate_status(
            changed_device_ids=request.changed_device_ids,
            changed_link_ids=request.changed_link_ids or [],
            update_database=request.update_database,
        )

        return StatusPropagateResponse(
            affected_devices=result.get("affected_devices", []),
            affected_links=result.get("affected_links", []),
            duration_ms=result.get("duration_ms", 0.0),
            source=result.get("source", "unknown"),
            dependency_paths=result.get("dependency_paths"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Status propagation failed: {str(e)}",
        ) from e


@router.get(
    "/health",
    response_model=StatusHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check status service health",
    description="""
    Check health of Status Propagation Service.
    
    Returns information about:
    - Service status (UP/HEALTHY/UNHEALTHY)
    - Backend type (go or python)
    - Service version (if Go backend)
    - Health message (if any issues)
    """,
)
async def get_status_health() -> StatusHealthResponse:
    """
    Check status service health.

    Returns:
        StatusHealthResponse with service health info
    """
    client = get_status_client()

    if not client:
        return StatusHealthResponse(
            status="UNHEALTHY",
            backend="python",
            message="Status client not initialized",
        )

    health = client.health()

    return StatusHealthResponse(
        status=health.get("status", "UNKNOWN"),
        backend=health.get("backend", "unknown"),
        message=health.get("message"),
        version=health.get("version"),
    )
