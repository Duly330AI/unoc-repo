"""Traffic V2 tick helpers for leaf demand generation.

This module generates per-leaf demand deterministically and aggregates
per-device and per-link totals along the chosen path to an anchor.
"""

from __future__ import annotations

import time as _time
from collections import defaultdict
from collections.abc import Callable, Iterable

from sqlmodel import Session

from backend.models import Device, DeviceType, Status, Tariff
from backend.services.traffic.v2_path import bfs_pick_anchor

from .rand import deterministic_rand01


def generate_flows_for_leaves(
    engine,
    session: Session,
    leaves: Iterable[Device],
    tariffs: Iterable[Tariff],
    status_by_id: dict[str, Status],
    allowed_device_ids: set[str],
    device_neighbors: dict[str, set[str]],
    link_by_pair: dict[frozenset[str], str],
    dev_type_by_id: dict[str, DeviceType],
    anchor_types: set[DeviceType],
    tick: int,
    rand01: Callable[[int, int, str], float] = deterministic_rand01,
    observe_phase: Callable[[str, float], None] | None = None,
) -> tuple[
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    int,
    dict[str, dict],
]:
    """Generate demand for eligible leaves and aggregate along selected paths.

    Returns per-device up/down totals, per-link up/down totals, leaves_count, and
    debug info for last generated flows (for engine._debug_last_generated).
    """
    per_device_totals: dict[str, float] = defaultdict(float)
    per_device_down_totals: dict[str, float] = defaultdict(float)
    per_link_totals: dict[str, float] = defaultdict(float)
    per_link_down_totals: dict[str, float] = defaultdict(float)
    leaves_count = 0

    tariff_by_id = {t.id: t for t in tariffs if t.id is not None}
    debug_generated: dict[str, dict] = {}

    # Optional sub-phase observer (provided by engine to avoid import cycles)
    _obs = observe_phase

    for d in leaves:
        try:
            # Generate traffic only when the device is effectively UP.
            if status_by_id.get(d.id) != Status.UP:
                continue
            t_id = d.tariff_id
            if t_id is None:
                continue
            tf = tariff_by_id.get(t_id)
            if tf is None:
                continue
            # Deterministic demand per leaf and tick (deferred commit until path confirmed)
            _t_dem = _time.perf_counter()
            r = rand01(engine.random_seed, tick, d.id)
            pending_up_bps = float(max(tf.max_up_mbps, 0.0)) * 1e6 * float(r)
            pending_down_bps = float(max(tf.max_down_mbps, 0.0)) * 1e6 * float(r)
            if _obs is not None:
                try:
                    _obs("demand_calc", _time.perf_counter() - _t_dem)
                except Exception:
                    pass

            # Build path to the nearest anchor via helper (BFS + deterministic fallback)
            # Use engine path cache (topology-versioned) to avoid repeated pathfinding per tick
            _t_path = _time.perf_counter()
            cached = None
            try:
                cached = getattr(engine, "_get_cached_path", None)
                cached = cached(d.id) if callable(cached) else None
            except Exception:
                cached = None
            if isinstance(cached, tuple) and len(cached) == 2:
                try:
                    path_nodes, path_links = list(cached[0]), list(cached[1])
                except Exception:
                    path_nodes, path_links = [], []
            else:
                path_nodes, path_links = bfs_pick_anchor(
                    start_id=d.id,
                    device_neighbors=device_neighbors,
                    link_by_pair=link_by_pair,
                    allowed_device_ids=allowed_device_ids,
                    dev_type_by_id=dev_type_by_id,
                    anchor_types=anchor_types,
                )
            if _obs is not None:
                try:
                    _obs("path_lookup", _time.perf_counter() - _t_path)
                except Exception:
                    pass

            # If no anchor path was established (path_nodes only leaf), attempt a deterministic
            # fallback using the dependency resolver's L3/anchor chain before suppressing.
            if len(path_nodes) <= 1:
                try:
                    from backend.services.dependency_resolver import (
                        has_upstream_l3_or_anchor as _has_up,
                    )

                    up_res = _has_up(session, d)
                    chain: list[str] = list(getattr(up_res, "chain", []) or [])
                    ok: bool = bool(getattr(up_res, "ok", False))
                    if ok and len(chain) > 1:
                        # Map chain devices to links, respecting allowed_device_ids
                        chain_nodes: list[str] = [x for x in chain if x in allowed_device_ids]
                        chain_links: list[str] = []
                        try:
                            for i in range(len(chain_nodes) - 1):
                                pair = frozenset({chain_nodes[i], chain_nodes[i + 1]})
                                lid = link_by_pair.get(pair)
                                if lid and lid not in chain_links:
                                    chain_links.append(lid)
                        except Exception:
                            chain_links = []
                        # Accept only if the chain reaches a true anchor type
                        if chain_nodes and any(
                            (dev_type_by_id.get(x) in anchor_types) and (x != d.id)
                            for x in chain_nodes
                        ):
                            path_nodes, path_links = chain_nodes, chain_links
                except Exception:
                    pass

            # If still no valid path, suppress generation
            if len(path_nodes) <= 1:
                continue

            # Store in path cache after successful path discovery
            try:
                st = getattr(engine, "_store_cached_path", None)
                if callable(st):
                    st(d.id, path_nodes, path_links)
            except Exception:
                pass

            # Commit generation now that a valid path exists
            debug_generated[d.id] = {
                "up_bps": pending_up_bps,
                "down_bps": pending_down_bps,
                "tariff": {
                    "id": t_id,
                    "up_mbps": float(max(tf.max_up_mbps, 0.0)),
                    "down_mbps": float(max(tf.max_down_mbps, 0.0)),
                },
            }

            up_bps = pending_up_bps
            down_bps = pending_down_bps

            # Aggregate along the path
            _t_agg = _time.perf_counter()
            # Use defaultdict accumulators to minimize get/set overhead
            pdt = per_device_totals
            pddt = per_device_down_totals
            plt = per_link_totals
            pldt = per_link_down_totals
            for dev_id in path_nodes:
                pdt[dev_id] += up_bps
                pddt[dev_id] += down_bps
            for lid in path_links:
                plt[lid] += up_bps
                pldt[lid] += down_bps
            if _obs is not None:
                try:
                    _obs("aggregation_map_updates", _time.perf_counter() - _t_agg)
                except Exception:
                    pass

            leaves_count += 1
        except Exception:
            # Best-effort: continue with other leaves
            continue

    return (
        dict(per_device_totals),
        dict(per_device_down_totals),
        dict(per_link_totals),
        dict(per_link_down_totals),
        leaves_count,
        debug_generated,
    )
