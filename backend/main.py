"""FastAPI application factory for UNOC backend (Phase B skeleton)."""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from . import events as _events
from .api.endpoints.ws import WsBroadcaster
from .api.routes import api_router
from .core.config import get_settings
from .core.limits import limiter
from .core.logging import configure_logging
from .core.observability import get_request_sql_metrics, reset_request_sql_metrics
from .db import init_db
from .error_handlers import install_error_handlers
from .services import recompute_coalescer as _coalescer
from .services.job_dispatcher import QUEUE as _JOB_QUEUE
from .services.job_dispatcher import handle_batch as _handle_batch
from .services.traffic_engine import ENGINE_SINGLETON as _traffic_engine
from .services.worker import Worker as _Worker


def _check_go_services_health():
    """Check health of all 5 Go services on startup (logs warnings only)."""
    import logging
    import socket
    import urllib.request

    log = logging.getLogger("backend.startup")
    log.info("🔍 Checking Go services availability...")

    services = {
        "Traffic Engine": {"type": "http", "url": "http://localhost:8080/health"},
        "Optical PathFinder": {"type": "grpc", "host": "localhost", "port": 50051},
        "Status Propagation": {"type": "grpc", "host": "localhost", "port": 50053},
        "Batch Operations": {"type": "grpc", "host": "localhost", "port": 50052},
        "Port Summary": {"type": "grpc", "host": "localhost", "port": 50054},
    }

    all_healthy = True
    for name, config in services.items():
        try:
            if config["type"] == "http":
                with urllib.request.urlopen(config["url"], timeout=2) as response:
                    if response.status == 200:
                        log.info(f"   ✅ {name:<22} → {config['url']}")
                    else:
                        log.warning(f"   ⚠️  {name:<22} → HTTP {response.status}")
                        all_healthy = False
            elif config["type"] == "grpc":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((config["host"], config["port"]))
                sock.close()
                if result == 0:
                    log.info(f"   ✅ {name:<22} → grpc://{config['host']}:{config['port']}")
                else:
                    log.warning(f"   ⚠️  {name:<22} → Connection refused")
                    all_healthy = False
        except Exception as e:
            log.warning(f"   ❌ {name:<22} → {type(e).__name__}: {e}")
            all_healthy = False

    if all_healthy:
        log.info("✅ All Go services are available!")
    else:
        log.warning("⚠️  Some Go services are unavailable (degraded mode)")
        log.warning("💡 Run: .\\scripts\\start_all_services.ps1")


