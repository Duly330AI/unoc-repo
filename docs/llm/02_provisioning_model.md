## 3. Provisioning Model & Provision Matrix

Provisioning transitions a device from created → provisioned and triggers (atomic transaction):

1. Pre-validation (dependencies, container context, uniqueness).
2. Interface realization (management interface now; p2p uplinks later when links created).
3. IP assignment via lazy IPAM (pool materialization if first usage).
4. Status phase 1 computation update for that device.
5. Optical recomputation trigger if device influences optical path (OLT / passive / ONT).
6. Event emission (deviceStatusUpdated, deviceSignalUpdated if applicable, deviceCreated already handled earlier).

### 3.1 Provision Matrix (Authoritative)

Defines what provisioning operations are valid. Table focuses on direct provisioning of a device type and required preconditions.

| Device Type                           | Provision Allowed? | Required Existing Upstream      | Required Container     | Disallowed Conditions                       | Side Effects                    | Notes                                                                                                                                            |
| ------------------------------------- | ------------------ | ------------------------------- | ---------------------- | ------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backbone Gateway                      | implicit (seed)    | none                            | none                   | >1 backbone gateway if single-backbone mode | Marks always_online root        | Created via bootstrap not endpoint in MVP                                                                                                        |
| Core Router                           | yes                | Backbone Gateway present        | none                   | Missing backbone                            | mgmt interface + core_mgmt IP   | May become multiple (scalable) later                                                                                                             |
| Router (edge)                         | yes                | Core Router reachable (logical) | none                   | No core router provisioned yet              | mgmt interface + core_mgmt IP   | Pool mapping determined by classification                                                                                                        |
| OLT                                   | yes                | Core Router (logical upstream)  | POP **only** (see 3.2) | Not inside POP; missing core                | mgmt interface + access_mgmt IP | tx_power_dbm editable post provision; parent is optional at creation; if set it must be POP. Provisioning enforces POP-only when parent present. |
| AON Switch                            | yes                | Core Router (logical upstream)  | POP **only** (see 3.2) | Not inside POP; missing core                | mgmt interface + access_mgmt IP | Hosts access layer fan-out; parent is optional at creation; if set it must be POP. Provisioning enforces POP-only when parent present.           |
| ONT                                   | yes                | OLT reachable via passive chain | none                   | No OLT path                                 | mgmt interface + ont_mgmt IP    | Signal gating applies                                                                                                                            |
| Business ONT                          | yes                | OLT reachable                   | none                   | No OLT path                                 | mgmt interface + ont_mgmt IP    | Same signal rules                                                                                                                                |
| AON CPE                               | yes                | AON Switch reachable (strict)   | none                   | No upstream path via AON Switch             | mgmt interface + cpe_mgmt IP    | Strict upstream to CORE via switch                                                                                                               |
| POP                                   | no (non-active)    | n/a                             | n/a                    | Attempt to provision                        | none                            | Passive container only                                                                                                                           |
| Passive Inline (ODF/NVT/Splitter/HOP) | no                 | n/a                             | n/a                    | Attempt to provision                        | none                            | Passive elements do not provision                                                                                                                |

**Key Updates to 3.1:**

- Added explicit "POP **only**" under Required Container for OLT/AON Switch to reflect current provisioning constraints (see 3.2 validation details).

### 3.2 Validation Order

1. Existence & type check (device present, not already provisioned, type is provisionable).
2. Dependency & path validation (graph-based): logical graph reachability (Core↔OLT/AON_SWITCH) and optical path (OLT→ONT / Business ONT) plus AON_SWITCH reachability for AON_CPE (and thus CORE via that switch) are enforced strictly (TASK-030B).
3. **Container correctness (parent_container_id rules) – IMPLEMENTED with strict enforcement:**

- **OLT / AON Switch:** Parent is OPTIONAL during creation. If provided, it **MUST be POP**. Provisioning-time validation enforces POP-only when a parent is present (see `DEVICE_PARENT_POOL_MAP`). Invalid parent ⇒ `CONTAINER_REQUIRED 422`.
- CORE_ROUTER / EDGE_ROUTER: MUST NOT have a parent (unexpected parent ⇒ `INVALID_PROVISION_PATH 400`).
- ONT / Business ONT / AON CPE: parent is optional; if provided it must not be POP/CORE_SITE (containers). Invalid container parent ⇒ `INVALID_PROVISION_PATH 400`.
- Passive inline (ODF/NVT/Splitter/HOP): parent optional; if provided it must exist (non-container or container allowed for placement).

