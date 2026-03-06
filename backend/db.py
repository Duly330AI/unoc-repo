"""Database helper utilities.

Adds simple environment-based persistence mode selection:

    UNOC_PERSISTENCE=inmemory  -> ephemeral in-memory (for tests / CI)
    UNOC_PERSISTENCE=file      -> file based (default) using ``unoc_dev.db``
    DATABASE_URL=...           -> explicit SQLAlchemy URL override (preferred)
    UNOC_DB_URL=...            -> legacy/alternative override (advanced)

Also exposes ``reset_db`` for test isolation (drop + recreate all tables).
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import QueuePool, StaticPool
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from .core.observability import DB_ACQUIRE, DB_QUERY, OBS, record_sql_query

# Windows async event loop compatibility for psycopg async
# Psycopg 3 cannot run with ProactorEventLoop; enforce Selector policy on Windows
try:  # pragma: no cover - environment-specific
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except Exception:
    pass

# Load .env file values into process environment early so DATABASE_URL and other
# settings are available even when not exported in the shell (dev convenience).
try:  # pragma: no cover - simple env bootstrap
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# Optional Prometheus metrics (guard import to keep runtime flexible). We import
# the already-registered primitives from the metrics endpoint to avoid duplicates.
try:  # pragma: no cover - optional dependency
    from .api.endpoints.metrics import DB_QUERY_SECONDS  # type: ignore
except Exception:  # pragma: no cover
    DB_QUERY_SECONDS = None  # type: ignore[assignment]
# Import models to register all SQLModel tables with metadata before DDL ops
from . import models as _models  # noqa: F401
from .models import VRF, Device, Interface, InterfaceAddress, Link, Prefix, Tariff  # noqa: F401

# Serialize schema operations to avoid DDL races (deadlocks) when endpoints/tests
# call init_db() concurrently. Also track if we've already initialized the schema
# to make init_db() effectively idempotent for this process.
_SCHEMA_LOCK = threading.RLock()
_SCHEMA_INITIALIZED = False

_persistence_mode = os.getenv("UNOC_PERSISTENCE", "file").lower().strip()
# Prefer standard DATABASE_URL; fall back to legacy UNOC_DB_URL
_explicit_url = os.getenv("DATABASE_URL") or os.getenv("UNOC_DB_URL")

if _explicit_url:
    SQLALCHEMY_DATABASE_URL = _explicit_url
elif _persistence_mode == "inmemory":
    # Use a named shared in-memory DB URI so multiple engines/connections see the same DB
    # Note: requires connect_args {"uri": True}
    SQLALCHEMY_DATABASE_URL = "sqlite:///file:unoc_memdb?mode=memory&cache=shared&uri=true"
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///unoc_dev.db"


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite:")


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql:")


def _to_async_url(url: str) -> str:
    """Convert sync URL to async driver URL where applicable.

    - sqlite -> sqlite+aiosqlite
    - postgresql[/+psycopg2|+psycopg] -> postgresql+psycopg
    Leaves already-async URLs unchanged.
    """
    if url.startswith("sqlite+aiosqlite:") or url.startswith("postgresql+psycopg:"):
        return url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql+psycopg2://") or url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.split("://", 1)[1]
    return url


def _to_sync_url(url: str) -> str:
    """Normalize sync SQLAlchemy URL to preferred drivers.

    - postgresql[/+psycopg2] -> postgresql+psycopg
    Leaves sqlite URLs unchanged and respects already-correct prefixes.
    """
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql+psycopg2://") or url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.split("://", 1)[1]
    return url


def _sanitize_connect_args(url: str, connect_args: dict | None) -> dict:
    """Return a copy of connect_args safe for the given URL.

    - For SQLite URLs: keep only known sqlite keys (check_same_thread, uri)
    - For non-SQLite URLs: strip all sqlite-only keys entirely

    This is a defensive guard to avoid leaking sqlite-only options like
    "check_same_thread" into other DBAPI connect() calls (e.g., psycopg).
    """
    if not connect_args:
        return {}
    if _is_sqlite(url):
        allowed = {"check_same_thread", "uri"}
        return {k: v for k, v in connect_args.items() if k in allowed}
    # Non-sqlite backends should not receive any sqlite-specific args
    return {}


def _install_query_timers_sync(bind):
    @event.listens_for(bind, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()  # type: ignore[attr-defined]

    @event.listens_for(bind, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        t0 = getattr(context, "_query_start_time", None)
        if t0 is not None:
            dt = time.perf_counter() - t0
            OBS.observe(DB_QUERY, dt)
            record_sql_query(dt)
            if DB_QUERY_SECONDS is not None:
                try:
                    DB_QUERY_SECONDS.observe(dt)
                except Exception:
                    pass


def _install_query_timers_async(async_bind):
    @event.listens_for(async_bind.sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()  # type: ignore[attr-defined]

    @event.listens_for(async_bind.sync_engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        t0 = getattr(context, "_query_start_time", None)
        if t0 is not None:
            dt = time.perf_counter() - t0
            OBS.observe(DB_QUERY, dt)
            record_sql_query(dt)
            if DB_QUERY_SECONDS is not None:
                try:
                    DB_QUERY_SECONDS.observe(dt)
                except Exception:
                    pass


_url_is_sqlite = _is_sqlite(SQLALCHEMY_DATABASE_URL)
if _persistence_mode == "inmemory" and _url_is_sqlite:
    # In-memory (shared) engines: must use StaticPool and URI syntax with shared cache
    _connect_args = {"check_same_thread": False, "uri": True}
    engine = sa_create_engine(
        _to_sync_url(SQLALCHEMY_DATABASE_URL),
        echo=False,
        connect_args=_sanitize_connect_args(SQLALCHEMY_DATABASE_URL, _connect_args),
        poolclass=StaticPool,
    )
    async_engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
        echo=False,
        connect_args=_sanitize_connect_args(SQLALCHEMY_DATABASE_URL, _connect_args),
        poolclass=StaticPool,
    )
    async_session_factory = async_sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )
    # Install instrumentation
    _install_query_timers_sync(engine)
    _install_query_timers_async(async_engine)
else:
    # Configurable pool settings for file-based SQLite or other RDBMS backends
    _pool_size = int(os.getenv("UNOC_DB_POOL_SIZE", "10"))
    _max_overflow = int(os.getenv("UNOC_DB_MAX_OVERFLOW", "20"))
    _pool_timeout = int(os.getenv("UNOC_DB_POOL_TIMEOUT", "30"))  # seconds
    _pool_recycle = int(os.getenv("UNOC_DB_POOL_RECYCLE", "3600"))  # seconds
    # Pre-ping keeps connections healthy across long idles
    _is_sqlite_backend = _is_sqlite(SQLALCHEMY_DATABASE_URL)
    # SQLite needs check_same_thread; Postgres must not receive sqlite-specific args
    _connect_args = _sanitize_connect_args(
        SQLALCHEMY_DATABASE_URL, {"check_same_thread": False} if _is_sqlite_backend else {}
    )
    if _is_sqlite_backend:
        engine = sa_create_engine(
            _to_sync_url(SQLALCHEMY_DATABASE_URL),
            echo=False,
            connect_args=_connect_args,  # type: ignore[arg-type]
            poolclass=QueuePool,
            pool_size=_pool_size,
            max_overflow=_max_overflow,
            pool_timeout=_pool_timeout,
            pool_recycle=_pool_recycle,
            pool_pre_ping=True,
        )
    else:
        engine = sa_create_engine(
            _to_sync_url(SQLALCHEMY_DATABASE_URL),
            echo=False,
            poolclass=QueuePool,
            pool_size=_pool_size,
            max_overflow=_max_overflow,
            pool_timeout=_pool_timeout,
            pool_recycle=_pool_recycle,
            pool_pre_ping=True,
        )
    # Async engine mirrors pool settings; translate driver
    _async_url = _to_async_url(SQLALCHEMY_DATABASE_URL)
    async_engine = create_async_engine(
        _async_url,
        echo=False,
        # connect_args only for sqlite; sanitize defensively otherwise
        connect_args=_sanitize_connect_args(
            _async_url, {"check_same_thread": False} if _is_sqlite_backend else {}
        ),
        pool_size=_pool_size,
        max_overflow=_max_overflow,
        pool_timeout=_pool_timeout,
        pool_recycle=_pool_recycle,
        pool_pre_ping=True,
    )
    async_session_factory = async_sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )
    # Install instrumentation
    _install_query_timers_sync(engine)
    _install_query_timers_async(async_engine)


def init_db() -> None:
    """Ensure database schema exists.

    Safe and idempotent: always attempts create_all() under a lock. This avoids
    race conditions where some tests or background tasks may reset the schema
    while others assume tables exist.
    """
    global _SCHEMA_INITIALIZED
    with _SCHEMA_LOCK:
        SQLModel.metadata.create_all(engine)
        _SCHEMA_INITIALIZED = True


def reset_db() -> None:
    """Drop and recreate all tables (test isolation).

    Additionally disposes engine pools to ensure any server-side prepared
    statements referencing dropped types (e.g., legacy native ENUM OIDs)
    are cleared. This prevents psycopg 'cache lookup failed for type' errors
    when tests call reset_db() mid-process.
    """
    global _SCHEMA_INITIALIZED
    with _SCHEMA_LOCK:
        # Quiesce background recompute timers to avoid SQLite lock races during DDL
        try:  # pragma: no cover - defensive guard
            from .services import recompute_coalescer as _coalescer

            _coalescer.stop()
            # Give any recently cancelled timers a moment to settle
            time.sleep(0.005)
            # If a recompute was mid-execution when stop() was called, wait
            # briefly for it to finish to avoid SQLITE "table is locked" when
            # issuing DDL below. is_idle() returns False while executing.
            try:
                deadline = time.time() + 1.0  # up to 1s (should normally be a few ms)
                while not _coalescer.is_idle() and time.time() < deadline:
                    time.sleep(0.01)
            except Exception:  # pragma: no cover - safety
                pass
        except Exception:
            pass
        # If running against Postgres, prefer dropping the entire public schema
        # with CASCADE to avoid dependency errors from out-of-band constraints
        # or older schemas that metadata.drop_all() can't order correctly.
        # Try Postgres-style schema reset first; fall back to SQLModel drop_all for others
        from sqlalchemy import text
        from sqlalchemy.schema import DropTable

        did_pg_schema_reset = False
        try:
            with engine.begin() as conn:
                conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
                did_pg_schema_reset = True
        except Exception:
            # Fallback: attempt per-table DROP ... CASCADE for PostgreSQL
            try:
                with engine.begin() as conn:
                    for table in reversed(SQLModel.metadata.sorted_tables):
                        conn.execute(DropTable(table, cascade=True))  # type: ignore[call-arg]
                did_pg_schema_reset = True
            except Exception:
                did_pg_schema_reset = False

        if did_pg_schema_reset:
            # Recreate on a clean public schema
            SQLModel.metadata.create_all(engine)
        else:
            # Default path for SQLite and non-Postgres backends
            SQLModel.metadata.drop_all(engine)
            SQLModel.metadata.create_all(engine)
        # Reset prepared statements / stale connections for non in-memory backends.
        # IMPORTANT: For SQLite in-memory with StaticPool, disposing closes the only
        # connection and drops the schema. Skip dispose in that case to preserve tables.
        try:
            is_inmemory_sqlite = _persistence_mode == "inmemory" and _is_sqlite(
                SQLALCHEMY_DATABASE_URL
            )
        except Exception:
            is_inmemory_sqlite = False
        if not is_inmemory_sqlite:
            try:
                # Dispose underlying sync engine used by async engine first
                async_engine.sync_engine.dispose(close=True)
            except Exception:
                pass
            try:
                engine.dispose(close=True)
            except Exception:
                pass
        _SCHEMA_INITIALIZED = True


@contextmanager
def get_session() -> Iterator[Session]:
    # Measure acquire time including pool checkout by forcing a connection
    with OBS.time_block(DB_ACQUIRE):
        session = Session(engine)
        try:
            session.connection()
        except Exception:
            # Ignore errors here; acquisition metric should still be recorded
            pass
    try:
        yield session
    finally:
        session.close()


# Async session dependency factory
async def get_async_session() -> AsyncIterator[AsyncSession]:
    # Measure acquire time including pool checkout by forcing a connection
    with OBS.time_block(DB_ACQUIRE):
        session: AsyncSession = async_session_factory()  # type: ignore[misc]
        try:
            await session.connection()
        except Exception:
            pass
    try:
        yield session
    finally:
        await session.close()


# --- end helpers ---
