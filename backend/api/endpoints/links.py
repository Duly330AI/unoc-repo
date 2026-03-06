from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Response

from backend.api.endpoints.links_helpers import create_link_impl, get_link_impl, update_link_impl
from backend.api.endpoints.links_helpers_ips import get_link_ips_impl
from backend.api.endpoints.links_helpers_query import get_links_json_cached, list_links_impl
from backend.api.schemas import (
    BatchCreateLinksResponse,
    BatchLinkCreateRequest,
    LinkCreate,
    LinkResolvedOut,
    LinkUpdate,
)
from backend.clients.go_services.batch_client import get_batch_client
from backend.db import get_session, init_db
from backend.services.job_dispatcher import enqueue

router = APIRouter(tags=["links"], prefix="/links")


def _create_link_impl(payload: LinkCreate, background: BackgroundTasks | None) -> LinkResolvedOut:
    # Delegate to helpers to keep this module lean (compat wrapper kept for tests)
    return create_link_impl(payload, background)


@router.post("", response_model=LinkResolvedOut, status_code=201)
def create_link_endpoint(payload: LinkCreate, background: BackgroundTasks):
    """FastAPI route function for creating links synchronously.

    Rationale: Even when async writes are enabled for mutations like overrides, link creation
    is kept synchronous to allow tests and callers to immediately build a topology before
    issuing further operations (e.g., async overrides) within the same request flow.
    """
    return _create_link_impl(payload, background)


def create_link(payload: LinkCreate, background: BackgroundTasks | None = None) -> LinkResolvedOut:
    """Helper used by tests to create a link.

    If `background` is provided, heavy recompute will be scheduled on it.
    Otherwise, recompute runs inline to preserve event semantics expected by tests.
    """
    return _create_link_impl(payload, background)


@router.delete("/{link_id}")
def delete_link(link_id: str):
    """Always enqueue link delete and return 202 Accepted.

    POST create remains synchronous; delete is now permanently async to keep
    request paths deterministic and fast.
    """
    job = enqueue("link.delete", {"link_id": link_id})
    return Response(
        status_code=202,
        media_type="application/json",
        content=('{"accepted": true, "job_id": ' + f'"{job.id}"' + "}"),
    )


@router.get("", response_model=list[LinkResolvedOut])
def http_list_links(if_none_match: str | None = Header(default=None, alias="If-None-Match")):
    """HTTP route that serves cached JSON with ETag handling.

    Note: For unit tests that import and call `list_links()` directly, use the
    helper alias defined below which returns a list of LinkResolvedOut objects.
    """
    json_bytes, etag = get_links_json_cached()
    if if_none_match and if_none_match == etag:
        return Response(status_code=304)
    return Response(content=json_bytes, media_type="application/json", headers={"ETag": etag})


# Preserve historical import surface for tests: list_links() returns objects
def list_links() -> list[LinkResolvedOut]:  # type: ignore[override]
    return list_links_impl()


@router.get("/{link_id}", response_model=LinkResolvedOut)
def get_link(link_id: str) -> LinkResolvedOut:  # lightweight single lookup for tests/UI
    """Return a single link with resolved effective_status.

    Fast path: does not perform full reclassification (rule_id omitted) to keep
    latency low; mirrors list_links shape. If richer classification data is
    required later we can add an expanded=1 param. Deterministic: no background
    side-effects triggered here.
    """
    return get_link_impl(link_id)


@router.get("/{link_id}/ips", response_model=dict)
def get_link_ips(link_id: str):
    """Get IP addresses on both endpoints of a link.

    Returns IPs from both interfaces and detects common subnet if present.
    Useful for validating connectivity and IP addressing schemes.
    """
    init_db()
    with get_session() as s:
        try:
            return get_link_ips_impl(s, link_id)
        except LookupError:
            raise HTTPException(status_code=404, detail="Not found") from None


@router.patch("/{link_id}/override")
def set_link_override(link_id: str, body: dict):  # type: ignore[no-untyped-def]
    """Set or clear admin override status for a link (always async).

    Body: { admin_override_status: "DOWN" | null }

    Enqueues a job and returns 202 with a job id; caller should poll or wait
    for the worker to process to observe effects.
    """
    job = enqueue("link.override", {"link_id": link_id, "body": body})
    return Response(
        status_code=202,
        media_type="application/json",
        content=('{"accepted": true, "job_id": ' + f'"{job.id}"' + "}"),
    )


@router.put("/{link_id}", response_model=LinkResolvedOut)
def update_link(link_id: str, payload: LinkUpdate) -> LinkResolvedOut:
    return update_link_impl(link_id, payload)


# ---- Batch Operations (Week 3 Day 14) ----


@router.post("/batch", response_model=BatchCreateLinksResponse, status_code=201)
def batch_create_links_endpoint(payload: BatchLinkCreateRequest) -> BatchCreateLinksResponse:
    """Batch create multiple links via Go service with Python fallback.

    Week 3 Day 14: Python → Go gRPC integration. Go service performs bulk operations
    in a single transaction with parallel validation. Python fallback (stub) used
    when Go service unavailable.

    Performance target: 64 links in <10s (Go) vs 37 min (Python one-by-one).

    Request body:
    {
      "links": [
        {
          "a_interface_id": 1,
          "b_interface_id": 2,
          "length_km": 5.0,
          "status": "active",
          "metadata": {"fiber_type": "SM"}
        },
        ...
      ],
      "dry_run": false,
      "skip_optical_recompute": false,
      "request_id": "optional-correlation-id"
    }

    Response:
    {
      "created_link_ids": [101, 102, ...],
      "failed_links": [
        {
          "index": 3,
          "a_interface_id": 7,
          "b_interface_id": 8,
          "error_code": "INTERFACE_NOT_FOUND",
          "error_message": "Interface 7 not found"
        },
        ...
      ],
      "total_requested": 64,
      "total_created": 63,
      "duration_ms": 8420,
      "request_id": "optional-correlation-id",
      "backend": "go"  // "go" or "python"
    }

    Error codes:
    - INTERFACE_NOT_FOUND: Interface doesn't exist
    - INTERFACE_ALREADY_LINKED: Interface already in a link
    - INTERFACE_SAME_DEVICE: Both interfaces on same device
    - TRANSACTION_FAILED: Database transaction error
    """
    # Get batch client (connects to Go service on port 50052)
    client = get_batch_client()

    # Convert Pydantic models to dicts for gRPC client
    links_data = [link.model_dump() for link in payload.links]

    # Call Go service (or Python fallback on error)
    result = client.batch_create_links(
        links=links_data,
        dry_run=payload.dry_run,
        skip_optical_recompute=payload.skip_optical_recompute,
        request_id=payload.request_id,
    )

    # Result is already a dict with correct structure (from batch_client)
    return BatchCreateLinksResponse(**result)
