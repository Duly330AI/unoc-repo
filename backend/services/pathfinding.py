"""Pathfinding Core Graph Layer (TASK-034A)

Implements versioned adjacency snapshots & graph builders for:
 - Optical Graph (OLT, ONT(+Business), passive inline devices; edges: optical_segment, optical_termination)
 - Logical Upstream Graph (Backbone Gateway, Core Router, Edge Router, OLT, AON Switch, AON CPE, ONT/Business ONT; edges: routed_p2p, access_edge plus synthetic when RELAXED)

Architecture Reference: ARCHITECTURE.md §18 (r5)

This module does NOT perform path resolution (handled in TASK-034B/034C) – it only supplies:
  build_optical_graph(devices, links)
  build_logical_graph(devices, links, relaxed)
and a PathfindingStore that tracks a monotonic topo_version when topology-affecting
mutations occur (device/link add/remove or relevant attribute edits – mutation integration
hooks to be wired where CRUD/provision logic lives).

Design Notes:
 - networkx is used for clarity; if profiling later shows bottlenecks we can replace with
   custom adjacency + heap Dijkstra (see §18.14).
 - For optical weights we attach preliminary attributes (link_loss_db if present). Passive
   insertion loss distribution into edge weights is deferred to TASK-034B (need full path logic).
 - Synthetic edges (RELAXED) are annotated with attribute {'synthetic': True}.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from threading import RLock
from typing import Any

import networkx as nx

# Device type groups (keep in sync with architecture §2 / §18)
OPTICAL_ACTIVE = {"OLT"}
OPTICAL_TERMINATORS = {"ONT", "BUSINESS_ONT"}
PASSIVE_INLINE = {"ODF", "NVT", "SPLITTER", "HOP"}

LOGICAL_ANCHORS = {"BACKBONE_GATEWAY", "CORE_ROUTER"}
LOGICAL_ACTIVE = LOGICAL_ANCHORS | {
    "EDGE_ROUTER",
    "OLT",  # Include OLT as logical active
    "AON_SWITCH",
    "AON_CPE",
    "ONT",
    "BUSINESS_ONT",
}

# Link class labels expected from classification (rule-based mapping):
OPTICAL_EDGE_CLASSES = {"optical_segment", "optical_termination"}
LOGICAL_EDGE_CLASSES = {"routed_p2p", "access_edge", "access_optical_term"}

# Raw link.kind to provisional classification hints.
LINK_TYPE_RULES = {
    "FIBER": {"logical": True, "optical": True},  # context filtered later
    "P2P": {"logical": True, "optical": False},
    "MGMT": {"logical": False, "optical": False},
}


@dataclass(slots=True)
class DeviceRecord:
    id: str
    type: str
    # additional fields optionally included but ignored here


@dataclass(slots=True)
class LinkRecord:
    id: str
    a_device_id: str
    b_device_id: str
    kind: str  # semantic class (already classified, not raw type)
    # optical attributes (optional) – not all needed yet
    link_loss_db: float | None = None


class PathfindingStore:
    """Holds current topology version & last built graphs.

    The store does not itself watch mutations; external code must call `bump_version()`
    whenever a topology-affecting change occurs (device/link add/remove or attribute
    change influencing path costs / membership).
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._topo_version: int = 0
        self._optical_graph: nx.Graph | None = None
        self._logical_graph: nx.Graph | None = None
        self._relaxed_flag_for_logical: bool | None = None

    def bump_version(self) -> int:
        with self._lock:
            self._topo_version += 1
            # Invalidate built graphs (lazy rebuild on next access)
            self._optical_graph = None
            self._logical_graph = None
            self._relaxed_flag_for_logical = None
            # Invalidate optical path resolver cache without creating import cycles
            try:
                from .optical_path_resolver import resolve_optical_path  # local import

                resolve_optical_path.cache_clear()  # type: ignore[attr-defined]
            except Exception:
                # Best-effort; cache will refresh on next successful import
                pass
            return self._topo_version

    def version(self) -> int:
        return self._topo_version

    def get_optical_graph(
        self, devices: Iterable[DeviceRecord], links: Iterable[LinkRecord]
    ) -> tuple[int, nx.Graph]:
        with self._lock:
            if self._optical_graph is None:
                self._optical_graph = build_optical_graph(devices, links)
            return self._topo_version, self._optical_graph

    def get_logical_graph(
        self,
        devices: Iterable[DeviceRecord],
        links: Iterable[LinkRecord],
        relaxed: bool,
    ) -> tuple[int, nx.Graph]:
        with self._lock:
            if self._logical_graph is None or self._relaxed_flag_for_logical != relaxed:
                self._logical_graph = build_logical_graph(devices, links, relaxed)
                self._relaxed_flag_for_logical = relaxed
            return self._topo_version, self._logical_graph


