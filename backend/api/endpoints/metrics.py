from fastapi import APIRouter, Response
from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest

import backend.services.metrics_service as metrics_service
from backend.api.schemas import MetricsSnapshotResponse
from backend.services.traffic_engine import get_v2_snapshot

router = APIRouter(tags=["metrics"], prefix="/metrics")

# Prometheus metric primitives (optionally used by instrumentation elsewhere)
DB_QUERY_SECONDS = Histogram("db_query_seconds", "Datenbankabfragezeiten")
OPTICAL_CACHE_HITS = Counter("optical_cache_hits_total", "Cache-Treffer bei Pfadberechnung")
OPTICAL_CACHE_MISSES = Counter("optical_cache_misses_total", "Cache-Fehler bei Pfadberechnung")
OPTICAL_CACHE_HITRATE = Gauge("optical_cache_hitrate", "Cache Hit-Rate (0..1)")

# PERF-001: Adjacency cache metrics
ADJACENCY_CACHE_HITS = Counter(
    "traffic_adjacency_cache_hits_total", "Number of adjacency cache hits"
)
ADJACENCY_CACHE_MISSES = Counter(
    "traffic_adjacency_cache_misses_total", "Number of adjacency cache misses"
)
ADJACENCY_CACHE_HITRATE = Gauge(
    "traffic_adjacency_cache_hitrate", "Adjacency cache hit rate (0..1)"
)

# L3 reachability/resolver observability (Phase 4)
L3_RESOLVER_DURATION = Histogram(
    "l3_resolver_duration_seconds",
    "Duration of L3 reachability resolution to backbone anchor",
)
# outcome: ok|fail; reason: categorized failure reason ("none" on success)
L3_RESOLVER_CALLS = Counter(
    "l3_resolver_calls_total",
    "Number of L3 reachability resolver calls",
    labelnames=["outcome", "reason"],
)
# Hop count observed for successful or partial traversals (integer buckets)
L3_RESOLVER_HOPS = Histogram(
    "l3_resolver_hops",
    "Hop count observed while resolving L3 path",
    buckets=(0, 1, 2, 3, 5, 8, 13, 21),
)

# Quick-win observability metrics
# API request duration (use path template when available to control cardinality)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "path", "status"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)

# Status recompute duration
STATUS_RECOMPUTE_DURATION = Histogram(
    "status_recompute_duration_seconds", "Status recompute duration in seconds"
)

# Status recompute phase durations (labeled by phase)
STATUS_RECOMPUTE_PHASE_DURATION = Histogram(
    "status_recompute_phase_seconds",
    "Status recompute phase duration in seconds",
    labelnames=["phase"],
    buckets=(
        0.0005,
        0.001,
        0.0025,
        0.005,
        0.0075,
        0.01,
        0.015,
        0.02,
        0.03,
        0.05,
        0.075,
        0.1,
        0.15,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        25.0,
    ),
)

# Traffic engine tick duration
TRAFFIC_TICK_DURATION = Histogram(
    "traffic_tick_duration_seconds", "Traffic engine tick duration in seconds"
)

# Traffic engine phase durations (labeled by phase)
TRAFFIC_TICK_PHASE_DURATION = Histogram(
    "traffic_tick_phase_seconds",
    "Traffic engine tick phase duration in seconds",
    labelnames=["phase"],
    buckets=(
        0.0005,
        0.001,
        0.0025,
        0.005,
        0.0075,
        0.01,
        0.015,
        0.02,
        0.03,
        0.05,
        0.075,
        0.1,
        0.15,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        25.0,
    ),
)

# Dirty-set frontier size histogram (incremental recompute observability)
DIRTY_SET_SIZE_HISTOGRAM = Histogram(
    "dirty_set_frontier_size",
    "Number of unique devices in the incremental recompute frontier",
    buckets=(1, 2, 4, 8, 16, 32, 64, 128, 256, 512),
)

# Async job worker/queue observability (Phase 2)
# Current kinds are limited (e.g., link.override); cardinality remains bounded.
JOB_QUEUE_DEPTH = Gauge("job_queue_depth", "Current depth of the async job queue")
JOBS_PROCESSED_TOTAL = Counter(
    "jobs_processed_total",
    "Total number of jobs processed by kind",
    labelnames=["kind"],
)
JOB_WORKER_BATCH_SIZE = Histogram(
    "job_worker_batch_size",
    "Size of microbatches processed by the worker",
    buckets=(1, 2, 4, 8, 16, 32, 64, 128, 256),
)
JOB_WORKER_BATCH_DURATION = Histogram(
    "job_worker_batch_duration_seconds",
    "Duration to process a microbatch",
    buckets=(
        0.0005,
        0.001,
        0.0025,
        0.005,
        0.0075,
        0.01,
        0.015,
        0.02,
        0.03,
        0.05,
        0.075,
        0.1,
        0.15,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
    ),
)


@router.get("/snapshot", response_model=MetricsSnapshotResponse)
def get_metrics_snapshot() -> MetricsSnapshotResponse:  # type: ignore[override]
    """Return the latest device metrics snapshot and last tick.

    Shape: { lastTick: number, devices: { [id]: { bps, utilization, version } } }
    """
    # Check if Go Traffic Engine is active
    from backend.services.traffic_engine import ENGINE_SINGLETON

    # If Go is active, use ONLY v2 (Go data) - no legacy fallback!
    # This prevents Python MetricsService from running expensive aggregation in parallel
    if hasattr(ENGINE_SINGLETON, "use_go") and ENGINE_SINGLETON.use_go:
        v2 = get_v2_snapshot()
        if isinstance(v2, dict):
            return v2  # type: ignore[return-value]
        # Fallback if Go data not ready
        return {"lastTick": 0, "devices": {}, "links": {}}  # type: ignore[return-value]

    # Python fallback: compute both snapshots and prefer fresher one
    legacy = metrics_service.METRICS.get_snapshot()
    v2 = get_v2_snapshot()
    if isinstance(v2, dict):
        try:
            tick_v2 = int(v2.get("lastTick", 0))
        except Exception:
            tick_v2 = 0
        try:
            tick_legacy = int(legacy.get("lastTick", 0))
        except Exception:
            tick_legacy = 0
        # Prefer v2 if it has equal or newer tick; otherwise, use legacy
        if tick_v2 >= tick_legacy:
            return v2  # type: ignore[return-value]
    return legacy  # type: ignore[return-value]


@router.get("/runtime", response_model=dict)
def get_runtime_metrics() -> dict:
    """Return runtime observability metrics (DB acquire/query, optical cache hit rate)."""
    from backend.core.observability import (
        CACHE_OPTICAL_HIT,
        CACHE_OPTICAL_HITRATE,
        CACHE_OPTICAL_MISS,
        OBS,
    )

    # Derive optical cache hit-rate gauge
    snap = OBS.snapshot()
    hits = int(snap["counters"].get(CACHE_OPTICAL_HIT, 0))
    misses = int(snap["counters"].get(CACHE_OPTICAL_MISS, 0))
    total = hits + misses
    rate = (hits / total) if total else 0.0
    OBS.set(CACHE_OPTICAL_HITRATE, rate)
    # Mirror into Prometheus gauge for scrapes
    try:
        OPTICAL_CACHE_HITRATE.set(rate)
    except Exception:
        pass
    # Return a fresh snapshot including the updated gauge
    return OBS.snapshot()


@router.get("/prometheus", include_in_schema=False)
def prometheus_metrics() -> Response:
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")
