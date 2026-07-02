"""Runtime context for event-store projection writes and guard enforcement."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar

_PROJECTION_WRITE: ContextVar[bool] = ContextVar("eventstore_projection_write", default=False)


def event_store_enforcement_enabled() -> bool:
    return os.getenv("UNOC_EVENTSTORE_ENFORCE", "0").strip().lower() in {"1", "true", "yes", "on"}


def is_projection_write_allowed() -> bool:
    return _PROJECTION_WRITE.get()


@contextmanager
def projection_write_context():
    token = _PROJECTION_WRITE.set(True)
    try:
        yield
    finally:
        _PROJECTION_WRITE.reset(token)