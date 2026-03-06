"""Metrics aggregation & diff emission (TASK-053).

Consumes leaf traffic samples per tick, aggregates upstream via logical graph,
computes utilization using device.capacity (Mbps), diffs against last snapshot,
and emits deviceMetricsUpdated events for devices with meaningful changes.

EPSILON and bucket thresholds aligned with frontend color scale.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import networkx as nx

from backend import events
from backend.constants.metrics import EPSILON_METRICS_DELTA, utilization_bucket
from backend.db import get_session
from backend.models import Device, Interface, Link
from backend.services.catalog_effective import (
    get_effective_device_capacity_mbps,
    get_effective_interface_capacity_mbps,
)
from backend.services.pathfinding import DeviceRecord, LinkRecord, build_logical_graph

# Constants centralized in backend.constants.metrics


@dataclass
class DeviceMetrics:
    device_id: str
    bps: float
    utilization: float  # 0..inf (1.0 == 100%)


class MetricsService:
    def __init__(self) -> None:
        # last snapshot by device_id
        self._last: dict[str, tuple[float, float, int]] = {}
        # (bps, utilization, bucket)
        self._last_tick = 0
        # last snapshot by link_id
        self._last_links: dict[str, tuple[float, float, int]] = {}

    def _load_graph_inputs(self) -> tuple[list[DeviceRecord], list[LinkRecord]]:
        with get_session() as s:
            devs = s.exec(nx.sqlalchemy.select(Device)).all()  # type: ignore[attr-defined]
        # Fallback: if networkx.sqlalchemy not present, construct via SQLModel select
        if not devs:
            from sqlmodel import select

            with get_session() as s2:
                dev_rows = s2.exec(select(Device)).all()
                # Minimal reconstruction via topology helper avoids duplicating mapping logic.
                # To avoid duplication, reconstruct using the same technique as topology endpoint:
                from backend.api.endpoints.topology import (
                    _collect_recs as _topo_collect,  # type: ignore
                )

                try:
                    d_recs, l_recs = _topo_collect()
                except Exception:
                    # Fallback local construction (id, type only; links empty)
                    d_recs = [DeviceRecord(id=d.id, type=d.type.value) for d in dev_rows]
                    l_recs = []
                return d_recs, l_recs
        # Should not reach here in normal code path; keeping stub for completeness
        return [], []

    def _build_graph(self) -> tuple[nx.Graph, dict[str, tuple[str, str]]]:
        """Build current logical graph and provide link endpoint interface ids.

        Returns:
            (graph, link_endpoints) where link_endpoints maps link_id -> (a_if_id, b_if_id)
        """
        # Load devices and links
        from sqlmodel import select

        with get_session() as s:
            dev_rows = s.exec(select(Device)).all()
            link_rows = s.exec(select(Link)).all()

        d_recs = [DeviceRecord(id=d.id, type=d.type.value) for d in dev_rows]
        l_recs = [
            LinkRecord(
                id=link.id,
                a_device_id=(
                    link.a_interface_id[:-4]
                    if link.a_interface_id.endswith("-if0")
                    else link.a_interface_id
                ),
                b_device_id=(
                    link.b_interface_id[:-4]
                    if link.b_interface_id.endswith("-if0")
                    else link.b_interface_id
                ),
                kind=link.kind.value if hasattr(link.kind, "value") else str(link.kind),
            )
            for link in link_rows
        ]
        # Build a fresh logical graph snapshot each time to avoid stale caches in tests
        # and ensure immediate reflection of topology mutations.
        g = build_logical_graph(d_recs, l_recs, relaxed=False)
        # Build link_id -> (a_if, b_if) mapping for capacity resolution
        link_endpoints: dict[str, tuple[str, str]] = {
            row.id: (row.a_interface_id, row.b_interface_id) for row in link_rows
        }
        return g, link_endpoints

    def process_tick(self, samples: Iterable[tuple[str, float]], tick: int) -> None:
        """Process one tick worth of leaf samples.

        Args:
            samples: Iterable of (device_id, bps).
            tick: Tick sequence number (for debug/emission ordering).
        """
        # 1) Aggregate leaf bps into a working map per device
        base: dict[str, float] = {}
        for did, bps in samples:
            base[did] = base.get(did, 0.0) + float(bps)

        # 2) Build logical graph and push sums upstream by BFS from leaves
        g, link_endpoints = self._build_graph()
        # Initialize totals map with leaf base
        totals: dict[str, float] = dict(base)
        # Per-link totals accumulator
        link_totals: dict[str, float] = {}
        # Define anchors (logical upstream) and route each leaf to its nearest anchor.
        anchors = [
            n
            for n, data in g.nodes(data=True)
            if data.get("type") in {"BACKBONE_GATEWAY", "CORE_ROUTER"}
        ]
        for leaf_id, leaf_bps in base.items():
            if not g.has_node(leaf_id):
                continue
            # Choose nearest anchor by shortest path length
            best_path: list[str] | None = None
            best_len: int | None = None
            for a in anchors:
                try:
                    path = nx.shortest_path(g, source=leaf_id, target=a)
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
                plen = len(path)
                if best_len is None or plen < best_len:
                    best_len = plen
                    best_path = path  # type: ignore[assignment]
            if not best_path or len(best_path) < 2:
                continue
            # Bump device totals along the path (excluding the leaf itself)
            for node in best_path[1:]:
                totals[node] = totals.get(node, 0.0) + leaf_bps
            # Accumulate link totals for each hop along the path
            for u, v in zip(best_path[:-1], best_path[1:], strict=True):
                data = g.get_edge_data(u, v) or {}
                if not data.get("synthetic", False):
                    link_id = data.get("id")
                    if isinstance(link_id, str):
                        link_totals[link_id] = link_totals.get(link_id, 0.0) + leaf_bps

        # 3) Compute utilization (capacity Mbps → convert to bps)
        with get_session() as s:
            from sqlmodel import select

            dev_rows = s.exec(select(Device)).all()
            dev_util: dict[str, float] = {}
            for d in dev_rows:
                cap_mbps = get_effective_device_capacity_mbps(s, d)
                bps_d = totals.get(d.id, 0.0)
                if cap_mbps is None or cap_mbps <= 0:
                    dev_util[d.id] = 0.0 if bps_d <= 0 else float("inf")
                else:
                    dev_util[d.id] = bps_d / (cap_mbps * 1_000_000.0)

        # 4) Diff vs last snapshot and emit if significant (devices)
        changed: list[dict] = []
        for did, u in dev_util.items():
            b = utilization_bucket(u)
            prev = self._last.get(did)
            if prev is None:
                # First snapshot: emit only for devices with non-zero traffic or non-zero capacity util
                if totals.get(did, 0.0) > 0.0:
                    changed.append({"id": did, "bps": totals.get(did, 0.0), "utilization": u})
                    self._last[did] = (totals.get(did, 0.0), u, b)
                else:
                    self._last[did] = (0.0, 0.0, utilization_bucket(0.0))
                continue
            prev_bps, prev_u, prev_bucket = prev
            delta = abs(u - prev_u)
            bucket_changed = b != prev_bucket
            if bucket_changed or delta >= EPSILON_METRICS_DELTA:
                changed.append({"id": did, "bps": totals.get(did, 0.0), "utilization": u})
                self._last[did] = (totals.get(did, 0.0), u, b)
            # else unchanged, keep previous snapshot

        if changed:
            evt = events.Event(type="deviceMetricsUpdated", payload={"devices": changed, "tick": tick})  # type: ignore[arg-type]
            events.publish(evt)
        # Track last processed tick for snapshot endpoint
        self._last_tick = tick

        # 5) Compute link utilizations and emit link deltas
        # Resolve per-link capacity in Mbps using interface capacities (min of endpoints) or default
        DEFAULT_LINK_CAP_MBPS = 1000.0
        link_changed: list[dict] = []
        if link_totals:
            with get_session() as s:
                from sqlmodel import select

                # Preload interfaces into a map
                if_ids = set()
                for lid, (a_if, b_if) in link_endpoints.items():
                    if lid in link_totals:
                        if_ids.add(a_if)
                        if_ids.add(b_if)
                if_rows = s.exec(select(Interface)).all()
                cap_map: dict[str, int | None] = {}
                for i in if_rows:
                    if i.id in if_ids:
                        cap_map[i.id] = get_effective_interface_capacity_mbps(s, i)

            for link_id, bps in link_totals.items():
                a_if, b_if = link_endpoints.get(link_id, ("", ""))
                cap_a = cap_map.get(a_if)
                cap_b = cap_map.get(b_if)
                # Determine capacity Mbps
                cap_candidates = [c for c in [cap_a, cap_b] if c is not None and c > 0]
                cap_mbps = float(min(cap_candidates)) if cap_candidates else DEFAULT_LINK_CAP_MBPS
                if cap_mbps <= 0:
                    l_util = 0.0 if bps <= 0 else float("inf")
                else:
                    l_util = bps / (cap_mbps * 1_000_000.0)
                bucket = utilization_bucket(l_util)
                prev = self._last_links.get(link_id)
                if prev is None:
                    if bps > 0.0:
                        link_changed.append({"id": link_id, "bps": bps, "utilization": l_util})
                        self._last_links[link_id] = (bps, l_util, bucket)
                    else:
                        self._last_links[link_id] = (0.0, 0.0, utilization_bucket(0.0))
                else:
                    prev_bps, prev_u, prev_bucket = prev
                    delta = abs(l_util - prev_u)
                    if bucket != prev_bucket or delta >= EPSILON_METRICS_DELTA:
                        link_changed.append({"id": link_id, "bps": bps, "utilization": l_util})
                        self._last_links[link_id] = (bps, l_util, bucket)

        if link_changed:
            evt2 = events.Event(
                type="linkMetricsUpdated", payload={"links": link_changed, "tick": tick}
            )  # type: ignore[arg-type]
            events.publish(evt2)

    def get_snapshot(self) -> dict:
        """Return a JSON-ready snapshot of the latest device metrics.

        Utilization values that are infinite are clamped to a large finite number for JSON safety.
        """
        devices: dict[str, dict] = {}
        for did, (bps, u, _b) in self._last.items():
            # Clamp infinite to large finite to avoid JSON Infinity
            util = 1e9 if u == float("inf") else u
            devices[did] = {"bps": float(bps), "utilization": float(util), "version": 0}
        links: dict[str, dict] = {}
        for lid, (bps, u, _b) in self._last_links.items():
            util = 1e9 if u == float("inf") else u
            links[lid] = {"bps": float(bps), "utilization": float(util), "version": 0}
        return {"lastTick": int(self._last_tick), "devices": devices, "links": links}


METRICS = MetricsService()
