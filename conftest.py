"""Global pytest configuration to enforce SQLite in-memory for all tests.

This file lives at the repository root so it's imported by pytest before any
test modules across the entire workspace. It ensures:

- Tests never read or use DATABASE_URL/UNOC_DB_URL from .env
- UNOC_PERSISTENCE is set to "inmemory" so backend.db initializes SQLite
- The same engine object is reused; we reset schema per-test without rebinding
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

# 1) Force isolation env before importing backend.db
os.environ["DATABASE_URL"] = ""
os.environ["UNOC_DB_URL"] = ""
os.environ["UNOC_PERSISTENCE"] = "inmemory"
# Avoid accidental dev-time features in tests
os.environ.pop("UNOC_DEV_FEATURES", None)

# 2) Import backend.db so it initializes engines against SQLite in-memory
import backend.db as db  # noqa: E402


@pytest.fixture(autouse=True)
def _per_test_clean_db():
    """Reset schema for a clean DB before each test without rebinding engines."""
    # Clear any cross-test propagation state
    try:
        from backend.services import status_propagation_store

        status_propagation_store.clear()
    except Exception:
        pass

    # Make sure dev features are disabled during tests unless explicitly enabled
    os.environ.pop("UNOC_DEV_FEATURES", None)

    # Reset and re-create schema using the currently-initialized engine
    db.reset_db()
    db.init_db()

    # Sanity check the engine is usable
    with db.engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    yield
