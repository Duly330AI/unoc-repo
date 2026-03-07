"""Centralized metrics constants and helpers (TASK-061).

These values are shared across services and exposed via /api/config for frontend use.
"""

from __future__ import annotations

# Absolute utilization delta required to emit a change event
EPSILON_METRICS_DELTA: float = 0.01

# Utilization bucket thresholds in percent
# Buckets: [0..50], (50..70], (70..90], (90..100], (>100)
UTILIZATION_BUCKETS: list[int] = [50, 70, 90, 100]


def utilization_bucket(util_fraction: float) -> int:
    """Return bucket index for a utilization fraction (1.0 == 100%).

    0: <=50%, 1: <=70%, 2: <=90%, 3: <=100%, 4: >100%
    """
    pct = 100.0 if util_fraction == float("inf") else (util_fraction * 100.0)
    if pct <= UTILIZATION_BUCKETS[0]:
        return 0
    if pct <= UTILIZATION_BUCKETS[1]:
        return 1
    if pct <= UTILIZATION_BUCKETS[2]:
        return 2
    if pct <= UTILIZATION_BUCKETS[3]:
        return 3
    return 4


def is_overloaded(util_fraction: float) -> bool:
    """True if utilization >= 100% (or infinite)."""
    if util_fraction == float("inf"):
        return True
    return util_fraction >= 1.0
