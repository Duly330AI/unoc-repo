## 13. Future Extensions / Non‑Goals (Initial Scope)

| Category    | Deferred Items                                                    |
| ----------- | ----------------------------------------------------------------- |
| Networking  | Dual-stack IPv6, Multi-backbone domains, advanced path caching    |
| UI          | Lasso selection, Bulk override UI, Additional viewer dashboards   |
| Persistence | Durable migrations, de-provision IP reclamation                   |
| Simulation  | Advanced traffic patterns, congestion modeling                    |
| Diagnostics | Path conflict analyzer, override audit log                        |
| Security    | AuthN/AuthZ, multi-tenancy, RBAC                                  |
| Performance | Large-scale (10k devices) optimization, event batching refinement |

## 14. Reference Catalog (Hardware & Optical Defaults)

Authoritative set of immutable (versioned) vendor / model characteristics used to seed runtime defaults (e.g. tx_power_dbm, sensitivity_min_dbm, insertion_loss_db).

### 14.1 Goals

- Preserve authenticity of original manufacturer values.
- Provide deterministic, validated source for provisioning defaults.
- Allow controlled overrides without mutating base artifacts.
- Enable reproducibility (hash & schema version).

### 14.2 File & Directory Layout

```

data/
catalog/
hardware/
olt/_.json # OLT models
ont/_.json # ONT & Business ONT
passive/\*.json # ODF / NVT / Splitter / HOP
manifest.json # schema_version, files[], sha256 map
overrides/
(mirrors structure – optional)

```

### 14.3 JSON Schema (Conceptual)

Common fields:

```

{
"catalog_id": "OLT_HUAWEI_MA5800_X2_V1",
"device_type": "OLT",
"vendor": "Huawei",
"model": "MA5800-X2",
"version": "1.0",
"attributes": {
"tx_power_dbm": 5.0,
"insertion_loss_db": 3.5, # only if passive / splitter
"sensitivity_min_dbm": -30.0 # ONT types
},
"meta": {"source": "datasheet 2024-05", "notes": "baseline"}
}

```

### 14.4 Load & Validation Pipeline

1. Read manifest.json (mandatory).
2. Validate schema_version compatibility.
3. Load listed files; compute sha256; compare with manifest entry (integrity check).
4. Parse via Pydantic models (CatalogOLT, CatalogONT, CatalogPassive...).
5. Build indexes: by catalog_id, by device_type, by vendor.
6. Load overrides (if any) and merge (whitelisted mutable fields only: tx_power_dbm, sensitivity_min_dbm, insertion_loss_db).
7. Generate consolidated hash (sorted catalog_id + sha256(file)).
8. Freeze in-memory structures (prevent runtime mutation).

### 14.5 Override Merge Rules

| Field                | Merge Strategy | Notes                          |
| -------------------- | -------------- | ------------------------------ |
| tx_power_dbm         | replace        | OLT only                       |
| sensitivity_min_dbm  | replace        | ONT only                       |
| insertion_loss_db    | replace        | Passive & splitter             |
| vendor/model/version | immutable      | Change requires new catalog_id |
| device_type          | immutable      | Guard mismatch                 |

Reject override if unknown catalog_id or forbidden field altered.

### 14.6 Service Interface (Backend)

`CatalogService` exported functions:

```

get_model(catalog_id) -> CatalogEntry
default_tx_power(olt_catalog_id) -> float
default_sensitivity(ont_catalog_id) -> float
default_insertion_loss(passive_catalog_id) -> float
list_fiber_types() -> list[FiberType]
compute_catalog_hash() -> str

```

### 14.7 API Endpoints (MVP)

| Endpoint                               | Purpose                              | Notes               |
| -------------------------------------- | ------------------------------------ | ------------------- |
| GET /api/catalog/hardware?type=OLT     | List models filtered                 | Pagination optional |
| GET /api/catalog/hardware/{catalog_id} | Single model detail                  | 404 if missing      |
| GET /api/optical/fiber-types           | Fiber types list (from section 6.10) | Cacheable           |

### 14.8 Provisioning Integration

- On provision, if user did not supply optical overrides, use catalog defaults.
- Device stores effective optical fields; also store `catalog_id` reference.
- If later UI edit deviates from catalog default, mark `modified_from_catalog = true` (boolean) for clarity.

#### 14.8.1 Runtime updates vs. device overrides (authoritative behavior)

- Effective value resolution order is: device-level override → catalog model default → fallback.
- Therefore, changing a catalog model will affect devices that reference that model only when the corresponding device field is null/unspecified (i.e., not explicitly overridden).
- Devices with explicit per-device values continue to use those values regardless of catalog changes.
- Recommendation: if you want devices to inherit future catalog adjustments, avoid persisting explicit device values for those fields; rely on the model linkage (`hardware_model_id`) instead.

### 14.9 Determinism Guarantees

- Catalog hash logged at startup: `catalog_hash=<sha256> schema_version=<n>`.
- Type generation for frontend sorts entries by catalog_id asc.

### 14.10 Testing

- test_catalog_load_ok (all entries valid).
- test_catalog_override_merge (override takes effect).
- test_catalog_hash_stable (hash only changes when file content changes).
- test_provision_uses_catalog_defaults (provisioned device fields match expected).

### 14.11 Observability

- Log counts per type: `catalog_counts{"OLT":X,"ONT":Y,...}`.
- Metric gauge: catalog_entries_total{type}.
- Warning log if overrides present: enumerated diff summary.

### 14.12 Future Enhancements

- Remote catalog fetch (signed bundle) for vendor updates.
- Version negotiation (multiple catalogs loaded side-by-side).
- Catalog diff endpoint.

---

Document Version: r2 (light/signal feature elaboration & UI integration).

Note: The authoritative fiber type catalog is exposed by the backend endpoint `/api/optical/fiber-types` and mirrors the constants documented in 04_signal_budget_and_overrides.md. Prefer querying the endpoint in UI to avoid drift.

## 15. Real-time Simulation & Metrics

Deterministic periodic traffic simulation producing granular delta events (no full refresh) consumed by the frontend for live visualization.

### 15.1 Goals & Non-Goals (MVP)

Goals: deterministic leaf traffic generation (ONT / Business ONT / AON CPE), hierarchical aggregation upstream, utilization computation, minimal diff emission (deviceMetricsUpdated), snapshot recovery after WS reconnect.
Non‑Goals: historical persistence, per-flow QoS, latency modeling, advanced congestion/queue simulation, smoothing (explicitly disabled for MVP).

