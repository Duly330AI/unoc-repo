from __future__ import annotations

from backend.core.jobs import InMemoryJobQueue, Job
from backend.services.worker import Worker


def test_queue_fifo_and_microbatch_selection():
    q = InMemoryJobQueue()
    j1 = Job.new("1", kind="test", payload={"i": 1})
    j2 = Job.new("2", kind="test", payload={"i": 2})
    j3 = Job.new("3", kind="test", payload={"i": 3})
    q.enqueue(j1)
    q.enqueue(j2)
    q.enqueue(j3)

    # First microbatch takes first two jobs deterministically
    b1 = q.next_microbatch(max_items=2)
    assert [j.id for j in b1] == ["1", "2"]
    assert q.size() == 1

    # Second microbatch takes the remaining one
    b2 = q.next_microbatch(max_items=2)
    assert [j.id for j in b2] == ["3"]
    assert q.size() == 0


def test_worker_run_once_invokes_handler_with_batch():
    q = InMemoryJobQueue()
    for i in range(5):
        q.enqueue(Job.new(str(i), kind="t", payload={"i": i}))

    seen: list[str] = []

    def handler(batch: list[Job]) -> None:
        seen.extend(j.id for j in batch)

    w = Worker()
    n = w.run_once(q, handler, max_items=3)
    assert n == 3
    assert seen == ["0", "1", "2"]
    assert q.size() == 2

    n2 = w.run_once(q, handler, max_items=3)
    assert n2 == 2
    assert seen == ["0", "1", "2", "3", "4"]
    assert q.size() == 0