4. IPAM pool availability (pool exhaustion → abort with `POOL_EXHAUSTED`).
5. Interface uniqueness (no existing management interface).
6. Concurrency guard (optimistic: check device provisioned flag again before commit).

### 3.3 Algorithm (Pseudocode)

```python
provision_device(device_id):
  with transaction():
     d = load(device_id, for_update=True)
     assert d.type in PROVISIONABLE_TYPES, INVALID_PROVISION_PATH
     assert not d.provisioned, ALREADY_PROVISIONED
     validate_dependencies(d)  # Includes container checks (3.2 step 3)
     pool_key = map_device_to_pool(d.type)
     ensure_pool(pool_key)
     ip = allocate_next(pool_key)
     create_management_interface(d, ip)
     d.provisioned = True
     persist(d)
  # Status/Optical recompute runs ASYNC post-transaction
  recompute_status_phase1(d)  # Non-transactional for performance
  if d.type in (OLT, ONT, Business ONT, AON Switch):
      trigger_optical_recompute(d)  # May take >1 tick to complete
  emit_deltas(d)  # WebSocket event with latest status
```

**Key Update to 3.3:**  
Added explicit note that status/optical recompute is asynchronous and may take multiple ticks to reflect in the UI.

### 3.4 Dependency Validation Details

| Target Type        | Checks                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------- |
| Core Router        | at least one Backbone Gateway exists                                                        |
| Router (edge)      | at least one Core Router exists (strict)                                                    |
| OLT                | at least one Core Router exists (logical). Parent **MUST be POP** (enforced in 3.2 step 3). |
| AON Switch         | at least one Core Router exists (logical). Parent **MUST be POP** (enforced in 3.2 step 3). |
| ONT / Business ONT | path to at least one OLT (strict; no soft dependency mode exists)                           |
| AON CPE            | reachability to Core Router (via AON Switch) (strict)                                       |

### 3.5 Error Code Mapping

| Condition                                                    | Error Code                 | HTTP |
| ------------------------------------------------------------ | -------------------------- | ---- |
| Missing dependency                                           | `INVALID_PROVISION_PATH`   | 400  |
| Already provisioned                                          | `ALREADY_PROVISIONED`      | 409  |
| Pool exhausted                                               | `POOL_EXHAUSTED`           | 409  |
| No management interface room (should not happen)             | `DUPLICATE_MGMT_INTERFACE` | 400  |
| POP/CORE_SITE parent missing/invalid when required           | `CONTAINER_REQUIRED`       | 422  |
| Unexpected parent set for non-container device               | `INVALID_PROVISION_PATH`   | 400  |
| Invalid container parent for endpoint (e.g., ONT parent=POP) | `INVALID_PROVISION_PATH`   | 400  |

### 3.6 Extensibility Hooks

- Pluggable rules engine: `PROVISION_MATRIX` could be YAML-driven later; initial code constant.
- Dry-run mode: `/provision?dry_run=1` returns prospective operations and IP.
- Batch provisioning endpoint (future) taking list of `device_ids` applying dependency ordering.
- **Optical recompute hook (TASK-112):** After provisioning optical-relevant devices (OLT, ONT, Business ONT, passive inline), a placeholder recompute call executes and emits `device.optical.updated` event with payload `{affected_device_ids[], reason:"provision"}`. Link create/delete also trigger recompute. Until real path math lands, this event is a no-op signal for frontend subscription wiring.

### 3.7 De-Provision (Deferred)

Not in MVP. When implemented: mark deprovisioned, optionally release IP (if reclamation policy evolves), emit status recalculation (dependents may remain unaffected except for optical recalculation).

### 3.8 API Endpoints (Provisioning)

- POST `/api/devices/{id}/provision` → 200 { device } or error codes above.
- GET `/api/provision/matrix` (future) → JSON representation for UI hints.
  Response device includes `provisioned=true`, management interface list, any immediate signal gating status changes (if ONT).

### 3.9 Testing Strategy (Minimum)

