"""
Performance test configuration - PostgreSQL REQUIRED

Performance tests (marked with @pytest.mark.perf) MUST use PostgreSQL,
not inmemory, because:
1. Go engine reads from PostgreSQL
2. Realistic performance measurements require persistent DB
3. Large datasets (200+ devices) need real DB constraints

IMPORTANT: pytest_configure() hook runs BEFORE root conftest.py imports backend.db,
so we can set DATABASE_URL early enough to override inmemory mode.

Usage:
    $env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
    pytest -m perf backend/tests/perf/test_go_200_clean.py
"""

import os

import pytest


def pytest_configure(config):
    """
    Pytest hook that runs BEFORE any imports.

    This is our chance to set DATABASE_URL before backend.db is imported.
    We override the root conftest.py settings here.

    CRITICAL: We must RE-INITIALIZE backend.db engine after changing ENV vars,
    because root conftest.py already imported backend.db with inmemory settings!
    """
    # Check if we're running perf tests - ONLY activate on explicit -m perf marker
    markexpr = config.getoption("-m", default="")
    if "perf" in markexpr:
        # Running perf tests - ensure PostgreSQL
        db_url = os.environ.get("DATABASE_URL", "")

        # Override root conftest.py
        if "postgresql" not in db_url.lower():
            # Use default PostgreSQL if not set
            os.environ["DATABASE_URL"] = "postgresql://unoc:unocpw@localhost:5432/unocdb"
            os.environ["UNOC_DB_URL"] = "postgresql://unoc:unocpw@localhost:5432/unocdb"

        # CRITICAL: Remove UNOC_PERSISTENCE=inmemory from root conftest.py
        if "UNOC_PERSISTENCE" in os.environ:
            del os.environ["UNOC_PERSISTENCE"]

        print(f"\n[PERF] Using PostgreSQL: {os.environ['DATABASE_URL']}")

        # RE-INITIALIZE backend.db engine with PostgreSQL!
        # (root conftest.py already imported it with inmemory)
        from sqlalchemy import create_engine
        from sqlalchemy.pool import QueuePool

        import backend.db as db

        # Rebuild engine with PostgreSQL URL
        pg_url = "postgresql+psycopg://unoc:unocpw@localhost:5432/unocdb"

        # Override module-level vars
        db.SQLALCHEMY_DATABASE_URL = pg_url
        db.engine = create_engine(
            pg_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )

        # Re-install query timers
        db._install_query_timers_sync(db.engine)

        print(f"[PERF] Re-initialized backend.db engine: {db.engine}")
    else:
        # Not running perf tests - let root conftest.py handle it (inmemory)
        pass


@pytest.fixture(autouse=True)
def _per_test_clean_db(request):
    """
    OVERRIDE root conftest.py's _per_test_clean_db for perf tests.

    Performance tests manage their own DB lifecycle (via reset_dev_db.py script),
    so we SKIP the automatic reset_db() that root conftest.py does.

    This fixture has the same name as root conftest.py, so it shadows it.
    """
    # Check if this is a perf test
    marker = request.node.get_closest_marker("perf")
    if marker:
        # Perf test - do NOT reset DB (fixture handles it)
        print("[PERF] Skipping auto-reset (managed by fixture)")
        yield
    else:
        # Not a perf test - let root conftest.py handle it
        # (This shouldn't happen, but just in case)
        import backend.db as db

        db.reset_db()
        db.init_db()
        yield