### 15.2 Metric Model

Per device (provisioned & effective_status=online unless stated):

- upstream_traffic_gbps (float)
- downstream_traffic_gbps (float, MVP = symmetric to upstream as per decision)
- utilization_percent (may exceed 100%)
- capacity_gbps (static from catalog/type/tariff – not in every delta, only snapshot or when changed later)
- tick_seq (monotonic global tick number)
- version (entity-local increment when any metric value changes)

Passive devices & POP: no utilization (omit or null). Backbone Gateway always aggregates full sum.

### 15.3 Leaf Traffic Generation

Applies only to ONT, Business ONT, AON CPE devices that are: provisioned AND effective_status=online.
Inputs:

- Tariff: max_up_gbps (and optional configured_percent for percent mode)
- Mode: variable | percent

Variable Mode: deterministic pseudo-random factor f ∈ [0,1] per (tick_seq, device_id) via lightweight PRNG (xor-shift or PCG). Leaf upstream = max_up_gbps * (bias + (1-bias)*f) with bias default 0.15 to avoid zero plateaus.
Percent Mode: upstream = max_up_gbps \* configured_percent.

MVP Decisions:

- Smoothing (EMA) disabled (could be TRAFFIC_SMOOTHING flag later).
- downstream_traffic_gbps = upstream_traffic_gbps (symmetrical).

### 15.4 Aggregation Upstream

Construct an immutable topology snapshot at tick start (device adjacency + parent relationships). Perform post-order aggregation adding children upstream_traffic_gbps to parents (POP sums its active children; passive inline devices not counted separately). Core / Backbone accumulate transit totals. Offline leaves contribute 0.

### 15.5 Utilization

utilization_percent = (upstream_traffic_gbps / capacity_gbps) \* 100.
Capacity policy:

- Core Router / Router: configured constant.
- OLT: e.g. 40 Gbps (catalog or config).
- AON Switch: e.g. 10 Gbps.
- ONT / CPE: tariff max_up_gbps.
  Values over 100% ARE allowed (no clamping) to visually highlight over-subscription.
  Division by zero: utilization_percent = null (and excluded from diffs) + WARN log.

### 15.6 Scheduler & Tick Engine

Background thread (TrafficSimulationEngine) launched at startup if TRAFFIC_ENABLED.
Config Keys:

- TRAFFIC_ENABLED (bool, default true in dev)
- TRAFFIC_TICK_INTERVAL_SEC (float, default 2.0)
- STRICT_ONT_ONLINE_ONLY (bool – ignore offline leaves, default true)
- TRAFFIC_RANDOM_SEED (int – base seed; combine with device_id & tick_seq)

Loop:

```

while running:
started = now()
run_tick()
sleep(max(0, interval - (now()-started)))

```

Graceful shutdown integrates existing system shutdown endpoint.

Persistence and determinism:

- In MVP, `tick_seq` is process-local and not persisted across restarts; it resets to 0 when the process restarts.
- Leaf generation remains deterministic per tick using `TRAFFIC_RANDOM_SEED`, `device_id`, and `tick_seq` (see §15.11). Given identical inputs, patterns repeat exactly.

### 15.7 Data Structures (Runtime, In-Memory)

```

metrics_by_device: dict[device_id] -> Metrics(up, down, util, version)
last_tick_seq: int
last_emitted_snapshot: dict[device_id] -> (up, down, util, version)

```

Thread-safety: snapshot read outside lock; write updates under short lock (RLock) or rely on GIL for primitive assignments.
No DB persistence in MVP (future: ring buffer of N ticks optional).

### 15.8 Diff & Event Emission

For each tick compute new metrics, compare to last_emitted_snapshot:
Change criteria per device:

- abs(new_up - old_up) >= EPSILON (default 0.01 Gbps)
- OR utilization bucket boundary crossed (buckets: <50, <70, <90, <100, >=100)
- OR version not present (first emission).

If changes collected → emit single `deviceMetricsUpdated` event:

```

{
event: "deviceMetricsUpdated",
tick: tick_seq,
items: [{id, up_gbps, down_gbps, utilization_percent, version}]
}

```

Version increments only when an item is included. Ordering within overall delta flush: optical/signal events → status events → metrics (ensures status stable before metrics consumption).
Backpressure strategy: if WS send buffer occupied, replace queued metrics event with latest (drop intermediate ticks) – eventual consistency sufficient for rapidly updating metrics.

### 15.9 Reconnect & Snapshot

Client tracks last_tick_seq. On WebSocket reconnect the frontend calls `GET /api/metrics/snapshot` (MVP always full snapshot). Response:

```

{
tick: current_tick_seq,
devices: { "dev-id": {up_gbps, down_gbps, utilization_percent, version, capacity_gbps} }
}

```

Later enhancement: `?since=` diff mode. Snapshot sets new baseline (replaces metrics map) without generating local synthetic events.

#### 15.9.1 Topology/store version gap handling (client guidance)

- The WebSocket envelope includes the current `topo_version` (see §11). Clients should detect gaps (missed ticks or topology updates) by comparing versions.
- On detecting a gap or after reconnect, fetch fresh snapshots (metrics via `GET /api/metrics/snapshot`; topology via the standard REST loaders) and replace local store baselines before resuming delta handling.

### 15.10 Link Metrics (Phase 2)

Deferred to Phase 2 (TASK-057). Approach: For each leaf path accumulate per traversed link. Optimization required to avoid O(L \* leaves): store for each device its upstream link pointer chain or precomputed path segments. Not part of MVP emission.

Snapshot Extension (in-progress via TASK-077A/TASK-554):

- Extend GET /api/metrics/snapshot to include `links` dictionary keyed by link id with utilization_percent, up/down gbps and version fields, derived from per-link counters in Traffic Engine v2. Frontend applies snapshot to a dedicated linkMetricsStore.

### 15.11 Deterministic PRNG

Use xor-shift / PCG seeded with hash(base_seed, device_id, tick_seq). Ensures identical input topology => identical traffic pattern (useful for tests). Hash can be a simple 64-bit FNV1a over concatenated values.

### 15.12 Observability

Prometheus metrics:

- unoc_sim_tick_duration_seconds (histogram)
- unoc_sim_changed_devices (histogram)
- unoc_sim_active_leaves (gauge)
- unoc_sim_skipped_ticks_total (counter)
  Structured Logs:
- tick.start {tick, leaves}
- tick.diff {tick, changed, duration_ms}
  Health Endpoint: `GET /api/sim/status` → { enabled, interval_sec, last_tick_ts, tick_seq }.

### 15.13 Error Handling & Resilience

- Exceptions inside run_tick captured & logged; counter increment, engine continues.
- Negative generated traffic clamped to 0 (warn once per device per run).
- Capacity 0 or missing: utilization null + warn.
- If no leaves provisioned: skip aggregation (fast path) still increments tick_seq for monotonicity.

### 15.14 Frontend Integration

Pinia adds `metricsStore`:

```

state: { byId: Record<string, {up: number, down: number, util: number, version: number}>, lastTick: 0 }
actions: applyMetricsDelta(eventItems), applySnapshot(snapshot)

```

WebSocket handler: on deviceMetricsUpdated iterate items, compare version, in-place patch to preserve node identity (minimizes D3 churn).
Visualization:

- Node ring / bar uses utilization bucket to color (green <50, yellow <70, orange <90, red <100, purple >=100 for overload).
- D3 transitions (ease-out, 300–400ms) on radius/thickness.
  Detail Panel: shows current metrics, tick_seq, optional over-100% indicator.
  Reconnect flow: after socket open → fetch snapshot → set baseline → resume delta handling.

### 15.15 Testing Strategy

Backend Unit:

- PRNG determinism: same tick_seq/seed → identical leaf outputs.
- Aggregation correctness (linear & branching topologies).
- Diff emission thresholds (EPSILON & bucket crossing).
- Utilization overflow >100 preserved.
  Integration:
- Simulate ticks; capture WS events; verify structure & ordering relative to status events.
- Reconnect: apply snapshot then subsequent delta consistent.
  Frontend:
- applyMetricsDelta mutates only changed ids (count assertions).
- Snapshot replace correctness (stale entries removed).
  Property: sum(leaf upstream) ≈ backbone upstream (allow minor FP tolerance).

### 15.16 Future Enhancements

- Adaptive Tick Interval (variance-based scaling).
- Capability negotiation (client declares interest: metrics, links, etc.).
- Compressed payload form (parallel arrays) for large change sets.
- Optional 60-tick rolling history per selected device (small ring buffer) enabling sparkline.
- Link metrics & congestion (Phase 2).
- EMA smoothing toggle (TRAFFIC_SMOOTHING) for less jittery UI charts.

### 15.17 Constants & Flags Summary

```

TRAFFIC_ENABLED
TRAFFIC_TICK_INTERVAL_SEC
TRAFFIC_RANDOM_SEED
STRICT_ONT_ONLINE_ONLY
EPSILON_METRICS_DELTA (default 0.01)
ALLOW_METRICS_OVERLOAD (true – permit >100%)
UTILIZATION_BUCKETS = [50,70,90,100] # thresholds; bucket selected by first >= threshold; values >=100 treated as overload

```

### 15.18 Security & Performance Notes

- No user input in metric generation → minimal injection surface.
- WS event size bounded by changed device count; large spikes mitigated by diff threshold.
- Avoid per-device allocations inside tick (reuse buffers) for high-scale scenarios (>10k leaves) if needed later.

---

Simulation section added (r1). Decisions: symmetric downstream, no smoothing MVP, link metrics deferred, allow >100% utilization.

### 15.19 Debug Traffic Injection (Test & Diagnostics)

Purpose: Facilitate fast, granular testing of aggregation & visualization without constructing full leaf topology. Allows synthetic traffic to be injected at intermediate aggregation points.

Implementation status: This section documents the planned behavior. Backend fields/endpoints for debug injection are not implemented yet; the UI surfaces the feature only when enabled via `/api/config` (see §15.20).

#### 15.19.1 Data Model Extensions

Active device types (Backbone Gateway optional, Core Router, Router (edge), OLT, AON Switch) gain optional fields:
| Field | Type | Nullable | Description |
| ---------------------------- | -------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| debug_traffic_injection_gbps | float | yes | Synthetic traffic value (Gbps) applied at this node each tick when enabled. Must be >= 0 and <= TRAFFIC_INJECTION_MAX_GBPS. |
| debug_traffic_mode | enum {add, override} | yes | How to apply injection: add → added to computed upstream aggregate; override → replaces computed upstream value before utilization. |

Storage: Persisted columns (simplifies API + snapshot). Default NULL (no effect). Changes require metrics diff emission on next tick.

#### 15.19.2 Application Order (Tick)

Base algorithm sequence modification inside aggregation phase for each eligible device d:

```

base = aggregated_children_upstream(d) # or leaf generated traffic if leaf
inj = d.debug_traffic_injection_gbps (or 0 if null)
if d.debug_traffic_mode == 'override': effective_up = inj
elif d.debug_traffic_mode == 'add': effective_up = base + inj
else: effective_up = base
upstream_traffic_gbps = effective_up

```

Then downstream_traffic_gbps = upstream_traffic_gbps (MVP symmetry) and utilization computed from effective_up.

Override semantics precedence:
Leaf generation → child aggregation → debug injection → utilization → diff detection.
Admin status overrides still gate (offline device → injection ignored unless future flag ALLOW_INJECTION_ON_OFFLINE set).

#### 15.19.3 Validation Rules

- Negative injection → 400 INVALID_DEBUG_INJECTION
- Injection > TRAFFIC_INJECTION_MAX_GBPS → 400 DEBUG_INJECTION_LIMIT
- Mode provided without value: treat as error (require both or clear both)
- Clearing: PATCH with {debug_traffic_injection_gbps: null, debug_traffic_mode: null}

#### 15.19.4 Configuration Flags

```

TRAFFIC_INJECTION_ENABLED (bool, default true in dev, false in prod)
TRAFFIC_INJECTION_MAX_GBPS (float, default 10000.0)
TRAFFIC_INJECTION_REQUIRE_DEBUG_FEATURE (bool, ties to UNOC_DEV_FEATURES)

```

If disabled: API returns 403 FEATURE_DISABLED on mutation attempts; existing stored values ignored at tick.

#### 15.19.5 API Surface

PATCH /api/devices/{id}/debug-traffic
Request JSON:

```

{ "debug_traffic_injection_gbps": 5.0, "debug_traffic_mode": "override", "immediate": false }

```

Immediate flag (optional): if true and value accepted → triggers on-demand micro-tick for that device only (shortcut recompute) producing a `deviceMetricsUpdated` event; else appears next scheduled tick.