- Unit: dependency validation matrix (table-driven tests).
- Unit: pool allocation idempotence (provisioning twice returns 409).
- **Integration:** Sequence Core Router → OLT in POP → ONT (strict mode) results in ONT provision rejection until optical path established (if strict dependency).
- Performance: provisioning single device under concurrent attempts (simulate race) ensures only one success.

### 3.10 Observability

- Log structured entry: `{event: provision.start, device_id, type}` and `{event: provision.success, pool_key, ip}`.
- Metrics counters: `provision_success_total{type}`, `provision_failure_total{reason}`.
- **Note:** Status/optical updates may lag behind the `provisioned` flag due to async recompute (see 3.3).

### 3.11 Condensed Device → Parent → Pool Mapping (Authoritative)

| Device Type                           | Provisionable? | Allowed Parent Container | Upstream Dependency (STRICT) | Pool Key (Mgmt)      | Notes                                                                                                         |
| ------------------------------------- | -------------- | ------------------------ | ---------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------- |
| Backbone Gateway                      | implicit seed  | none                     | none                         | core_mgmt (optional) | Always-online root. Created by bootstrap; mgmt IP allocation may be feature-flagged (ALLOW_BACKBONE_MGMT_IP). |
| Core Router                           | yes            | none                     | ≥1 Backbone Gateway          | core_mgmt            | Multiple allowed later; provides logical upstream for access layer.                                           |
| Router (edge)                         | yes            | none                     | ≥1 Core Router               | core_mgmt            | Edge routed node (future P2P /31 links).                                                                      |
| OLT                                   | yes            | POP **only**             | ≥1 Core Router               | access_mgmt          | Optical origin; parent optional. If set, must be POP. Provisioning rejects non-POP parents.                   |
| AON Switch                            | yes            | POP **only**             | ≥1 Core Router               | access_mgmt          | Access aggregation; parent optional. If set, must be POP. Provisioning rejects non-POP parents.               |
| ONT                                   | yes            | none                     | Reachable path to OLT        | ont_mgmt             | Optical path must exist at provisioning time (strict; no soft dependency mode exists).                        |
| Business ONT                          | yes            | none                     | Reachable path to OLT        | ont_mgmt             | Same semantics as ONT.                                                                                        |
| AON CPE                               | yes            | none                     | Reachable AON Switch         | cpe_mgmt             | Customer premises equipment variant.                                                                          |
| POP                                   | no             | n/a                      | n/a                          | n/a                  | Passive container only (never provisioned).                                                                   |
| Passive Inline (ODF/NVT/Splitter/HOP) | no             | n/a                      | n/a                          | n/a                  | Non-provisionable; optical attenuation contributors.                                                          |

**Key Updates to 3.11:**

- Explicitly marked OLT/AON Switch parent as "POP **only**" to reflect current provisioning constraints.

### 3.12 Link Type Classification & Rules

Defines allowed device endpoint combinations and semantic class of the link. Drives constant `LINK_TYPE_RULES` used by link creation validation & (later) interface realization for routed links.

Container endpoint invariant:

- **POP / CORE_SITE are containers and can never be link endpoints.** They serve only as physical parents/anchors. Pathfinding and the optical resolver operate on device↔device links; containers are therefore transparent to both logical dependency checks and optical signal calculations (no edges originate or terminate at containers).

Added in r6: Rule L6A (AON Switch ↔ Router) – access uplink.
Added in r7: Rule L6B (OLT ↔ Router) to visualize/logically model the management / aggregation uplink of an OLT toward the routed layer. It is intentionally non-optical (does not participate in optical attenuation) and shares the `access_uplink` class for now (future refinement may split into `olt_uplink`). Provisioning dependency rules remain unchanged (still require Core presence irrespective of physical link).

