from __future__ import annotations

import threading
import time
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any


@dataclass
class Histogram:
    count: int = 0
    total: float = 0.0
    min: float | None = None
    max: float | None = None

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        if self.min is None or value < self.min:
            self.min = value
        if self.max is None or value > self.max:
            self.max = value

    def snapshot(self) -> dict[str, Any]:
        avg = (self.total / self.count) if self.count else 0.0
        return {
            "count": self.count,
            "avg_ms": avg * 1000.0,
            "min_ms": (self.min or 0.0) * 1000.0,
            "max_ms": (self.max or 0.0) * 1000.0,
        }


@dataclass
class Counter:
    value: int = 0

    def inc(self, n: int = 1) -> None:
        self.value += int(n)

    def snapshot(self) -> int:
        return self.value


@dataclass
class Gauge:
    value: float = 0.0

    def set(self, v: float) -> None:
        self.value = float(v)

    def snapshot(self) -> float:
        return self.value


class ObservabilityRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.histograms: dict[str, Histogram] = defaultdict(Histogram)
        self.counters: dict[str, Counter] = defaultdict(Counter)
        self.gauges: dict[str, Gauge] = defaultdict(Gauge)

    def observe(self, key: str, seconds: float) -> None:
        with self._lock:
            self.histograms[key].observe(seconds)

    def inc(self, key: str, n: int = 1) -> None:
        with self._lock:
            self.counters[key].inc(n)

    def set(self, key: str, v: float) -> None:
        with self._lock:
            self.gauges[key].set(v)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": {k: v.snapshot() for k, v in self.counters.items()},
                "gauges": {k: v.snapshot() for k, v in self.gauges.items()},
                "histograms": {k: v.snapshot() for k, v in self.histograms.items()},
            }

    def time_block(self, key: str):  # context manager
        registry = self

        class _CM:
            def __enter__(self):
                self.t0 = time.perf_counter()
                return self

            def __exit__(self, exc_type, exc, tb):
                t1 = time.perf_counter()
                registry.observe(key, t1 - self.t0)
                return False

        return _CM()


OBS = ObservabilityRegistry()

# Metric keys (namespaced)
DB_ACQUIRE = "db.acquire"
DB_QUERY = "db.query"
CACHE_OPTICAL_HIT = "cache.optical.hit"
CACHE_OPTICAL_MISS = "cache.optical.miss"
CACHE_OPTICAL_HITRATE = "cache.optical.hitrate"

# --- Per-request SQL metrics (count and total time in seconds) ---
_REQ_SQL_COUNT: ContextVar[int] = ContextVar("req_sql_count", default=0)
_REQ_SQL_TIME: ContextVar[float] = ContextVar("req_sql_time", default=0.0)


def reset_request_sql_metrics() -> None:
    """Reset per-request SQL counters at the beginning of each HTTP request."""
    _REQ_SQL_COUNT.set(0)
    _REQ_SQL_TIME.set(0.0)


def record_sql_query(elapsed_seconds: float) -> None:
    """Increment the per-request SQL counters when a query completes."""
    try:
        _REQ_SQL_COUNT.set(_REQ_SQL_COUNT.get() + 1)
        _REQ_SQL_TIME.set(_REQ_SQL_TIME.get() + float(elapsed_seconds))
    except Exception:
        # If no context is active, ignore silently (e.g., background tasks/tests)
        pass


def get_request_sql_metrics() -> tuple[int, float]:
    """Return current per-request SQL (count, total_seconds)."""
    try:
        return _REQ_SQL_COUNT.get(), _REQ_SQL_TIME.get()
    except Exception:
        return 0, 0.0
