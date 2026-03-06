"""Shared, small helpers for links endpoints.

Kept separate to reduce the size of `links_helpers.py` while preserving the
public import surface via re-exports in that module.
"""

from __future__ import annotations

__all__ = ["normalize_status_str"]


def normalize_status_str(x: object | None) -> str:
    """Normalize enum or string status values to plain strings like 'UP'."""
    if x is None:
        return ""
    val = getattr(x, "value", None)
    if isinstance(val, str):
        return val
    s = str(x)
    if "." in s:
        return s.split(".")[-1]
    return s
