from __future__ import annotations

from itertools import count
from typing import Any

from fastapi import BackgroundTasks

from backend.api.endpoints.links_helpers_create import create_link_impl
from backend.api.endpoints.links_helpers_delete import delete_link_impl
from backend.api.endpoints.links_helpers_override import set_link_override_impl
from backend.api.schemas import LinkCreate
from backend.core.jobs import InMemoryJobQueue, Job

# Global, deterministic FIFO queue for async writes (phase 1 skeleton)
QUEUE = InMemoryJobQueue()
_COUNTER = count(1)


def _next_job_id(kind: str) -> str:
    """Return a stable, process-local increasing job id.

    Deterministic within a single process lifetime; no timestamp or randomness,
    to keep ordering stable in tests.
    """
    return f"{kind}:{next(_COUNTER)}"


def enqueue(kind: str, payload: dict[str, Any] | None = None) -> Job:
    """Create and enqueue a job of the given kind with optional payload.

    Returns the Job object for reference (e.g., job_id in 202 responses).
    """
    job = Job.new(id=_next_job_id(kind), kind=kind, payload=payload or {})
    QUEUE.enqueue(job)
    return job


def handle_batch(batch: list[Job]) -> None:
    """Process a microbatch deterministically.

    Current implementation handles link.override jobs by applying the override
    persistence and side-effects (events/recompute) using the existing helper.
    """
    for job in batch:
        try:
            if job.kind == "link.override":
                link_id = str(job.payload.get("link_id"))
                body = job.payload.get("body") or {}
                # Delegate to existing implementation to avoid duplicating logic
                set_link_override_impl(link_id, body)
            elif job.kind == "link.create":
                payload_dict = job.payload.get("payload") or {}
                # Re-hydrate Pydantic model to reuse the existing implementation
                payload = LinkCreate.model_validate(payload_dict)
                create_link_impl(payload, background=BackgroundTasks())
            elif job.kind == "link.delete":
                link_id = str(job.payload.get("link_id"))
                delete_link_impl(link_id)
            else:
                # Unknown kinds are ignored (forward-compat), no-op
                pass
        except Exception:
            # Swallow to keep batch processing deterministic; future iterations can log/metrics
            continue


__all__ = ["QUEUE", "enqueue", "handle_batch"]