def _rl_exception_handler(request: Request, exc: Exception):
    # Bridge handler to satisfy FastAPI typing while delegating to slowapi's handler
    if isinstance(exc, RateLimitExceeded):
        return _rate_limit_exceeded_handler(request, exc)
    raise exc


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    # Wire global broadcaster early so tests that don't run lifespan still see it
    try:
        _events.set_broadcaster(WsBroadcaster())
    except Exception:
        # Non-fatal in tests or unusual startup sequences
        pass
    app = FastAPI(title=settings.app_name)
    # Configure rate limiter - TEMPORARILY DISABLED FOR PERFORMANCE TESTING
    # app.state.limiter = limiter
    # app.add_exception_handler(RateLimitExceeded, _rl_exception_handler)
    # app.add_middleware(SlowAPIMiddleware)
    # Dev CORS (allow Vite frontend on :5173). Adjust in prod.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        try:
            # Ensure database schema is initialized once at startup
            init_db()
        except Exception:
            # Non-fatal in tests or unusual startup sequences
            pass

        # Check Go services health on startup
        try:
            _check_go_services_health()
        except Exception:
            # Non-fatal warning only
            pass
        try:
            _coalescer.start()
        except Exception:
            pass
        try:
            # Start traffic engine if enabled by env flag inside the engine
            _traffic_engine.start()
        except Exception:
            pass
        # Background worker loop (always on)
        _worker_task = None
        try:
            # Import metrics lazily to avoid circular imports
            try:
                from backend.api.endpoints.metrics import JOB_QUEUE_DEPTH as _JOB_Q_GAUGE
                from backend.api.endpoints.metrics import JOB_WORKER_BATCH_DURATION as _BATCH_DUR
                from backend.api.endpoints.metrics import JOB_WORKER_BATCH_SIZE as _BATCH_SIZE
                from backend.api.endpoints.metrics import JOBS_PROCESSED_TOTAL as _JOBS_COUNT
            except Exception:
                _JOB_Q_GAUGE = _BATCH_DUR = _BATCH_SIZE = _JOBS_COUNT = None  # type: ignore

            _worker = _Worker()

            async def _loop():
                # Simple periodic loop; keep deterministic cadence.
                # Use settings.batch_budget_ms to bound per-iteration work.
                budget_ms = int(getattr(get_settings(), "batch_budget_ms", 50) or 50)
                while True:
                    try:
                        # Gauge current queue depth
                        if _JOB_Q_GAUGE is not None:
                            try:
                                _JOB_Q_GAUGE.set(_JOB_QUEUE.size())
                            except Exception:
                                pass
                        # Pull one microbatch and time it
                        t0 = asyncio.get_running_loop().time()
                        # Fetch batch without side effects, then handle to observe size
                        batch = _JOB_QUEUE.next_microbatch(max_items=256, budget_ms=budget_ms)
                        if not batch:
                            # Small sleep to avoid tight loop when idle
                            await asyncio.sleep(0.05)
                            continue
                        if _BATCH_SIZE is not None:
                            try:
                                _BATCH_SIZE.observe(len(batch))
                            except Exception:
                                pass
                        # Handle the batch
                        _handle_batch(batch)
                        # Record duration
                        if _BATCH_DUR is not None:
                            try:
                                _BATCH_DUR.observe(asyncio.get_running_loop().time() - t0)
                            except Exception:
                                pass
                        # Increment processed counters
                        if _JOBS_COUNT is not None:
                            try:
                                for j in batch:
                                    _JOBS_COUNT.labels(kind=j.kind).inc()
                            except Exception:
                                pass
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        # Never crash the loop on exceptions
                        await asyncio.sleep(0.05)

            _worker_task = asyncio.create_task(_loop())
        except Exception:
            # Non-fatal
            _worker_task = None
        try:
            yield
        finally:
            # Shutdown
            try:
                _traffic_engine.stop()
            except Exception:
                pass
            try:
                _coalescer.stop()
            except Exception:
                pass
            try:
                if _worker_task is not None:
                    _worker_task.cancel()
                    with contextlib.suppress(Exception):
                        await _worker_task
            except Exception:
                pass

    # Recreate app with lifespan handler to avoid deprecated on_event
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    # Configure rate limiter again on the re-instantiated app
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rl_exception_handler)
    app.add_middleware(SlowAPIMiddleware)
    # Re-apply middleware and routes after re-instantiating app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_prefix)

    # Per-request perf logging middleware (lightweight)
    import logging
    import time as _time

    perf_logger = logging.getLogger("perf")
    if not perf_logger.handlers:
        try:
            import os as _os
            from logging.handlers import RotatingFileHandler

            _os.makedirs("logs", exist_ok=True)
            h = RotatingFileHandler("logs/perf.log", maxBytes=5 * 1024 * 1024, backupCount=2)
            fmt = logging.Formatter("%(asctime)s %(message)s")
            h.setFormatter(fmt)
            perf_logger.addHandler(h)
            perf_logger.setLevel(logging.INFO)
        except Exception:
            # Fallback to console-only if file handler fails
            pass

    @app.middleware("http")
    async def _perf_middleware(request: Request, call_next):  # type: ignore[override]
        reset_request_sql_metrics()
        t0 = _time.perf_counter()
        response = await call_next(request)
        dt = _time.perf_counter() - t0
        # Observe API latency histogram (import lazily to avoid circulars)
        try:
            from backend.api.endpoints import metrics as _metrics

            # Prefer templated path from route to control cardinality
            route = request.scope.get("route") if isinstance(request.scope, dict) else None
            path_tmpl = getattr(route, "path", None) or request.url.path
            status_code = getattr(response, "status_code", 0) or 0
            status_cls = f"{int(status_code) // 100}xx" if status_code else "0xx"
            _metrics.HTTP_REQUEST_DURATION.labels(
                method=request.method,
                path=path_tmpl,
                status=status_cls,
            ).observe(dt)
        except Exception:
            # Never fail request due to metrics
            pass
        sql_count, sql_time = get_request_sql_metrics()
        # Log as a single line for easy grep
        try:
            perf_logger.info(
                "method=%s path=%s status=%s dur_ms=%.2f sql_count=%d sql_ms=%.2f",
                request.method,
                request.url.path,
                getattr(response, "status_code", "?"),
                dt * 1000.0,
                sql_count,
                sql_time * 1000.0,
            )
        except Exception:
            pass
        return response

    install_error_handlers(app)
    return app


app = create_app()