GET /api/devices/{id} includes the two fields when non-null (or always if we prefer explicitness; implementation choice – recommended always include for schema stability).

#### 15.19.6 Events & Diff Behavior

- Standard diff detection picks up changed upstream_traffic_gbps due to injection.
- Changing injection fields should force emission even if resulting numeric equals prior value (e.g., base 5, override 5) → set a device dirty flag to bypass EPSILON suppression once.
- No new event type; rely on deviceMetricsUpdated.

#### 15.19.7 Security & Safety

- Only enabled in dev / test by config (hard disable in production builds unless explicitly toggled).
- Rate limiting (optional future) to prevent rapid high-value oscillation causing UI churn.
- Large override may create extreme utilization → allowed (purpose: stress path) but logged if utilization > 1000%.

#### 15.19.8 Testing Scenarios

1. add mode: base=2.0, inject=3.0 → effective=5.0.
2. override mode: base=2.0, inject=3.0 → effective=3.0.
3. Clear injection: subsequent tick reverts to base; diff emitted.
4. Dirty emission: override=5.0 when base already 5.0 still triggers diff once.
5. Disabled feature flag: attempt returns 403.
6. Offline device (effective_status=offline): injection ignored (upstream=0) and warning optionally logged.

#### 15.19.9 Frontend Debug UI

Device Details Panel → collapsible "Debug" section (shown when TRAFFIC_INJECTION_ENABLED flag returned via /api/config or dev mode active):

- Numeric input (step 0.1) for injection value.
- Mode radio (add | override).
- Apply button (PATCH) + Clear button (sets both null).
- Immediate checkbox (maps to immediate flag).
  Visual cues: badge on node when injection active (e.g., small lightning icon).

#### 15.19.10 Observability

Metrics:

- unoc_debug_injection_active_devices (gauge)
- unoc_debug_injection_updates_total (counter)
  Logs:
- debug_injection.set {device_id, mode, value}
- debug_injection.clear {device_id}

#### 15.19.11 Future Enhancements

- Time-bound injections (expires_after_ticks).
- Directional injection (separate upstream vs downstream future).
- Pattern generators (ramp, sine) for performance profiling.
- Bulk injection endpoint for scenario scripting.

#### 15.19.12 Error Codes (Additions)

| Code                    | Meaning                                    |
| ----------------------- | ------------------------------------------ |
| INVALID_DEBUG_INJECTION | Negative or malformed injection parameters |
| DEBUG_INJECTION_LIMIT   | Injection value exceeds configured maximum |
| FEATURE_DISABLED        | Feature disabled by configuration          |

#### 15.19.13 Immediate Micro-Tick (Implementation Sketch)

Goal: Apply a single-device (plus ancestor chain) metrics refresh immediately after a successful debug traffic injection PATCH with `immediate=true`, without waiting for the next scheduled global tick.

Design Constraints:

- Must preserve global ordering (`tick_seq` monotonic).
- Must not run concurrently with the scheduled tick loop (acquire same lock / guard).
- Scope-limited recomputation: only the target device and its ancestor path to the root (until a device whose aggregate value is unchanged) are recalculated.
- Emits only `deviceMetricsUpdated` events for devices whose metrics actually changed or were explicitly dirtied by the injection flag bypassing epsilon suppression.

Locking & Sequencing:

```

micro_tick(device_id):
acquire tick_lock (non-blocking attempt; if busy → return 409 or queue)
seq = ++tick_seq
affected = []
target = load(device_id)
mark target.force_metrics_emit = true # bypass epsilon once
recompute_chain(target)
snapshot_and_diff(affected)
emit_events(affected, tick_seq=seq, micro=true)
release tick_lock

```

`recompute_chain(d)`:

1. Recompute d's upstream_traffic_gbps (including injection logic).
2. Compute downstream (symmetry) & utilization.
3. If metrics changed (or force emit) add to `affected`.
4. If parent exists, update parent's aggregated_children_upstream; if parent aggregate changes beyond EPSILON or child forced emit, recurse upward; otherwise stop (early termination optimization).

Tick Sequence Handling:

- Micro-tick increments the same `tick_seq` counter used by scheduled ticks (keeps ordering simple for clients).
- Event payloads include `{"micro": true}` flag (new optional boolean field) so the frontend can (optionally) visually distinguish immediate updates (not required for correctness).

Concurrency:

- Scheduled tick loop obtains the same `tick_lock` prior to aggregation. Micro-tick attempts to acquire; if it fails quickly, returns 409 (client may retry with backoff) or waits (configurable). (Potential future code: TICK_IN_PROGRESS error.)

Failure Modes:

- Device not found → 404.
- Feature disabled mid-flight → 403 FEATURE_DISABLED.
- Validation failure already handled in PATCH stage (no micro-tick executed).

Observability:

- Counter: `unoc_micro_ticks_total{reason="debug_injection"}`.
- Histogram: `unoc_micro_tick_duration_seconds`.
- Log: `micro_tick.run {device_id, affected_count, seq}`.

Frontend Handling:

- Treat like any other metrics events (ordering by tick_seq). Optional: show transient pulse on updated nodes when `micro=true`.

Limitations (MVP):

- No batching of multiple immediate injections; sequential calls each run their own micro-tick.
- Does not recompute descendants (not needed because injection affects upstream flow only).

Future Enhancements:

- Batch micro-ticks for multiple devices within short debounce window.
- Allow combining with requested hypothetical scenarios (sandbox mode) before committing.

### 15.20 Frontend Configuration Endpoint (/api/config)

Purpose: Deliver runtime feature flags & constants to the frontend at bootstrap (and optionally on demand) so UI logic (e.g., showing Debug Injection UI) remains decoupled from build-time assumptions.

Endpoint: `GET /api/config`

Response (JSON):

```

{
"version": "2025-09-07T12:34:56Z", # ISO timestamp or commit hash for cache busting
"devMode": true, # UNOC_DEV_FEATURES active
"traffic": {
"enabled": true,
"tick_interval_sec": 1.0,
"epsilon_metrics_delta": 0.01,
"allow_metrics_overload": true,
"utilization_buckets": [50,70,90,100]
},
"injection": {
"enabled": true,
"max_gbps": 10000.0,
"require_debug_feature": true
},
"flags": {
"strict_ont_online_only": true,
"link_metrics_enabled": false # Phase 2 placeholder
},
"build": {
"commit": "<git-sha>",
"build_time": "2025-09-07T12:30:00Z"
}
}

```

