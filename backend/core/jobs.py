from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Job:
    id: str
    kind: str
    payload: dict
    created_at: datetime

    @staticmethod
    def new(id: str, kind: str, payload: dict | None = None) -> Job:
        return Job(
            id=id,
            kind=kind,
            payload=payload or {},
            created_at=datetime.now(UTC),
        )


class InMemoryJobQueue:
    """Deterministic FIFO in-memory queue with microbatch selection.

    - Stable order: FIFO by enqueue sequence
    - Deterministic microbatch: take items in order up to max_items; we do not use time for tests
    """

    def __init__(self) -> None:
        self._q: list[Job] = []

    def enqueue(self, job: Job) -> None:
        # Append to the end; duplicates allowed, coalescing is deferred to a later iteration
        self._q.append(job)

    def size(self) -> int:
        return len(self._q)

    def next_microbatch(self, max_items: int = 256, budget_ms: int = 50) -> list[Job]:
        # Deterministic selection: ignore budget_ms in this minimal skeleton; just slice by max_items
        if max_items <= 0:
            return []
        batch = self._q[:max_items]
        # Remove taken jobs
        self._q = self._q[len(batch) :]
        return batch
