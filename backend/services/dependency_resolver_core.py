"""Core utilities for upstream dependency evaluation (split from dependency_resolver).

Contains dataclasses, graph input collection, legacy wrapper, and the unified
has_upstream_l3_or_anchor() diagnostic. Behavior preserved; imports unchanged for callers
via the re-export shim in dependency_resolver.py.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from threading import RLock

from sqlmodel import Session, select

from backend.models import Device, DeviceType, Interface, Link, Status
from backend.services.pathfinding import (
    PATHFINDING_STORE,
    DeviceRecord,
    LinkRecord,
    build_logical_graph,
)


@dataclass
class DependencyCheckResult:
    """(Deprecated) Retained for callers expecting the symbol.

    New logic should rely on UpstreamL3Result and trace_l3_path_to_anchor.
    """

    ok: bool
    reason: str | None = None
    chain: list[str] | None = None  # upstream chain


@dataclass
class UpstreamL3Result:
    """Unified upstream L3 / anchor evaluation for any device type (diagnostics).

    Deterministic ordering: shortest path length first, tie-broken lexicographically.
    """

    ok: bool
    anchor: str | None
    chain: list[str]
    reasons: list[str]


# Topology-versioned memoization for unified upstream evaluation.
#
# Key design points:
# - Bound strictly to PATHFINDING_STORE.version() so any topology-affecting
#   change (device/link CRUD, admin override integrated with bump_version) fully
#   invalidates the map, ensuring correctness with deterministic results.
# - Thread-safe via a module-level lock; function is called during recompute and
#   request paths (FastAPI), where multiple threads may be active.
_UPSTREAM_CACHE_LOCK = RLock()
_UPSTREAM_CACHE: dict[str, object] = {"version": -1, "override_fp": None, "map": {}}


def _compute_override_fingerprint(session: Session) -> tuple[int, int, int, int]:
    """Return a lightweight fingerprint of admin overrides across devices and links.

    Tuple: (n_dev_up, n_dev_down, n_link_up, n_link_down)
    Any change toggling overrides will change this tuple, triggering cache invalidation.
    """
    try:
        from backend.models import Link as _Link

        dev_rows = session.exec(select(Device)).all()
        link_rows = session.exec(select(_Link)).all()
        n_dev_up = 0
        n_dev_down = 0
        for d in dev_rows:
            v = getattr(d, "admin_override_status", None)
            if v is None:
                continue
            if (hasattr(v, "value") and v.value == "UP") or (
                not hasattr(v, "value") and str(v) == "UP"
            ):
                n_dev_up += 1
            elif (hasattr(v, "value") and v.value == "DOWN") or (
                not hasattr(v, "value") and str(v) == "DOWN"
            ):
                n_dev_down += 1
        n_link_up = 0
        n_link_down = 0
        for ln in link_rows:
            v = getattr(ln, "admin_override_status", None)
            if v is None:
                continue
            if (hasattr(v, "value") and v.value == "UP") or (
                not hasattr(v, "value") and str(v) == "UP"
            ):
                n_link_up += 1
            elif (hasattr(v, "value") and v.value == "DOWN") or (
                not hasattr(v, "value") and str(v) == "DOWN"
            ):
                n_link_down += 1
        return (n_dev_up, n_dev_down, n_link_up, n_link_down)
    except Exception:
        # On any error, return a neutral value that won't spuriously invalidate repeatedly
        return (-1, -1, -1, -1)


def _collect_devices_links(
    session: Session,
) -> tuple[list[DeviceRecord], list[LinkRecord], dict[str, str]]:
    """Collect devices/links and interface->device map with optional per-session cache."""
    use_cache = os.getenv("UNOC_DEP_CACHE", "1") != "0"
    cache = session.info.get("_dep_cache") if use_cache else None

    if cache and cache.get("devices") is not None and cache.get("links") is not None:
        return cache["devices"], cache["links"], cache["if_to_dev"]

    dev_rows = session.exec(select(Device)).all()
    # Exclude devices administratively forced DOWN from dependency graphs
    dev_allowed = [d for d in dev_rows if getattr(d, "admin_override_status", None) != Status.DOWN]
    link_rows = session.exec(select(Link)).all()
    if_rows = session.exec(select(Interface)).all()
    devices = [DeviceRecord(id=d.id, type=d.type.value) for d in dev_allowed]
    allowed_ids = {d.id for d in dev_allowed}
    # Map interface id -> device id using actual Interface rows
    if_to_dev = {i.id: i.device_id for i in if_rows}
    links: list[LinkRecord] = []
    for link in link_rows:
        # Inline passability check to avoid per-link DB lookups
        try:
            lov = getattr(link, "admin_override_status", None)
            if lov is not None:
                lov_up = (str(lov) == "UP") or (hasattr(lov, "value") and lov.value == "UP")
                if not lov_up:
                    continue
            else:
                stv = getattr(link, "status", None)
                stv_up = (stv is not None) and (
                    (str(stv) == "UP")
                    or (hasattr(stv, "value") and getattr(stv, "value", None) == "UP")
                )
                if not stv_up:
                    continue
        except Exception:
            # On any unexpected attribute issue, conservatively skip the link
            continue

        a_dev = if_to_dev.get(link.a_interface_id)
        b_dev = if_to_dev.get(link.b_interface_id)
        # Fallback to legacy '-if0' suffix derivation only if necessary
        if not a_dev:
            a_dev = (
                link.a_interface_id[:-4]
                if link.a_interface_id and link.a_interface_id.endswith("-if0")
                else None
            )
        if not b_dev:
            b_dev = (
                link.b_interface_id[:-4]
                if link.b_interface_id and link.b_interface_id.endswith("-if0")
                else None
            )
        if not a_dev or not b_dev:
            # Skip malformed links we cannot resolve to devices
            continue
        # Respect admin DOWN filtering: skip links attached to excluded devices
        if a_dev not in allowed_ids or b_dev not in allowed_ids:
            continue
        links.append(
            LinkRecord(id=link.id, a_device_id=a_dev, b_device_id=b_dev, kind=link.kind.value)
        )

    if use_cache:
        session.info["_dep_cache"] = {
            "devices": devices,
            "links": links,
            "if_to_dev": if_to_dev,
        }

    return devices, links, if_to_dev


def evaluate_upstream_dependencies(
    session: Session, device: Device
) -> DependencyCheckResult:  # pragma: no cover - deprecated wrapper
    """Deprecated legacy BFS-style dependency check wrapper.

    Delegates to trace_l3_path_to_anchor for routers; uses unified diagnostic for others.
    """
    if device.type in {DeviceType.CORE_ROUTER, DeviceType.EDGE_ROUTER, DeviceType.BACKBONE_GATEWAY}:
        # Local import to avoid cycle
        from .dependency_resolver_trace import trace_l3_path_to_anchor

        res = trace_l3_path_to_anchor(session, device)
        return DependencyCheckResult(ok=res.ok, reason=res.reason, chain=res.chain)
    # Non-routers: rely on diagnostic outcome; map first reason
    diag = has_upstream_l3_or_anchor(session, device)
    return DependencyCheckResult(
        ok=diag.ok, reason=(diag.reasons[0] if diag.reasons else None), chain=diag.chain
    )


def has_upstream_l3_or_anchor(session: Session, device: Device) -> UpstreamL3Result:
    """Return unified upstream L3 evaluation result for any device type (diagnostics only).

    With a topology-versioned memoization layer to avoid repeated expensive graph
    traversals across the same static topology snapshot.

    Rules:
      1. Routers delegate to trace_l3_path_to_anchor.
      2. Else find candidate routers reachable in logical graph; choose shortest path.
      3. Classify reason buckets when failing: no_router_path, routers_no_l3.
      4. Deterministic tie-breaking: shortest path, then lexicographic path tuple.
    """
    topo_v = PATHFINDING_STORE.version()
    override_fp = _compute_override_fingerprint(session)
    # Determine if this is a router-class device (CORE/EDGE/BACKBONE). We intentionally
    # avoid caching router outcomes because their L3 state depends on routing tables,
    # neighbors, and interface admin flags which are not reflected in the topology version
    # or override fingerprint. Non-routers benefit from memoization.
    is_router = device.type in {
        DeviceType.CORE_ROUTER,
        DeviceType.EDGE_ROUTER,
        DeviceType.BACKBONE_GATEWAY,
    }
    # Topology-versioned cache lookup (non-routers only)
    if not is_router:
        with _UPSTREAM_CACHE_LOCK:
            if (
                _UPSTREAM_CACHE.get("version") != topo_v
                or _UPSTREAM_CACHE.get("override_fp") != override_fp
            ):
                _UPSTREAM_CACHE["version"] = topo_v
                _UPSTREAM_CACHE["override_fp"] = override_fp
                _UPSTREAM_CACHE["map"] = {}
            cache_map = _UPSTREAM_CACHE["map"]  # type: ignore[assignment]
            cached = cache_map.get(device.id) if isinstance(cache_map, dict) else None
            if isinstance(cached, UpstreamL3Result):
                return cached

    # Compute on miss
    result: UpstreamL3Result
    try:
        from backend.models import DeviceType as _DT  # local import to avoid cycles

        # Fast path: routers
        if device.type in {_DT.CORE_ROUTER, _DT.EDGE_ROUTER, _DT.BACKBONE_GATEWAY}:
            from .dependency_resolver_trace import trace_l3_path_to_anchor

            res = trace_l3_path_to_anchor(session, device)
            result = UpstreamL3Result(
                ok=bool(res.ok),
                anchor=(res.chain[-1] if res.ok and res.chain else None),
                chain=res.chain or [device.id],
                reasons=[] if res.ok else [res.reason or "unknown"],
            )
        else:
            # Build / reuse logical graph
            devices, links, _if_to_dev = _collect_devices_links(session)
            logical_g = build_logical_graph(devices, links, relaxed=False)
            if device.id not in logical_g:
                result = UpstreamL3Result(False, None, [device.id], ["device_not_in_graph"])
            else:
                # Gather candidate routers reachable from the device
                router_nodes: list[str] = []
                for n in logical_g.nodes:
                    t = logical_g.nodes[n].get("type")
                    if t in {"CORE_ROUTER", "EDGE_ROUTER", "BACKBONE_GATEWAY"}:
                        try:
                            import networkx as _nx

                            if _nx.has_path(logical_g, device.id, n):
                                router_nodes.append(n)
                        except Exception:
                            continue
                router_nodes_sorted = sorted(router_nodes)
                if not router_nodes_sorted:
                    result = UpstreamL3Result(False, None, [device.id], ["no_router_path"])
                else:
                    # Evaluate each router's L3 chain (cache results per router to avoid recompute)
                    from .dependency_resolver_trace import trace_l3_path_to_anchor

                    router_chain_cache: dict[str, DependencyCheckResult] = {}
                    candidates: list[tuple[int, tuple[str, ...], str, list[str]]] = []
                    for r_id in router_nodes_sorted:
                        r_dev = session.get(Device, r_id)
                        if not r_dev:
                            continue
                        if r_id not in router_chain_cache:
                            router_chain_cache[r_id] = trace_l3_path_to_anchor(session, r_dev)
                        rr = router_chain_cache[r_id]
                        if not rr.ok:
                            continue
                        import networkx as _nx

                        try:
                            dev_to_r = _nx.shortest_path(logical_g, device.id, r_id)  # type: ignore
                        except Exception:
                            continue
                        full_chain = dev_to_r + (rr.chain[1:] if rr.chain else [])
                        anchor = full_chain[-1] if full_chain else None
                        candidates.append(
                            (len(full_chain), tuple(full_chain), anchor or "", full_chain)
                        )
                    if not candidates:
                        result = UpstreamL3Result(False, None, [device.id], ["routers_no_l3"])
                    else:
                        candidates.sort(key=lambda t: (t[0], t[1]))
                        best = candidates[0]
                        result = UpstreamL3Result(True, best[2], list(best[3]), [])
    except Exception:
        result = UpstreamL3Result(False, None, [device.id], ["exception"])

    # Store in cache after successful computation (non-routers only)
    if not is_router:
        try:
            with _UPSTREAM_CACHE_LOCK:
                cmap = _UPSTREAM_CACHE.get("map")
                if isinstance(cmap, dict):
                    cmap[device.id] = result
        except Exception:
            # Never fail due to caching issues
            pass
    return result


__all__ = [
    "DependencyCheckResult",
    "UpstreamL3Result",
    "evaluate_upstream_dependencies",
    "has_upstream_l3_or_anchor",
]
