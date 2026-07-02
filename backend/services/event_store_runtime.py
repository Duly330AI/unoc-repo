"""Runtime context for event-store projection writes and guard enforcement."""

from __future__ import annotations

import functools
import os
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, TypeVar

_PROJECTION_WRITE: ContextVar[bool] = ContextVar("eventstore_projection_write", default=False)

_F = TypeVar("_F", bound=Callable[..., Any])


def event_store_enforcement_enabled() -> bool:
    # Enabled by default: the EventStore is authoritative for guarded domain
    # mutations. Set UNOC_EVENTSTORE_ENFORCE=0 only for explicit opt-out
    # (e.g. unit tests that build topology state directly).
    return os.getenv("UNOC_EVENTSTORE_ENFORCE", "1").strip().lower() in {"1", "true", "yes", "on"}


def is_projection_write_allowed() -> bool:
    return _PROJECTION_WRITE.get()


@contextmanager
def projection_write_context():
    token = _PROJECTION_WRITE.set(True)
    try:
        yield
    finally:
        _PROJECTION_WRITE.reset(token)


def projection_write(fn: _F) -> _F:
    """Mark a covered write path: its DB mutations run inside projection_write_context.

    Covered paths append EventStore write-path events for their mutations, so the
    hard bypass guard (UNOC_EVENTSTORE_ENFORCE=1) must allow them.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with projection_write_context():
            return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]