"""Optical constants and enumerations (TASK-037).

Defines supported fiber types and their baseline attenuation characteristics.
This is intentionally small and can expand alongside the optical simulation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FiberSpec:
    key: str
    mode: str  # "SMF" | "MMF"
    standard: str  # e.g., "G.652D", "G.657A1", "OM4"
    attenuation_db_per_km: float  # baseline @ 1310/850nm depending on mode


# Minimal catalog; add more as needed
_FIBERS: list[FiberSpec] = [
    FiberSpec("SMF_G652D", "SMF", "G.652D", 0.35),
    FiberSpec("SMF_G657A1", "SMF", "G.657A1", 0.35),
    FiberSpec("SMF_G657A2", "SMF", "G.657A2", 0.35),
    FiberSpec("MMF_OM3", "MMF", "OM3", 3.5),
    FiberSpec("MMF_OM4", "MMF", "OM4", 3.0),
]

FIBER_TYPES: dict[str, FiberSpec] = {f.key: f for f in _FIBERS}
FIBER_TYPE_KEYS: set[str] = set(FIBER_TYPES.keys())

__all__ = ["FiberSpec", "FIBER_TYPES", "FIBER_TYPE_KEYS"]