def build_optical_graph(devices: Iterable[DeviceRecord], links: Iterable[LinkRecord]) -> nx.Graph:
    g = nx.Graph()
    # Add nodes (only those relevant in optical projection)
    for d in devices:
        if d.type in OPTICAL_ACTIVE or d.type in OPTICAL_TERMINATORS or d.type in PASSIVE_INLINE:
            g.add_node(d.id, type=d.type)

    # Add edges for qualifying link classes where both endpoints exist in optical node set
    node_set = g.nodes
    for link in links:
        if link.a_device_id not in node_set or link.b_device_id not in node_set:
            continue
        # Accept already classified semantic kinds directly
        if link.kind in OPTICAL_EDGE_CLASSES:
            attrs: dict[str, Any] = {"id": link.id, "class": link.kind}
            if link.link_loss_db is not None:
                attrs["link_loss_db"] = link.link_loss_db
            g.add_edge(link.a_device_id, link.b_device_id, **attrs)
            continue
        # Backwards compatibility: raw FIBER classification fallback
        if link.kind == "FIBER":
            a_type = g.nodes[link.a_device_id]["type"]
            b_type = g.nodes[link.b_device_id]["type"]
            pair = {a_type, b_type}
            if ("OLT" in pair and ("ONT" in pair or "BUSINESS_ONT" in pair)) or pair <= (
                OPTICAL_ACTIVE | OPTICAL_TERMINATORS | PASSIVE_INLINE
            ):
                g.add_edge(
                    link.a_device_id,
                    link.b_device_id,
                    **{"id": link.id, "class": "optical_segment"},
                )
    return g


