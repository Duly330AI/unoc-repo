"""Traffic V2 engine: generation and aggregation.

This engine is a pure consumer of centralized status. All traversal and
generation decisions depend solely on evaluate_device_status from
status_service. We build adjacency from links whose logical status is UP and
restrict traversal to devices whose effective status is UP. If a leaf is not
UP (including DEGRADED or DOWN), it doesn't generate traffic.
"""

from __future__ import annotations

import logging
import time as _time

from sqlmodel import select

import backend.events as events
from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, PortProfile, Status, Tariff
from backend.services import forwarding_service as forwarding_service
from backend.services.status_service import evaluate_device_status, is_link_passable
from backend.services.traffic.v2_caches import ensure_profiles_cache, ensure_topology_caches
from backend.services.traffic.v2_graph import build_adjacency
from backend.services.traffic.v2_path import has_upstream_ok
from backend.services.traffic.v2_segments import compute_segments_map
from backend.services.traffic.v2_tick import generate_flows_for_leaves

from .rand import deterministic_rand01 as _deterministic_rand01  # compat re-export for tests
from .v2_aggregation import compute_device_changes, compute_link_changes
from .v2_congestion import handle_device_congestion, handle_link_congestion
from .v2_dirty import aggregate_dirty, prepare_dirty  # re-export for clients/tests
from .v2_phases import emit_zero_metrics, schedule_status_recompute_if_needed
from .v2_snapshot import build_snapshot_maps

# Re-export for tests that monkeypatch backend.services.traffic.v2_engine.deterministic_rand01
# This preserves the historical module-level symbol that some tests rely on.
deterministic_rand01 = _deterministic_rand01
prepare_dirty = prepare_dirty  # type: ignore[assignment]
aggregate_dirty = aggregate_dirty  # type: ignore[assignment]

LEAF_TYPES = {DeviceType.ONT, DeviceType.BUSINESS_ONT, DeviceType.AON_CPE}


# Global latest snapshot produced by any TrafficEngine.run_tick in this process
LATEST_V2_SNAPSHOT: dict | None = None
# Last non-empty snapshot (devices or links present). Useful to avoid races with
# background runner ticks that might temporarily produce empty activity.
LAST_NONEMPTY_V2_SNAPSHOT: dict | None = None