Behavior & Semantics:

- Values are read-only snapshots; server holds authoritative config (env vars / internal settings module).
- Include an `ETag` header (hash of payload) so frontend can conditional GET (`If-None-Match`) for cheap refresh.
- Cache-Control: `public, max-age=30` (tunable) since changes are rare; immediate invalidation via version bump.
- Optional WebSocket event `configUpdated` (deferred) enabling push refresh when admin toggles a flag.

Usage (Frontend):

- Fetch at application bootstrap before rendering device detail panels.
- Store in a reactive store (e.g., Pinia) and expose selectors (isDebugInjectionVisible → config.devMode && config.injection.enabled).
- Re-fetch on explicit user action (e.g., Dev Tools panel reload) or when a 403 FEATURE_DISABLED is received for an operation previously believed enabled.

Security:

- Do not expose sensitive values (tokens, internal seeds). Only operational toggles & non-sensitive constants.
- In production, `devMode` typically false; injection.enabled false; the UI hides debug controls gracefully.

Extensibility:

- Additional namespaces (optical, sandbox, limits) can be appended without breaking clients if frontend ignores unknown keys.
- Version field pattern: if semantic config schema changes, embed `schema_version` for client adaptation.

Error Cases:

- 500 on internal failure (rare); client may retry with backoff.
- (Future) 503 if configuration subsystem reloading.

Testing:

- Add contract test asserting keys & types.
- Snapshot test to detect accidental removal of fields consumed by frontend.

---

## 16. Smart SVG Cockpits & Real-time Visualization (ON HOLD)

Status: ON HOLD / To Be Redefined. The core D3/Vue boundary and cockpit unification remain in place for current visuals. Advanced tasks (port matrix, tooltip engine, performance overlay, link utilization animation) are deferred while backend emulation work proceeds.

Authoritative visualization engine design ("Smart SVG Cockpits"). Vue 3 components render device-specific SVG dashboards while D3 is confined to spatial layout & link geometry. A SINGLE central D3 canvas controls all spatial transforms; Vue cockpits never write to transform state (see §9). This section is the implementation plan for Milestone 8.
Incorporates user-approved decisions:
DECISION LOG:

- Signal budget computation: BACKEND ONLY (frontend is presentation-only).
- OLT Port Matrix Layout: Column-based, scroll / tooltip for overflow.
- No <foreignObject>; pure SVG for portability & performance.

### 16.1 Ziele & Scope

Ziele: Reaktive, skalierbare Geräte-Cockpits mit Live-Traffic-, Status- und Signal-Budget-Indikatoren; konsistente Farb-/Legendenlogik; minimale Re-render Kosten bei Delta-Events.
Nicht-Ziele (MVP): Historisierung, Multi-OLT Pfadvergleich UI, Cluster/Lod Rendering (Future), Worker-basierte Delta-Normalisierung.

### 16.2 Datenfluss & Events

Source-of-truth: Pinia Stores (devices, metrics, signal, ports, links). WebSocket liefert nur Deltas (deviceStatusUpdated, deviceSignalUpdated, deviceMetricsUpdated, linkUpdated). Batching & rAF commit verhindern Render-Stürme. Reihenfolge garantiert per §11 & §15.

Event→Store Mapping (authoritativ):

- deviceStatusUpdated → devicesStore.updateStatus(id, status, override?, versions)
- deviceSignalUpdated → signalStore.upsert({ id, received_dbm, margin_db, signal_status, path? })
- deviceMetricsUpdated → metricsStore.upsert({ id, total_utilization_percent, up_mbps?, down_mbps?, ts })
- linkUpdated/linkMetricsUpdated → linksStore.upsertMeta({ id, length_km?, fiber_type? }) + linkMetricsStore.upsert({ id, utilization_percent, ts })
- deviceCreated/deviceDeleted/linkCreated/linkDeleted → topologyStore.applyDelta(payload)

All store upserts are versioned; if payload.version <= currentVersion, drop silently to ensure determinism.

### 16.3 Store Module

topologyStore (positions, basic device/link meta)
metricsStore (device metrics byId, versions)
signalStore (ONT signal payloads incl. margin_db, path meta)
portStore (OLT/Switch port occupancy arrays)
linkMetricsStore (utilization buckets per link; optional until TASK-077A)
uiStore (selection, hover, viewport, config flags, legend toggles)
derivedCache (memoized color bucket & status mapping)

Contracts (TS-style shapes):

```

type DeviceStatus = 'up' | 'down' | 'degraded' | 'unknown'
interface SignalEntry { id: string; received_dbm?: number; margin_db?: number; signal_status?: 'OK'|'WARNING'|'CRITICAL'|'NO_SIGNAL'|'UNKNOWN'; path?: { olt_id?: string; total_attenuation_db?: number; segments?: Array<{type:string; id:string; loss_db?:number}> } }
interface MetricsEntry { id: string; total_utilization_percent?: number; up_mbps?: number; down_mbps?: number; ts: number }
interface LinkMetricsEntry { id: string; utilization_percent?: number; ts: number }

```

### 16.4 Render Pipeline

1. WS Event → enqueue delta
2. Coalescing (map keyed by entity id + event type)
3. requestAnimationFrame tick applies mutations (atomic batch)
4. Vue reactive computeds trigger minimal updates (fine-grained computed getters per device id)
5. D3 retains only link paths + node <g> transform positions (no inner content handoff)

Bootstrap Snapshot (initial load):

- On app start, fetch GET /api/metrics/snapshot once (TASK-077A extends with links dict).
- Apply snapshot to metricsStore, linkMetricsStore, and optionally signalStore if included.
- WS connects after snapshot apply; any deltas buffered during fetch are coalesced then applied.

### 16.5 Cockpit Layout Typen

Gemeinsamer BaseCockpit: Rahmen (stroke color = status), display_id, padding, size tokens.

