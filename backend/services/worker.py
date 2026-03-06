from __future__ import annotations

from collections.abc import Callable

from backend.core.jobs import InMemoryJobQueue, Job


class Worker:
    """Minimal single-threaded worker skeleton.

    run_once pulls a microbatch from the queue and invokes the provided handler.
    The handler receives the batch (possibly empty) and returns None.
    """

    def run_once(
        self,
        queue: InMemoryJobQueue,
        handler: Callable[[list[Job]], None],
        *,
        max_items: int = 256,
        budget_ms: int = 50,
    ) -> int:
        batch: list[Job] = queue.next_microbatch(max_items=max_items, budget_ms=budget_ms)
        if not batch:
            return 0
        handler(batch)
        return len(batch)