class TrafficEngine:
    def __init__(self) -> None:
        self._log = logging.getLogger("traffic.TrafficEngineV2")
        self.tick_seq = 0
        self.random_seed = 0xAA55AA55
        self.device_detect_threshold = 1.0
        self.device_clear_threshold = 0.95
        self.link_detect_threshold = 1.0
        self.link_clear_threshold = 0.95
        self._debug_last_generated = {}
        self._debug_last_aggregates = {}
        self._debug_last_link_aggregates = {}
        self._prev_device_congested = set()
        self._prev_link_congested = set()
        self._last_devices = {}
        self._last_links = {}
        self._last_tick = 0
        self._last_ports = {}
        # Track devices that had non-zero metrics in prior tick to detect DOWN transitions
        self._prev_active_devices = set()
        # Track links that had non-zero metrics in prior tick for zeroing when inactive
        self._prev_active_links = set()
        # Per-segment congestion tracking (segment id = f"{pon_if_id}::{odf_id}")
        self._prev_segment_congested: set[str] = set()
        self.segment_detect_threshold = 0.95
        self.segment_clear_threshold = 0.85
        self._last_segments: dict = {}

        # Topology-versioned caches to accelerate 'segments' phase (OLT/ODF aggregation)
        self._cached_topo_version: int | None = None
        # Interfaces and device/iface mappings
        self._iface_by_id: dict[str, Interface] = {}
        self._dev_by_iface: dict[str, str] = {}
        # Neighbor devices per interface id (iface_id -> set(device_id))
        self._neigh_by_if: dict[str, set[str]] = {}
        # OLT -> list of PON interfaces
        self._olt_pon_ifaces_by_olt: dict[str, list[Interface]] = {}
        # Device type by id snapshot from last cache rebuild
        self._dev_type_by_id: dict[str, DeviceType] = {}
        # Device hardware model id by device id (for PortProfile lookup)
        self._dev_hw_model_by_id: dict[str, str | None] = {}
        # Cached optical path results for ONTs keyed by ont_id for current topology version
        self._optical_path_cache: dict[str, object] = {}
        # Cached PortProfiles grouped by hardware_model_id (lazy-built)
        self._profiles_by_hw_model: dict[str, list[PortProfile]] = {}
        self._profiles_cache_ready: bool = False
        # Path cache for generate phase (leaf_id -> (path_nodes, path_links))
        self._path_cache: dict[str, tuple[list[str], list[str]]] = {}
        self._path_cache_topo_v: int | None = None

        # PERF-001: Adjacency cache (device_neighbors, link_by_pair, iface_to_device)
        self._adjacency_cache: (
            tuple[dict[str, set[str]], dict[frozenset[str], str], dict[str, str]] | None
        ) = None
        self._adjacency_cache_valid: bool = False
        self._adjacency_topo_version: int | None = None
        self._adjacency_cache_hits: int = 0
        self._adjacency_cache_misses: int = 0

    def _ensure_topology_caches(self, dev_rows: list[Device]) -> None:  # thin wrapper
        ensure_topology_caches(self, dev_rows)

    def _ensure_profiles_cache(self) -> None:  # thin wrapper
        ensure_profiles_cache(self)

    # --- Path cache helpers for generate phase ---
    def _get_cached_path(self, leaf_id: str) -> tuple[list[str], list[str]] | None:
        try:
            return self._path_cache.get(leaf_id)
        except Exception:
            return None

    def _store_cached_path(self, leaf_id: str, nodes: list[str], links: list[str]) -> None:
        try:
            self._path_cache[leaf_id] = (list(nodes), list(links))
        except Exception:
            pass

    def run_tick(self) -> None:
        # Preserve 0-based ticks to avoid interfering with legacy MetricsService tests
        tick = self.tick_seq
        self.tick_seq += 1
        _t0 = _time.perf_counter()
        _phase_t = _t0

        # Ensure any test monkeypatch of deterministic_rand01 is observed on this tick
        try:
            self.rand01 = deterministic_rand01  # type: ignore[attr-defined]
        except Exception:
            # Fallback to existing attribute if present
            self.rand01 = getattr(self, "rand01", None)

        init_db()
        # Background status recompute scheduling (kept semantically identical)
        schedule_status_recompute_if_needed()
        # Phase timing: status recompute (observes scheduling overhead only now)
        try:
            from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

            _PH.labels(phase="status_recompute").observe(_time.perf_counter() - _phase_t)
        except Exception:
            pass
        _phase_t = _time.perf_counter()
        with get_session() as s:
            # Fine-grained: data_setup (DB reads, adjacency, status eval, tariffs)
            _t_data_setup = _time.perf_counter()
            dev_rows = s.exec(select(Device)).all()
            # Leaf devices with a tariff. Provisioning gate is enforced by evaluate_device_status.
            leaves = [d for d in dev_rows if (d.type in LEAF_TYPES and d.tariff_id is not None)]
            # Detect presence of at least one backbone anchor; only enforce upstream L3 gating
            # when a true anchor exists. This preserves existing test topologies that omit
            # a backbone while still enforcing strict semantics in realistic deployments.
            backbone_present = any(d.type == DeviceType.BACKBONE_GATEWAY for d in dev_rows)

            # Prepare outputs for aggregation downstream
            per_device_totals: dict[str, float] = {}
            per_device_down_totals: dict[str, float] = {}
            per_link_totals: dict[str, float] = {}
            per_link_down_totals: dict[str, float] = {}
            leaves_count = 0

            # Helper maps
            dev_type_by_id = {d.id: d.type for d in dev_rows}
            # Keep available for segments phase later
            # (local variable used later below)

            # PERF-003: Interface/Link data preloaded in ensure_topology_caches()
            # No additional eager loading needed here - caches already provide O(1) lookups via:
            # - _iface_by_id: Interface lookups
            # - _dev_by_iface: Device ID by interface
            # - _neigh_by_if: Neighbors by interface
            # The main N+1 query source (5049 session.get() calls from profiling) comes from
            # status evaluations (evaluate_device_status + has_upstream_l3_or_anchor),
            # which will be addressed in PERF-004 and PERF-005.

            # Preload interfaces and links for adjacency building
            ifaces = s.exec(select(Interface)).all()
            links = s.exec(select(Link)).all()

            # PERF-002: Preload device admin override status for inline link evaluation
            device_override_map: dict[str, Status | None] = {
                d.id: getattr(d, "admin_override_status", None) for d in dev_rows
            }

            # PERF-001: Check adjacency cache before rebuilding
            from backend.services.pathfinding import PATHFINDING_STORE

            try:
                from backend.api.endpoints.metrics import (
                    ADJACENCY_CACHE_HITRATE,
                    ADJACENCY_CACHE_HITS,
                    ADJACENCY_CACHE_MISSES,
                )

                _metrics_available = True
            except Exception:
                _metrics_available = False

            current_topo_v = PATHFINDING_STORE.version()
            if (
                self._adjacency_cache_valid
                and self._adjacency_topo_version == current_topo_v
                and self._adjacency_cache is not None
            ):
                # Cache hit! Use cached adjacency
                device_neighbors, link_by_pair, iface_to_device = self._adjacency_cache
                self._adjacency_cache_hits += 1
                if _metrics_available:
                    ADJACENCY_CACHE_HITS.inc()
                    # Update hit rate gauge
                    total = self._adjacency_cache_hits + self._adjacency_cache_misses
                    if total > 0:
                        ADJACENCY_CACHE_HITRATE.set(self._adjacency_cache_hits / total)
            else:
                # Cache miss: rebuild adjacency
                device_neighbors, link_by_pair, iface_to_device = build_adjacency(
                    ifaces, links, is_link_passable, device_override_map
                )
                # Store in cache
                self._adjacency_cache = (device_neighbors, link_by_pair, iface_to_device)
                self._adjacency_cache_valid = True
                self._adjacency_topo_version = current_topo_v
                self._adjacency_cache_misses += 1
                if _metrics_available:
                    ADJACENCY_CACHE_MISSES.inc()
                    # Update hit rate gauge
                    total = self._adjacency_cache_hits + self._adjacency_cache_misses
                    if total > 0:
                        ADJACENCY_CACHE_HITRATE.set(self._adjacency_cache_hits / total)

            # Evaluate effective status once per tick
            status_by_id: dict[str, Status] = {d.id: evaluate_device_status(d) for d in dev_rows}
            # Devices explicitly forced DOWN administratively are excluded from traversal
            allowed_device_ids: set[str] = set(
                d.id for d in dev_rows if getattr(d, "admin_override_status", None) != Status.DOWN
            )

            # Preload tariffs for demand generation
            tariffs = s.exec(select(Tariff)).all()

            # Anchor device types for target pathfinding
            # Strict mode: only ALWAYS_ONLINE anchors are considered valid
            # aggregation targets. Core routers are deliberately excluded so
            # that a backbone/core break halts generation beyond the access
            # segment.
            ANCHOR_TYPES = {
                DeviceType.BACKBONE_GATEWAY,
                DeviceType.POP,
            }

            # Observe data_setup
            try:
                from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

                _PH.labels(phase="data_setup").observe(_time.perf_counter() - _t_data_setup)
            except Exception:
                pass

            # Phase 1.5: upstream L3 gating before generation (enforced only if backbone present)
            _t_leaf_filter = _time.perf_counter()
            gated_leaves = [d for d in leaves if has_upstream_ok(s, d, backbone_present)]
            # Observe leaf_filtering
            try:
                from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

                _PH.labels(phase="leaf_filtering").observe(_time.perf_counter() - _t_leaf_filter)
            except Exception:
                pass

            # Invalidate path cache on topology version change
            from backend.services.pathfinding import PATHFINDING_STORE

            topo_v = PATHFINDING_STORE.version()
            if self._path_cache_topo_v != topo_v:
                try:
                    self._path_cache.clear()
                except Exception:
                    self._path_cache = {}
                self._path_cache_topo_v = topo_v

            # Sub-phase observer to record fine-grained timings without import cycles
            def _observe_subphase(label: str, seconds: float) -> None:
                try:
                    from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH_SUB

                    _PH_SUB.labels(phase=label).observe(seconds)
                except Exception:
                    # Metrics are optional in some test runs
                    pass

            _t_generate = _time.perf_counter()
            (
                per_device_totals,
                per_device_down_totals,
                per_link_totals,
                per_link_down_totals,
                leaves_count,
                debug_generated,
            ) = generate_flows_for_leaves(
                self,
                s,
                gated_leaves,
                tariffs,
                status_by_id,
                allowed_device_ids,
                device_neighbors,
                link_by_pair,
                dev_type_by_id,
                ANCHOR_TYPES,
                tick,
                rand01=getattr(self, "rand01", deterministic_rand01),
                observe_phase=_observe_subphase,
            )
            # Observe generate duration around the generate call only
            try:
                from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

                _PH.labels(phase="generate").observe(_time.perf_counter() - _t_generate)
            except Exception:
                pass
            # Update debug map identically to prior behavior
            self._debug_last_generated.update(debug_generated)

            # Ensure topology caches are up-to-date for later 'segments' phase
            _t_post_generate = _time.perf_counter()
            try:
                self._ensure_topology_caches(list(dev_rows))
            except Exception:
                pass
            # Observe post_generate (after generate before aggregation)
            try:
                from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

                _PH.labels(phase="post_generate").observe(_time.perf_counter() - _t_post_generate)
            except Exception:
                pass

        _phase_t = _time.perf_counter()

        with get_session() as s2:
            dev_rows = s2.exec(select(Device)).all()
            device_changes = compute_device_changes(
                s2, dev_rows, per_device_totals, per_device_down_totals
            )

        # Phase timing: aggregate_devices
        try:
            from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

            _PH.labels(phase="aggregate_devices").observe(_time.perf_counter() - _phase_t)
        except Exception:
            pass
        _phase_t = _time.perf_counter()

        if device_changes:
            events.publish(
                events.Event(
                    type="deviceMetricsUpdated",
                    payload={"devices": device_changes, "tick": tick},
                )
            )

        with get_session() as s3:
            link_changes, ports_map = compute_link_changes(
                s3, per_link_totals, per_link_down_totals
            )

        # Phase timing: aggregate_links_ports
        try:
            from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

            _PH.labels(phase="aggregate_links_ports").observe(_time.perf_counter() - _phase_t)
        except Exception:
            pass
        _phase_t = _time.perf_counter()

        # --- Phase 2: Per PON-segment aggregation (OLT PON-port <-> ODF) ---
        # Map ONT demand to segments and compute capacity, shaping and congestion.
        try:
            segments_map = compute_segments_map(
                self, per_device_totals, per_device_down_totals, tick
            )
        except Exception:
            segments_map = {}

        # Phase timing: segments (OLT/ODF aggregation & shaping)
        try:
            from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

            _PH.labels(phase="segments").observe(_time.perf_counter() - _phase_t)
        except Exception:
            pass
        _phase_t = _time.perf_counter()

        if link_changes:
            events.publish(
                events.Event(
                    type="linkMetricsUpdated",
                    payload={"links": link_changes, "tick": tick},
                )
            )

        # Emit zero metrics for inactive entities and update previous-active sets
        zero_events, link_zero_events = emit_zero_metrics(self, device_changes, link_changes, tick)

        self._debug_last_aggregates = dict(per_device_totals)
        self._debug_last_link_aggregates = dict(per_link_totals)

        # Reset phase timer so 'congestion' measures only congestion handlers
        _phase_t = _time.perf_counter()

        current_device_congested = handle_device_congestion(
            self._prev_device_congested,
            device_changes,
            self.device_detect_threshold,
            self.device_clear_threshold,
            tick,
        )
        self._prev_device_congested = current_device_congested

        current_link_congested = handle_link_congestion(
            self._prev_link_congested,
            link_changes,
            self.link_detect_threshold,
            self.link_clear_threshold,
            tick,
        )
        self._prev_link_congested = current_link_congested

        # Phase timing: congestion
        try:
            from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

            _PH.labels(phase="congestion").observe(_time.perf_counter() - _phase_t)
        except Exception:
            pass
        _phase_t = _time.perf_counter()

        dev_map, link_map = build_snapshot_maps(device_changes, link_changes)
        # Merge zeroed entries into the snapshot so get_v2_snapshot reflects cleared metrics
        if zero_events:
            for item in zero_events:
                did = item.get("id")
                if did:
                    dev_map[did] = {
                        "bps": 0.0,
                        "utilization": 0.0,
                        "version": 0,
                        "upstream_bps": 0.0,
                        "downstream_bps": 0.0,
                    }
        if link_zero_events:
            for item in link_zero_events:
                lid = item.get("id")
                if lid:
                    link_map[lid] = {"bps": 0.0, "utilization": 0.0, "version": 0}
        self._last_devices = dev_map
        self._last_links = link_map
        self._last_ports = ports_map
        self._last_segments = segments_map
        self._last_tick = tick
        # Phase timing: snapshot_build
        try:
            from backend.api.endpoints.metrics import TRAFFIC_TICK_PHASE_DURATION as _PH

            _PH.labels(phase="snapshot_build").observe(_time.perf_counter() - _phase_t)
        except Exception:
            pass
        _phase_t = _time.perf_counter()
        # Publish process-wide latest snapshot for the facade/endpoint
        global LATEST_V2_SNAPSHOT, LAST_NONEMPTY_V2_SNAPSHOT
        LATEST_V2_SNAPSHOT = {
            "lastTick": int(self._last_tick),
            "devices": dict(self._last_devices),
            "links": dict(self._last_links),
            "ports": dict(self._last_ports),
            "segments": dict(self._last_segments),
        }
        # Update last non-empty snapshot as a stable fallback
        try:
            if LATEST_V2_SNAPSHOT.get("devices") or LATEST_V2_SNAPSHOT.get("links"):
                LAST_NONEMPTY_V2_SNAPSHOT = dict(LATEST_V2_SNAPSHOT)
        except Exception:
            pass

        # Observe traffic tick duration at the very end of the tick
        try:
            from backend.api.endpoints.metrics import TRAFFIC_TICK_DURATION as _TICK_HIST

            _TICK_HIST.observe(_time.perf_counter() - _t0)
        except Exception:
            pass
        # Debug summary for dev runs
        try:
            # Promote to info so dev runs can see activity without enabling debug
            self._log.info(
                "tick=%d leaves=%d dev_updates=%d link_updates=%d",
                tick,
                leaves_count,
                len(device_changes),
                len(link_changes),
            )
            if leaves_count == 0:
                self._log.info("no eligible leaves (ONT/Business ONT/AON CPE with tariff and UP)")
        except Exception:
            pass

    def get_snapshot(self) -> dict:
        return {
            "lastTick": int(self._last_tick),
            "devices": dict(self._last_devices),
            "links": dict(self._last_links),
            "ports": dict(self._last_ports),
            "segments": dict(getattr(self, "_last_segments", {})),
        }
