"""In‑memory diagnostics snapshot for unified status refactor (Phase 1).

Provides lightweight, side‑effect free storage of per‑device evaluation facts
that future phases (Phase 1b/2) will expand. This initial commit intentionally
does NOT alter existing status semantics; it only records observable data so
we can compare legacy BFS reachability vs. upcoming strict upstream L3 logic.

Design goals:
  * Deterministic (insertion order preserved by capturing sorted device ids)
  * Lock‑protected for recompute cycles (simple RLock; single writer pattern)
  * Opaque to callers except via exported read API / debug endpoint

Data model (Phase 1 minimal):
  device_id -> {
      "upstream_l3_ok": bool,          # For routers: result of trace_l3_path_to_anchor, else False (placeholder)
      "anchor": str|None,              # Anchor id if L3 path ok (routers only now)
      "chain": list[str],              # Device id chain (routers only now)
      "reason_codes": list[str],       # Empty or single legacy placeholder value
      "legacy_bfs_reachable": bool,    # Current BFS propagation membership
      "ts": float                      # Monotonic timestamp when recorded
  }

Reason code placeholders (English, stable identifiers):
  LEGACY_ONLY  – Entry created before unified status logic; non‑router L3 path not yet evaluated.
  NO_L3_PATH   – Router trace failed (reason from dependency_resolver will replace later).

Future phases will: populate full reason codes, add optical flags, and restructure
non‑router evaluation.
"""

from __future__ import annotations

from threading import RLock
from time import perf_counter
from typing import TypedDict


class DeviceDiagnostics(TypedDict, total=False):
    upstream_l3_ok: bool
    anchor: str | None
    chain: list[str]
    reason_codes: list[str]
    legacy_bfs_reachable: bool
    ts: float


_LOCK = RLock()
_DATA: dict[str, DeviceDiagnostics] = {}


def set_device_diag(
    device_id: str,
    *,
    upstream_l3_ok: bool,
    anchor: str | None,
    chain: list[str] | None,
    reason_codes: list[str],
    legacy_bfs_reachable: bool,
) -> None:
    with _LOCK:
        _DATA[device_id] = DeviceDiagnostics(
            upstream_l3_ok=upstream_l3_ok,
            anchor=anchor,
            chain=chain or [],
            reason_codes=reason_codes,
            legacy_bfs_reachable=legacy_bfs_reachable,
            ts=perf_counter(),
        )


def snapshot() -> dict[str, DeviceDiagnostics]:
    """Return a shallow copy of the current diagnostics for debug exposure."""
    with _LOCK:
        # Sorted for determinism
        return {k: _DATA[k] for k in sorted(_DATA.keys())}


__all__ = ["set_device_diag", "snapshot", "DeviceDiagnostics"]