| Rule ID | Endpoint A (Role/Class)                     | Endpoint B (Role/Class)       | Link Class          | Allowed?   | Special Handling                 | Notes                                                                 |
| ------- | ------------------------------------------- | ----------------------------- | ------------------- | ---------- | -------------------------------- | --------------------------------------------------------------------- |
| L1      | Active (router-class: Backbone/Core/Router) | Active (router-class)         | routed_p2p          | yes        | /31 allocation (future TASK-027) | Deterministic endpoint ordering by device id for IP assignment.       |
| L2      | OLT (active)                                | Passive Inline                | optical_segment     | yes        | contributes optical path         | May chain multiple passives before ONT.                               |
| L3      | Passive Inline                              | Passive Inline                | optical_segment     | yes        | contributes optical path         | Splitter, ODF, NVT, HOP combinations allowed.                         |
| L4      | Passive Inline                              | ONT / Business ONT            | optical_termination | yes        | terminates path at ONT           | Last passive before ONT.                                              |
| L5      | OLT                                         | ONT (direct)                  | optical_segment     | yes (diag) | contributes optical path         | Simplified lab topologies (no passives).                              |
| L6A     | AON Switch                                  | Router-class (Edge/Core)      | access_uplink       | yes        | Maps to FIBER/P2P (impl detail)  | Non-optical uplink; excluded from optical attenuation.                |
| L6B     | OLT                                         | Router-class (Edge/Core)      | access_uplink       | yes        | Maps to FIBER/P2P (impl detail)  | OLT management/aggregation uplink; excluded from optical attenuation. |
| L6      | AON Switch                                  | AON CPE                       | access_edge         | yes        | (future traffic sim)             | Non-optical (Ethernet) – excluded from optical path calc.             |
| L7      | Active (non-OLT)                            | Passive Inline                | mixed_invalid       | no         | reject                           | Prevents illogical path (e.g., Core Router direct to passive).        |
| L8      | ONT/Business ONT                            | ONT/Business ONT              | peer_invalid        | no         | reject                           | No ONT↔ONT links.                                                     |
| L9      | Passive Inline                              | Backbone/Core/Router (active) | reverse_invalid     | no         | reject                           | Optical chain must originate at OLT (directional semantics).          |

**Key Clarification in Notes for L6B:**

- **L6B (OLT ↔ Router-class):** OLT management/aggregation uplink; excluded from optical attenuation. This link satisfies OLT's upstream dependency check (Core Router reachability) but does not contribute to optical path calculation for downstream ONTs.

### 3.13 Runtime Configuration Flags (Reference)

| Flag                             | Default      | Scope            | Effect                                        | Sections       |
| -------------------------------- | ------------ | ---------------- | --------------------------------------------- | -------------- |
| ALLOW_RELAXED_UPSTREAM_CHECK     | (removed)    | —                | **Removed** – upstream checks are strict-only | §3.1, §18.5    |
| STRICT_ONT_ONLINE_ONLY           | (planned)    | Status           | Reserved for future signal gating control     | §5, §15.17     |
| TRAFFIC_ENABLED                  | true (dev)   | Simulation       | Enables periodic metrics engine               | §15            |
| TRAFFIC_TICK_INTERVAL_SEC        | 2.0          | Simulation       | Tick cadence seconds                          | §15.6          |
| TRAFFIC_RANDOM_SEED              | (unset)      | Simulation       | Deterministic PRNG seed                       | §15.11         |
| TRAFFIC_INJECTION_ENABLED        | true (dev)   | Simulation Debug | Enables debug traffic injection               | §15.19         |
| TRAFFIC_INJECTION_MAX_GBPS       | 10000.0      | Simulation Debug | Injection upper bound                         | §15.19.4       |
| THRESHOLD_PATH_CACHE_FLUSH_RATIO | 0.5          | Pathfinding      | Cache global flush threshold                  | §18.8          |
| UNOC_DEV_FEATURES                | false (prod) | Global           | Gates dev-only UI/debug endpoints             | §15.20, §16.19 |
| ALLOW_BACKBONE_MGMT_IP           | (future)     | IPAM             | Optional mgmt IP for Backbone Gateway         | §3.11          |

**Note Added to 3.13:**

- `ALLOW_RELAXED_UPSTREAM_CHECK` is removed; upstream checks are strict-only. There is no "soft dependency mode" for ONTs.

### 18. Pathfinding Logic

Canonical specification for pathfinding (optical and logical upstream) now lives in `06_future_extensions_and_catalog.md` (§18). This document retains the §18 anchor for cross‑references and summarizes the integration points only:

- Provisioning dependency checks use the logical upstream graph (STRICT mode). See §18.5 in the canonical spec.
- Optical ONT signal gating uses the selected minimal‑attenuation path to an OLT. See §18.4.
- Cache invalidation on topology or optical attribute changes is delegated to the shared path cache. See §18.8.

For algorithms, data contracts, complexity and testing matrix, refer to: `/docs/llm/06_future_extensions_and_catalog.md#pathfinding-logic`.
