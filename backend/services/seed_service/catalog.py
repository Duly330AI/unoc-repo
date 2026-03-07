"""Deprecated module.

All seeding helpers moved to `backend.services.seed_helpers`.
This file remains only as a placeholder to avoid import ambiguity on some systems.
"""

from __future__ import annotations

from typing import Any


def ensure_default_tariffs(*_: Any, **__: Any) -> None:  # pragma: no cover
    return


def ensure_default_hardware_models(*_: Any, **__: Any) -> None:  # pragma: no cover
    return
