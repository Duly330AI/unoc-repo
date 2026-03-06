"""Optical path resolver (TASK-034B).

Implements resolve_optical_path(ont_id) using the optical projection from
PATHFINDING_STORE. Edge weights are optical attenuation (fiber length *
attenuation_db_per_km) plus passive device insertion losses encountered at
intermediate nodes.

Deterministic ordering of candidates:
- Primary: total attenuation (dB)
- Secondary: total physical path length (km)
- Tertiary: hop count
- Quaternary: OLT id, then path signature (stable string)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import cast

import networkx as nx
from sqlmodel import select

from backend.constants import FIBER_TYPES
from backend.core.observability import CACHE_OPTICAL_HIT, CACHE_OPTICAL_MISS, OBS
from backend.db import get_session, init_db
from backend.models import Device, Interface, Link, PhysicalMedium
from backend.services.pathfinding import PATHFINDING_STORE, DeviceRecord, LinkRecord

# Optional Prometheus counters imported lazily from metrics endpoint to avoid duplicate collectors
try:  # pragma: no cover
    from backend.api.endpoints.metrics import OPTICAL_CACHE_HITS as _PROM_HITS  # type: ignore
    from backend.api.endpoints.metrics import OPTICAL_CACHE_MISSES as _PROM_MISSES  # type: ignore
except Exception:  # pragma: no cover
    _PROM_HITS = None  # type: ignore[assignment]
    _PROM_MISSES = None  # type: ignore[assignment]


@dataclass(slots=True, frozen=True)
class PathSegment:
    src: str
    dst: str
    link_id: str | None
    attenuation_db: float


@dataclass(slots=True, frozen=True)
class OpticalPathResult:
    olt_id: str
    total_attenuation_db: float
    segments: tuple[PathSegment, ...]


def _build_records() -> tuple[list[DeviceRecord], list[LinkRecord]]:
    """Read current DB snapshot and turn into records for PATHFINDING_STORE."""
    init_db()
    with get_session() as s:
        devices = s.exec(select(Device)).all()
        links = s.exec(select(Link)).all()
        # Build a stable mapping from interface ID -> parent device ID
        interfaces = s.exec(select(Interface)).all()
        if_to_dev = {i.id: i.device_id for i in interfaces}

    # Use enum values (e.g., 'OLT') instead of str(enum) (e.g., 'DeviceType.OLT')
    d_recs = [
        DeviceRecord(id=d.id, type=d.type.value if hasattr(d.type, "value") else str(d.type))
        for d in devices
    ]
    l_recs: list[LinkRecord] = []
    for link in links:
        # Resolve interface endpoints to their owning device IDs. This avoids relying on
        # fragile suffix heuristics and ensures the optical graph receives device nodes.
        a_dev = if_to_dev.get(link.a_interface_id)
        b_dev = if_to_dev.get(link.b_interface_id)
        # Conservative fallback for legacy "-if0" default interface IDs
        if (
            not a_dev
            and isinstance(link.a_interface_id, str)
            and link.a_interface_id.endswith("-if0")
        ):
            a_dev = link.a_interface_id[:-4]
        if (
            not b_dev
            and isinstance(link.b_interface_id, str)
            and link.b_interface_id.endswith("-if0")
        ):
            b_dev = link.b_interface_id[:-4]
        # Skip malformed links we cannot map to devices
        if not a_dev or not b_dev:
            continue
        l_recs.append(
            LinkRecord(
                id=link.id,
                a_device_id=a_dev,
                b_device_id=b_dev,
                # Use enum value (e.g., 'FIBER') for compatibility with graph builder
                kind=link.kind.value if hasattr(link.kind, "value") else str(link.kind),
                link_loss_db=None,  # per-edge precomputed not used here
            )
        )
    return d_recs, l_recs


PASSIVE_NODE_TYPES = {"SPLITTER", "HOP", "NVT", "ODF"}


def _edge_loss_db(g: nx.Graph, u: str, v: str) -> float:
    """Compute attenuation for edge (u, v).

    - Fiber loss from Link fields: length_km * attenuation_db_per_km derived
      from the selected PhysicalMedium (if set)
    - Passive device insertion loss: add insertion_loss_db for intermediate node
      when traversing into that node (i.e., for every interior node in path).
    """
    data = g.get_edge_data(u, v) or {}
    link_id = data.get("id")
    fiber_loss = 0.0
    if link_id:
        # Read link fields directly from DB to avoid duplicating them on the graph
        init_db()
        with get_session() as s:
            link_obj = s.get(Link, link_id)
            if (
                link_obj
                and link_obj.length_km is not None
                and link_obj.physical_medium_id is not None
            ):
                pm = s.get(PhysicalMedium, link_obj.physical_medium_id)
                if pm and pm.code in FIBER_TYPES:
                    fiber_loss = float(link_obj.length_km) * float(
                        FIBER_TYPES[pm.code].attenuation_db_per_km
                    )
    return float(fiber_loss)


def _path_total_loss(g: nx.Graph, path: Sequence[str]) -> float:
    total = 0.0
    # Edge contributions
    for i in range(len(path) - 1):
        total += _edge_loss_db(g, path[i], path[i + 1])
    # Passive insertion on interior nodes (exclude endpoints)
    if len(path) >= 3:
        init_db()
        with get_session() as s:
            for node_id in path[1:-1]:
                d = s.get(Device, node_id)
                if d and d.insertion_loss_db:
                    total += float(d.insertion_loss_db)
    return float(total)


def _path_total_length_km(g: nx.Graph, path: Sequence[str]) -> float:
    """Compute total physical path length (km) for the given node path.

    Only sums known Link.length_km values for edges present. Missing values
    contribute 0 to avoid inflating unknowns; this keeps the tie-break
    deterministic without changing attenuation semantics.
    """
    total_km = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edata = g.get_edge_data(u, v) or {}
        link_id = edata.get("id")
        if not link_id:
            continue
        init_db()
        with get_session() as s:
            link_obj = s.get(Link, link_id)
            if link_obj and link_obj.length_km is not None:
                total_km += float(link_obj.length_km)
    return float(total_km)


def _segments(g: nx.Graph, path: Sequence[str]) -> tuple[PathSegment, ...]:
    segs: list[PathSegment] = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edata = g.get_edge_data(u, v) or {}
        lid = edata.get("id")
        segs.append(PathSegment(src=u, dst=v, link_id=lid, attenuation_db=_edge_loss_db(g, u, v)))
    return tuple(segs)


def _is_olt(g: nx.Graph, node_id: str) -> bool:
    t = (g.nodes.get(node_id) or {}).get("type")
    return t == "OLT"


@lru_cache(maxsize=10_000)
def resolve_optical_path(ont_id: str) -> OpticalPathResult | None:
    """Resolve the minimal-attenuation path from ONT to any reachable OLT.

    Returns None if no path exists.
    """
    # Use latest cached optical graph snapshot from PATHFINDING_STORE.
    d_recs, l_recs = _build_records()
    _, g = PATHFINDING_STORE.get_optical_graph(d_recs, l_recs)
    if ont_id not in g:
        OBS.inc(CACHE_OPTICAL_MISS)
        if _PROM_MISSES is not None:
            try:
                _PROM_MISSES.inc()
            except Exception:
                pass
        return None

    # Dijkstra from ONT with custom weight (fiber loss + passive insertion entering target)
    def weight_fn(u: str, v: str, data: dict) -> float:  # type: ignore[no-redef]
        w = _edge_loss_db(g, u, v)
        v_type = (g.nodes.get(v) or {}).get("type")
        if v_type in PASSIVE_NODE_TYPES:
            # Add insertion if available
            init_db()
            with get_session() as s:
                dev = s.get(Device, v)
                if dev and dev.insertion_loss_db is not None:
                    w += float(dev.insertion_loss_db)
        return float(w)

    try:
        # Cast weight function to Any to satisfy type checker; networkx accepts callables
        _distances, _paths = nx.single_source_dijkstra(g, source=ont_id, weight=weight_fn)  # type: ignore[arg-type]
        distances = cast(dict[str, float], _distances)
        paths = cast(dict[str, list[str]], _paths)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        OBS.inc(CACHE_OPTICAL_MISS)
        if _PROM_MISSES is not None:
            try:
                _PROM_MISSES.inc()
            except Exception:
                pass
        return None

    # Collect candidate OLTs that were reached
    candidates: list[tuple[float, float, int, str, str, Sequence[str]]] = []
    for node, dist in distances.items():
        if not _is_olt(g, node):
            continue
        path = paths.get(node)
        if not path:
            continue
        length_km = _path_total_length_km(g, path)
        hop_count = len(path) - 1
        signature = ",".join(path)
        candidates.append(
            (float(dist), float(length_km), hop_count, str(node), signature, list(path))
        )
    if not candidates:
        OBS.inc(CACHE_OPTICAL_MISS)
        if _PROM_MISSES is not None:
            try:
                _PROM_MISSES.inc()
            except Exception:
                pass
        return None
    # Deterministic ordering: attenuation, physical length, hops, olt id, path signature
    candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]))
    best = candidates[0]
    best_path = best[5]
    OBS.inc(CACHE_OPTICAL_HIT)
    if _PROM_HITS is not None:
        try:
            _PROM_HITS.inc()
        except Exception:
            pass
    return OpticalPathResult(
        olt_id=best[3], total_attenuation_db=float(best[0]), segments=_segments(g, best_path)
    )


__all__ = [
    "OpticalPathResult",
    "PathSegment",
    "resolve_optical_path",
]
