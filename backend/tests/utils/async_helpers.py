import asyncio

from backend.services import recompute_coalescer as coalescer


async def wait_for_coalescer_idle(timeout_s: float = 3.0, poll_ms: int = 10) -> None:
    """Await until the recompute coalescer reports idle or timeout expires.

    Args:
        timeout_s: Maximum time to wait before raising TimeoutError.
        poll_ms: Polling interval in milliseconds.
    """
    deadline = asyncio.get_event_loop().time() + timeout_s
    interval = max(poll_ms, 1) / 1000.0
    while True:
        if coalescer.is_idle():
            return
        if asyncio.get_event_loop().time() >= deadline:
            raise TimeoutError("Timed out waiting for coalescer to become idle")
        await asyncio.sleep(interval)
