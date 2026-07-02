from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Response

from backend.api.endpoints.links_helpers import create_link_impl, get_link_impl, update_link_impl
from backend.api.endpoints.links_helpers_ips import get_link_ips_impl
from backend.api.endpoints.links_helpers_query import get_links_json_cached, list_links_impl
from backend.api.schemas import (
    LinkCreate,
    LinkResolvedOut,
    LinkUpdate,
)
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


# ---- Batch Operations ----
#
# POST /links/batch is served by backend.api.endpoints.links_batch (Python,
# event-first, projection-guarded). The former Go-client route was removed:
# the Go batch-service INSERTed link rows directly into the database, which
# would bypass the EventStore. No frontend or test caller used the Go route.