- Core / Edge Router: Large % utilization (total_utilization_percent), dual traffic bars (up/down), status ring.
- OLT / AON Switch: Port matrix (column layout). Each port: occupancy color. Overflow: scroll region or condensed icon + tooltip list >N.
- ONT / Business ONT / AON CPE: Signal badge (status + received_dbm), traffic inline, tariff chip, utilization subtle ring.
- Passive (ODF, NVT, Splitter, HOP): Minimal label + insertion_loss_db (e.g. "−0.5 dB"), status border, optional attenuation icon.
  Status Frame Colors: online=green (#2ecc71), degraded=yellow (#f1c40f), offline=red (#e74c3c), unprovisioned=gray (#7f8c8d).
  Signal Status Colors: OK=green, WARNING=amber (#f39c12), CRITICAL=red, NO_SIGNAL=gray dashed outline, UNKNOWN=muted (#95a5a6).

Component API (per cockpit, Props minimal & reactive):

- BaseCockpit: { id, status, title?, width=COCKPIT_BASE_WIDTH, height=COCKPIT_BASE_HEIGHT }
- RouterCockpit: Base + { utilizationPct, upMbps?, downMbps? }
- OLTCockpit: Base + { portOccupancy: number[], maxVisible=PORT_MATRIX_MAX_VISIBLE }
- ONTCockpit: Base + { signal?: SignalEntry, utilizationPct? }
- PassiveCockpit: Base + { insertionLossDb?: number }

All cockpits render pure SVG; no DOM measurements during rAF commit. Overflow content uses clipPath.

### 16.6 Signal-Budget Modell (Frontend Darstellung)

Backend liefert authoritative: received_dbm, margin_db, signal_status, path breakdown. Frontend berechnet NICHT neu (Vermeidung von Drift). Margin Schwellen (OK ≥6, WARN 3–6, CRITICAL 0–3, NO_SIGNAL <0) rein visuell gezeigt (Chips + color ring on ONT). Tooltips erlauben segmentierte Loss-Darstellung (link + passive Anteil). Path liste optional collapsible.

### 16.7 Port Matrix Darstellung

Column-based grid; each cell: 8×8 (scalable). Occupancy Farbskala buckets: 0% (empty neutral) / (0–50] / (50–80] / (80–100] / >100% (overload pulsierend). Overflow > N (konfigurierbar, default 32): Scrollbar (SVG mask + clip) oder Aggregationssymbol mit Tooltip (listet ausgelassene Ports). Virtualisierung optional (Phase 2) bei sehr großen Portzahlen.

### 16.8 Link Visualisierung

Link stroke color & width mapped to utilization bucket (shared from UTILIZATION_BUCKETS). Overload (≥100%) animierter dash oder pulsierende Breite. Tooltip (hover): Länge (km to 2 decimals), Fasertyp (key), berechnete Dämpfung (Y.YY dB). Passive optical info resides in linkUpdated & fiber meta.

### 16.9 Tooltip System

Single global <TooltipHost> (absolut positioniert). rAF-throttled reposition. Delay hysterese 80ms Eintritt / 120ms Exit um Flickern zu verhindern. Accessible fallback via focus outlines & aria-describedby IDs. Device tooltips optional (e.g., quick signal snapshot on ONT hover). Link tooltips show fiber meta & current utilization_percent.

### 16.10 Performance & Batching

Techniken: Delta coalescing map, rAF commit, fine-grained computed selectors (avoid deep reactive objects), early bail if version unchanged, port matrix lazy expand on hover, shared color scale arrays, text clipping for long IDs, minimal reflow (pure SVG). Render Budget Overlay (dev-only) counts cockpit component renders pro frame. Target: ≤ 3ms commit @ 2000 devices & 3000 links for typical metrics delta.

Scalability Thresholds (Worker Offload Trigger Guidance):

- Consider WebWorker delta normalization when sustained cockpit update coalesced batch > 5000 entities per second OR average commit time > 5ms over 120 consecutive frames.
- Consider GPU/canvas hybrid for links when link DOM count > 10k and frame budget exceeds 4ms purely from stroke updates.
- If port matrix virtualization triggers > 30 layout thrashes per 5s interval, move matrix rendering to deferred idle callbacks.

### 16.11 Accessibility & Theming

ARIA: group roles with aria-label "<display_id> status <status> utilization <x%>". High-contrast mode: CSS vars alternate palette. Color + Icon dual-encoding (✓ OK, ! Warn, ✕ Critical, Ø NoSignal). Keyboard nav: tab cycles nodes (outline focus ring). Legend auto-generated from colorScale.ts.

### 16.12 Risiken & Mitigation

| Risiko                              | Wirkung               | Mitigation                               |
| ----------------------------------- | --------------------- | ---------------------------------------- |
| Re-render Storm                     | FPS Einbruch          | Coalescing, version check, rAF batch     |
| Große Port Sets                     | DOM Kosten            | Scroll + lazy expand + aggregation glyph |
| Tooltip Jitter                      | Schlechte UX          | Hysterese & rAF Position                 |
| Farbblindheit                       | Erkennbarkeit         | Icon + Pattern + Text Labels             |
| Signal Race (metrics before signal) | Inkonsistente Anzeige | Enforce backend event order (§11)        |

### 16.13 Erweiterungen (Future)

- GPU/Canvas layer für Links bei >10k edges (hybrid).
- Worker für Delta Normalisierung.
- Cluster / Level-of-Detail (LOD) Aggregation bei Zoom-Out.
- Path margin heatmap overlay.
- Export/Screenshot (serialize <svg>).
- Batch micro-ticks & scenario sandbox injection layer.

### 16.14 Offene Implementierungsdetails (RESOLVED)

- Signal-Budget Rechenort: Backend (final). Frontend nur Darstellung.
- OLT Port Overflow: Scroll + Tooltip (keine pagination UI im MVP).
- Kein foreignObject: reine SVG für Performance & Browser-Konsistenz.

### 16.15 Neue Konstanten / Konfiguration (Frontend Konvention)

```

COCKPIT_BASE_WIDTH = 120
COCKPIT_BASE_HEIGHT = 70
PORT_MATRIX_MAX_VISIBLE = 32
TOOLTIP_SHOW_DELAY_MS = 80
TOOLTIP_HIDE_DELAY_MS = 120
RENDER_BUDGET_WARN_THRESHOLD = 0.25 # ms per cockpit avg (heuristic)

```

### 16.16 Teststrategie (Zusatz zu §15.15)

Unit: Mapping funktionen (util→bucket, signal→icon). Snapshot: minimal structural DOM (strip dynamic numbers). Perf Harness: Synthetic 2k Device Delta → assert < X mutated nodes. E2E: Hover link → correct tooltip; injection immediate micro-tick pulses only affected nodes.

### 16.17 Aufgaben Mapping (TASK-071..086 / optional 087..088)

Siehe TASK.md Abschnitt Milestone M8 für vollständige Auflistung & Abhängigkeiten.

### 16.18 Legenden & Farbquellen

Single file colorScale.ts exportiert: STATUS_COLORS, UTIL_BUCKET_COLORS, SIGNAL_COLORS, PORT_OCCUPANCY_COLORS. Frontend Legend UI bezieht sich ausschließlich auf diese Maps (Vermeidung divergenter Hardcodes).

### 16.19 Render Budget Overlay (Dev Feature)

Optional panel (`?renderDebug=1`) zeigt: lastFrameCockpitRenders, avgRenderTimeMs, changedDevicesCount. Aktiv nur in devMode.

### 16.20 Migration & Einführungsreihenfolge

Incremental Rollout (Ref): 1 Base + Router Cockpit → 2 Link Utilization → 3 Signal ONT → 4 Port Matrix → 5 Passive Cockpits → 6 Tooltip Engine → 7 Performance pass → 8 Accessibility/Theming → 9 Tests & Polish.

### 16.21 Abhängigkeiten zu existierenden Abschnitten

Re-use event contract (§8), determinism ordering (§11), simulation metrics (§15), config endpoint (§15.20). No schema duplication; signal & metrics shapes remain authoritative in respective sections.

### 16.22 Fehlerbehandlung & Edge Cases

UI handling for partial payloads and ordering:

- If signalStore entry lacks path or margin_db, display UNKNOWN chip and avoid misleading values.
- If deviceStatusUpdated arrives before deviceSignalUpdated, ONT cockpit shows status border updated immediately; signal chip updates later without layout shift.
- If linkMetricsUpdated missing for a link, default utilization bucket to 0% neutral styling.
- Drop out-of-order deltas by version.

### 16.23 Änderungsprotokoll Bezug

Revision r3 introduced this section; any deviation in implementation must update both this section & TASK.md dependencies.

---

End Section 16.

## 17. Stable Physics Engine (Incremental D3 Force Layout) (ON HOLD)

Status: ON HOLD / To Be Redefined. Drag/pin and deterministic transforms remain under simple non-physics movement. Full incremental force integration is paused; the section below is retained for future resumption and may be revised.

Authoritative design for a non-destructive, incremental D3 forceSimulation integration. Eliminates layout "twitch" by preserving internal integrator state across all topology changes. References: §9 (UI Interaction Model) & §16 (Cockpits) — this section governs spatial lifecycle only.

### 17.1 Prinzip & Lebenszyklus

- Single instantiation: `forceSimulation` created once during initial topology bootstrap; NEVER re-created due to graph mutations.
- Node identity preservation: PhysicsNode objects retained (mutated in-place) so velocities (vx, vy), alpha, and cooling curve continuity are maintained.
- Separation of concerns: Semantic device/link data lives in Pinia (topologyStore). A distinct physics layer mirrors only layout fields (x,y,vx,vy,fx,fy, pinned flags).

### 17.2 Datenstrukturen

Physics Node (runtime only): `{ id, type, x, y, vx, vy, fx?, fy?, pinned, userPinned, systemPinned, degree, createdAt, lastManualMoveAt? }`.
Physics Store State: `nodes: Map<id,PhysicsNode>`, `links: PhysicsLink[]`, `running:boolean`, `pinnedCount`, `layoutVersion`, `pendingDirty:Set<id>`, `config:{ repelStrength, linkDistanceBase, linkDistancePassiveFactor, collideRadius, alphaMin, alphaDecay }`.

### 17.3 Initialisierung & Platzierung

1. Lade Geräte & Links (erste vollständige Snapshot-Phase).
2. Falls persistierte Koordinaten vorhanden → anwenden.
3. Sonst heuristisches Seed-Layout:
   - Backbone/Core: Ring / radial (golden angle) um Zentrum.
   - POP / Container: Nähe Parent / Backbone-Knoten.
   - OLT / AON: Gruppiert um POP / Backbone.
   - ONT / CPE: Fächer (sector) um zugehörige OLT mit zufälligem Jitter.
4. Simulation Forces:

```

forceSimulation(nodes)
.force('link', forceLink(links).id(d=>d.id).distance(linkDistanceFor))
.force('charge', forceManyBody().strength(config.repelStrength))
.force('center', forceCenter(width/2, height/2))
.force('collide', forceCollide().radius(config.collideRadius))
.alpha(1)
.alphaDecay(config.alphaDecay)
.alphaMin(config.alphaMin)
.on('tick', tickHandler)

```

### 17.4 Inkrementelle Graph-Updates

Ein Vue-Watcher detektiert strukturelle Änderungen (IDs hinzu/entfernt). Algorithmus:

1. Added Devices → PhysicsNode anlegen, Startposition: Mittelwert existierender Nachbarn (oder Center + jitter wenn isoliert).
2. Removed Devices → aus Node-Map & Array entfernen (zuerst Links filtern, dann Node entfernen).
3. Added / Removed Links: Rebuild link array minimal (Filter + Append).
4. Apply:

```

simulation.nodes(currentNodesArray)
simulation.force('link').links(currentLinksArray)
if (structuralChanged) simulation.alpha(adaptiveAlpha).restart()

```

Adaptive Alpha: kleine Mutation (<=2 nodes) => 0.12; sonst 0.3.

### 17.5 Benutzerinteraktion: Drag & Pinning

- Drag Start: `alphaTarget(0.25).restart()`.
- Drag Move: set `node.fx = x; node.fy = y; node.userPinned = true; pendingDirty.add(id)`.
- Drag End: `alphaTarget(0)`.
- Multi-Select Pin / Unpin: toggelt `userPinned` (fx/fy setzen oder löschen).

### 17.6 Stop / Start Physics

Stop:

```

simulation.stop()
for node: if !node.userPinned { node.systemPinned = true; node.fx = node.x; node.fy = node.y }
running=false

```

Start:

```

for node: if node.systemPinned { node.systemPinned=false; if(!node.userPinned){ node.fx=null; node.fy=null } }
running=true
simulation.alpha(1).restart()

```

Dual-Level Pinning (userPinned vs systemPinned) verhindert versehentliches Lösen bewusst fixierter Nodes.

### 17.7 Persistenz & Backend Sync

PATCH Endpoint: `/api/layout/positions` payload `{ version?, positions:[{id,x,y,pinned}] }`.
Throttle: Flush alle 2s oder wenn `pendingDirty.size >= 40`.
Merge-Strategie beim Reload: Server-Koordinaten überschreiben lokale nur falls Node nicht `userPinned` (Konflikte protokollieren). Version mismatch -> Soft-Merge (kein Hard-Reset).

### 17.8 Tick Handler & DOM Update

`tickHandler` mutiert ausschließlich:

- Node `<g>`: `transform="translate(x,y)"`.
- Link `<line>` (oder path) Attribute: `x1,y1,x2,y2` (oder `d`).
  Keine Vue-Reaktivität für jede Koordinate (Performance). Frame-Metriken sammeln (optional) für Render Budget Overlay (§16.19).

### 17.9 Link-Stabilität

Links referenzieren persistente Node-Objekte (`source` / `target`). Keine Re-Creation → Kein "Verlust" beim Verschieben. Entfernen sicher über Filter + Rebinding.

### 17.10 Edge Cases

| Szenario                   | Mitigation                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------ |
| Node entfernt während Drag | Drag-End prüft Existenz; ignoriert sonst                                             |
| Massive Node-Batches       | Temporär `alpha(0.5)`, niedrigere charge (-40) danach revert                         |
| >5k ONTs                   | After settle: auto `simulation.stop()` + lazy incremental local relax                |
| >70% pinned                | Hinweis & Option "Disable Physics"                                                   |
| Reconnect ohne Layoutdaten | Heuristische Neuplatzierung + Interpolation beim Eintreffen persistierter Positionen |

### 17.11 Adaptive Performance

- Dynamische charge-Funktion: `strength = base * sqrt(1000 / max(n,1000))` clamp.
- Skip DOM Updates: Option nur jeden 2. Tick bei hoher CPU.
- AutoStop bei Inaktivität: Kein Delta + keine Interaktion > 30s.
- Anti-Jitter Filter: Positionsdelta < 0.05px → skip transform write.

### 17.12 Tests

Unit: placement heuristics (deterministisch mit seed), mergeLogik, adaptiveAlpha.
Integration (Vitest+jsdom): Add/Remove Node verändert nicht existierende Node-Referenzen. Drag setzt fx/fy & pinned Flags. Persistence throttle (fake timers). Snapshot Guard: Kein zusätzlicher `new forceSimulation` nach init.

### 17.13 Erweiterungen (Future)

- Worker-Offload (Positionsberechnung in Worker, DOM apply main thread)
- Cluster / LOD (verweist §16.13) vor Physikstart für entfernte Zoomlevel
- GPU Link Layer ab >10k Links
- Layout Health Metrics (avgLinkStretch, pinnedRatio) Overlay

### 17.14 Risiken & Mitigation

| Risiko                          | Wirkung      | Mitigation                                        |
| ------------------------------- | ------------ | ------------------------------------------------- |
| Unbeabsichtigter Neuaufbau      | Layout-Reset | Dev assert wrapper um forceSimulation             |
| Persistenz Flood                | Backend Load | Batched + distinct ID merges                      |
| Performance Drift große Graphen | Latenz       | Adaptive forces + AutoStop + Worker Option        |
| Race Delta vs Drag              | Spring-Back  | `node.dragging=true` ignoriert externe pos-Deltas |

### 17.15 Aufgaben Mapping

Siehe TASK.md (TASK-092..106). Implementation MUSS diese Reihenfolge respektieren: Bootstrap (093) → Delta Applier (094) → Drag (095) → Placement (097) → Persistence (098) → Merge (099) → Perf Metrics (100) → Tests (101) → Docs (102) → Adaptive (103) → Partial Freeze (104) → Health Overlay (105) → Worker POC (106).

### 17.16 Änderungsprotokoll

Revision r4 fügt stabile Physics Engine hinzu. Änderungen an Force-Parametern oder Persistenzschema erfordern Update dieses Abschnitts und TASK.md Dependencies.

---

End Section 17.

## 18. Pathfinding Logic

<!-- Existing Section 18 content retained above (placeholder note for context; actual detailed pathfinding spec already present earlier in doc). -->

## 19. Ring Protection (Failure Link Protection)

### 19.1 Motivation

Placeholder: Prevent loops in physical fiber rings by logically blocking one deterministic link; enable fast failover & recovery.

### 19.2 Terminology

Placeholder: physical_status (raw) vs logical_status (exposed), protection_mode (AUTO_BLOCKING, AUTO_FORWARDING, MANUAL_BLOCKING, NONE), ring_id (hash of sorted link ids).

### 19.3 High-level Goals

Placeholder: Deterministic selection, minimal churn, debounce flaps, override precedence, scalable detection.

### 19.4 Data Model Changes

Placeholder: Extend Link.status with BLOCKING; add Link.protection_mode; future API dual-status exposure.

### 19.5 Configuration Flags

Placeholder: ENABLE_RING_PROTECTION, RING_PROTECTION_DETERMINISM, RING_PROTECTION_DEBOUNCE_MS, RING_PROTECTION_RECOVERY_DELAY_MS, RING_PROTECTION_MAX_CYCLE_LENGTH, RING_PROTECTION_MAX_RINGS_TRACKED, RING_PROTECTION_OVERLAP_STRATEGY, RING_PROTECTION_IGNORE_PASSIVE_NODES.

### 19.6 State Machine

Placeholder: Healthy (one BLOCKING) → Failover (BLOCKING→UP when other DOWN) → Recovery (re-block after delay) → Healthy.

### 19.7 Algorithm Outline

Placeholder: Build active graph; compute cycle basis; select deterministically; apply status transitions with debounce.

### 19.8 Determinism Rules

Placeholder: Lexicographically highest link id (initial policy), stable absent mutations.

### 19.9 Event Model

Placeholder: New link.protection.updated event emitted before link.status.changed; ordering table update pending.

### 19.10 Overlapping Rings Strategy

Placeholder: Phase 1 PER_CYCLE; future MIN_BLOCK_SET optimization.

### 19.11 Debounce & Recovery

Placeholder: Separate debounce & recovery delay windows mitigate flapping.

### 19.12 Admin Overrides

Placeholder: Manual block supersedes auto; alternate candidate chosen.

### 19.13 Metrics & Observability

Placeholder: Counters (failover/recovery), histograms (convergence), gauges (ring_total, overlapping_factor).

### 19.14 Testing Strategy

Placeholder: Unit (cycles, selection), Integration (failover/recovery), Property (invariant), Performance (1k links cycles).

### 19.15 Limitations & Future Work

Placeholder: No persistence initial, no weighted policy, no domain partitioning yet.