def build_logical_graph(
    devices: Iterable[DeviceRecord], links: Iterable[LinkRecord], relaxed: bool
) -> nx.Graph:
    g = nx.Graph()
    for d in devices:
        if d.type in LOGICAL_ACTIVE:
            g.add_node(d.id, type=d.type)

    node_set = g.nodes
    for link in links:
        if link.a_device_id not in node_set or link.b_device_id not in node_set:
            continue
        if link.kind in LOGICAL_EDGE_CLASSES:
            g.add_edge(
                link.a_device_id,
                link.b_device_id,
                **{"id": link.id, "class": link.kind, "synthetic": False},
            )
            continue
        # Backwards compatibility for raw kinds
        if link.kind in {"FIBER", "P2P"}:
            a_type = g.nodes[link.a_device_id]["type"]
            b_type = g.nodes[link.b_device_id]["type"]
            pair = {a_type, b_type}
            if link.kind == "FIBER" and pair <= (LOGICAL_ACTIVE | LOGICAL_ANCHORS):
                g.add_edge(
                    link.a_device_id,
                    link.b_device_id,
                    **{"id": link.id, "class": "routed_p2p", "synthetic": False},
                )
            elif link.kind == "P2P":
                g.add_edge(
                    link.a_device_id,
                    link.b_device_id,
                    **{"id": link.id, "class": "routed_p2p", "synthetic": False},
                )

    # Collapsed Optical Access Edge logic:
    # For every ONT / BUSINESS_ONT, if there exists an optical path (through passive inline devices)
    # to an OLT, add a synthetic logical edge ONT<->OLT so that upstream L3 evaluation sees
    # the ONT as logically attached. Deterministic selection: shortest hop count (optical
    # path length in devices), then lexicographic tuple of device ids in that path.
    try:
        # Build a lightweight optical adjacency for collapse computation (only ONT/BUSINESS_ONT, OLT, passive inline)
        optical_nodes: dict[str, str] = {}
        for d in devices:
            if d.type in OPTICAL_ACTIVE | OPTICAL_TERMINATORS | PASSIVE_INLINE:
                optical_nodes[d.id] = d.type
        # Build undirected adjacency limited to optical edge classes derived from links
        from collections import defaultdict

        opt_adj: dict[str, set[str]] = defaultdict(set)
        for link in links:
            # We rely on original link.kind (semantic classification for optical graph uses FIBER also)
            if link.a_device_id not in optical_nodes or link.b_device_id not in optical_nodes:
                continue
            # Accept any link that would appear in optical graph (FIBER or classified optical classes)
            # Simplify: treat all qualifying raw kinds as usable optical continuity.
            opt_adj[link.a_device_id].add(link.b_device_id)
            opt_adj[link.b_device_id].add(link.a_device_id)

        def _shortest_optical_path(src: str, dst_candidates: set[str]) -> list[str] | None:
            import heapq

            if src not in optical_nodes:
                return None
            # Dijkstra with unit weights (equivalent to BFS but deterministic ordering via heap & tie-break)
            visited: set[str] = set()
            heap: list[tuple[int, tuple[str, ...], str]] = []
            heapq.heappush(heap, (0, (src,), src))
            best_paths: dict[str, tuple[int, tuple[str, ...]]] = {src: (0, (src,))}
            target_paths: list[tuple[int, tuple[str, ...]]] = []
            while heap:
                dist, path_tuple, node = heapq.heappop(heap)
                if node in visited:
                    continue
                visited.add(node)
                if node != src and node in dst_candidates:
                    target_paths.append((dist, path_tuple))
                    # We do not break; we must still discover equally short paths to compare lexicographically
                for nb in sorted(
                    opt_adj.get(node, ())
                ):  # sorted ensures deterministic neighbor order
                    if nb in visited:
                        continue
                    nd = dist + 1
                    cand = (nd, path_tuple + (nb,))
                    prev = best_paths.get(nb)
                    if prev is None or cand < prev:
                        best_paths[nb] = cand
                        heapq.heappush(heap, (nd, cand[1], nb))
            if not target_paths:
                return None
            target_paths.sort(key=lambda t: (t[0], t[1]))
            return list(target_paths[0][1])

        # Precompute set of OLT ids present in optical domain
        olt_ids = {d_id for d_id, t in optical_nodes.items() if t == "OLT"}
        if olt_ids:
            for d_id, d_type in optical_nodes.items():
                if d_type in {"ONT", "BUSINESS_ONT"}:
                    path = _shortest_optical_path(d_id, olt_ids)
                    if not path or len(path) < 2:
                        continue  # no path or trivial
                    olt_endpoint = path[-1]
                    # Add synthetic logical edge if both endpoints are already logical-active nodes in g
                    if (
                        d_id in g.nodes
                        and olt_endpoint in g.nodes
                        and not g.has_edge(d_id, olt_endpoint)
                    ):
                        g.add_edge(
                            d_id,
                            olt_endpoint,
                            **{
                                "id": f"collapsed_optical:{d_id}->{olt_endpoint}",
                                "class": "access_optical_term",
                                "synthetic": True,
                            },
                        )
    except Exception:
        # Fail-safe: never break logical graph construction due to collapse logic errors
        pass

    if relaxed:
        # Synthetic edges: OLT -> any Core Router if not already connected; AON Switch -> Core Router
        # Simple heuristic: connect each OLT / AON Switch to lexicographically lowest Core Router.
        core_ids = sorted(
            [n for n, data in g.nodes(data=True) if data.get("type") == "CORE_ROUTER"]
        )
        if core_ids:
            core_anchor = core_ids[0]
            for n, data in list(g.nodes(data=True)):
                t = data.get("type")
                if t in {"OLT", "AON_SWITCH"} and not g.has_edge(n, core_anchor):
                    g.add_edge(
                        n,
                        core_anchor,
                        **{
                            "id": f"synthetic:{n}->{core_anchor}",
                            "class": "synthetic_relaxed",
                            "synthetic": True,
                        },
                    )
    return g


# Singleton store instance (mirrors pattern used by layout_state)
PATHFINDING_STORE = PathfindingStore()
