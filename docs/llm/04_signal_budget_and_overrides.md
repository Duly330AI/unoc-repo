## 5. Status Simulation & Propagation

### 5.1 Single Source of Truth (Current)

Authoritative logic lives in `backend/services/status_service.py`:

- Admin override wins: DOWN overrides any computed value; UP can force online but may be constrained by device-specific rules in the future.
- ALWAYS_ONLINE devices → `UP`.
- **PASSIVE devices:** use the propagation snapshot; unreachable from anchors → `DEGRADED`. Reachable (e.g., in a valid chain between UP OLT and UP ONT) → UP.
  - **Note:** The status of passive devices (UP/DEGRADED) is for display/propagation purposes only and does not affect optical pathfinding. The Dijkstra algorithm uses topological connectivity and attenuation values regardless of passive device status.
- ACTIVE devices:
  - Unprovisioned → `DOWN`.
  - Provisioned → `UP` only if `dependency_resolver.evaluate_upstream_dependencies(...).ok` is true; otherwise `DEGRADED`.
  - ONT / Business ONT with `signal_status == NO_SIGNAL` → `DOWN` (unless overridden as above).

Propagation builder and dependency checks are inputs; only the status service sets the final computed status.

### 5.2 Pseudocode (Centralized Evaluation)

```
compute_device_status(d):
  if d.admin_override == DOWN: return DOWN
  if d.role == ALWAYS_ONLINE: return UP
  if d.role == PASSIVE:
     return UP if propagation_snapshot.is_up(d.id) else DEGRADED
  if d.role == ACTIVE:
     if not d.provisioned: return DOWN
     if d.type in {ONT, BUSINESS_ONT} and d.signal_status == NO_SIGNAL: return DOWN
     return UP if dependency_resolver.ok(d) else DEGRADED
```

### 5.3 ONT Online Rule

ONT effective_status = online only if:

1. provisioned = true
2. path resolved to an OLT
3. signal_status != NO_SIGNAL
4. override does not force down (override=down supersedes; override=up can force online; conflict policies may evolve).

```

### 5.4 Edge Cases
- Cycles (should be prevented at link creation; otherwise visited set guards propagation).
- Orphan passive devices remain offline.
- Bulk changes: may coalesce events (see Event Coalescing).

## 6. Signal Budget Model ("Light")
### 6.1 Path Resolution
Goal: For each ONT, find exactly one upstream OLT path through passive inline devices. If multiple OLTs are reachable, choose the path with the lowest total attenuation; apply deterministic tie-breakers when equal.

Algorithm (resolve_optical_path):
1. Run Dijkstra from the ONT on the optical graph with a custom weight consisting of per-link fiber loss plus passive insertion loss when entering interior passive nodes.
2. Per-link fiber loss uses Link.length_km multiplied by the attenuation coefficient from the link's selected Physical Medium: Link.physical_medium_id → PhysicalMedium.code → FIBER_TYPES[code].attenuation_db_per_km.
3. Sum Device.insertion_loss_db for interior passive devices (ODF/NVT/SPLITTER/HOP).
4. Collect all reached OLTs and sort candidates by (total_attenuation_db, total_physical_length_km, hop_count, olt_id, path_signature). Pick the first.

**Determinism:** The detailed tie-breaker cascade (including path_signature) ensures stability and prevents flapping between equivalent paths. When two paths have identical attenuation, length, and hop count, the lexicographically smallest path_signature (ordered node list) guarantees consistent selection across recomputations.

### 6.2 Attenuation Components
For a chosen path P:
- Link fiber loss: Link.length_km × attenuation_db_per_km, with the coefficient resolved via PhysicalMedium.code → FIBER_TYPES[code].attenuation_db_per_km.
- Passive device loss: Device.insertion_loss_db for interior passives.
- Splitter loss: represented via insertion_loss_db (may vary by split ratio in a future phase).
- Connector loss: deferred (not modeled in this phase).

Total Path Attenuation:
```

total_path_attenuation_db = Σ(link_loss_db) + Σ(passive_insertion_loss_db)

```

### 6.3 Receive Power & Margin
```

received_power_dbm = olt.tx_power_dbm - total_path_attenuation_db
margin_db = received_power_dbm - ont.sensitivity_min_dbm

```

If path unresolved → signal_status = NO_SIGNAL (no computation).

### 6.4 Classification Logic
Use ONT sensitivity as base threshold. Default classification (tunable constants):
| Status    | Condition                        |
| --------- | -------------------------------- |
| OK        | margin_db >= 6.0                 |
| WARNING   | 3.0 <= margin_db < 6.0           |
| CRITICAL  | 0 <= margin_db < 3.0             |
| NO_SIGNAL | margin_db < 0 OR path unresolved |

### 6.5 Emission Rules
Emit deviceSignalUpdated when any of: (a) status changes, (b) |received_power_dbm - previous| >= 0.1, (c) margin classification boundary crossed.
If signal_status transition causes ONT effective_status change, emit deviceStatusUpdated after signal event in same tick (ordering guarantee).

### 6.6 Recompute Triggers
- Creation/deletion of a Link on any candidate path.
- Update to Link.length_km or Link.physical_medium_id (changes attenuation via FIBER_TYPES).
- Update to PhysicalMedium specs (attenuation_db_per_km) – treated as global invalidation.
- Update to Device.insertion_loss_db for any interior passive on the path.
- Update to OLT tx_power_dbm or ONT sensitivity_min_dbm (when used to classify signal).
- ONT provisioning event.

**Cache Invalidation Scope (MVP):** Global. Any topology or optical-attribute change that could affect paths triggers:
- `PathfindingStore.bump_version()` → increments `topo_version`, invalidates built graph caches, and clears the optical resolver's LRU cache (`resolve_optical_path.cache_clear()`).
- `optical_service.recompute_optical_paths_for_affected_onts()` currently recomputes for all provisioned ONTs (not selective yet). This ensures correctness at the expense of extra work; selectivity can be added later.

### 6.7 Determinism
Deterministic selection via the tuple (total_attenuation_db, total_physical_length_km, hop_count, olt_id, path_signature). If all prior keys tie, the lexicographically smallest path_signature (concatenated ordered node IDs) wins.

Purpose: This deep determinism explicitly prevents flapping between equivalent paths; repeated recomputations will choose the same path when candidates are identical by cost and structure.

### 6.8 Data Shapes (Frontend Consumption)
deviceSignalUpdated payload extended:
```

{
"id": "<ont-id>",
"received_dbm": -17.5,
"signal_status": "OK",
"margin_db": 12.5,
"path": {
"olt_id": "<olt-id>",
"total_attenuation_db": 22.5,
"segments": [
{ "src": "<nodeA>", "dst": "<nodeB>", "link_id": "<L1>", "attenuation_db": 5.2 },
{ "src": "<nodeB>", "dst": "<nodeC>", "link_id": null, "attenuation_db": 3.5 }
]
}
}

```
**Note (current implementation):** The resolver produces segment details (`OpticalPathResult.segments`), but the WebSocket event `device.optical.updated` sends only a compact summary: `{id, received_dbm, signal_status, margin_db}`. Segment lists are not included today and would require an additional endpoint or an event schema extension.

### 6.9 Validation & Errors
- Negative length_km → ATTENUATION_PARAM_INVALID.
- Unknown fiber_type key → FIBER_TYPE_INVALID.
- insertion_loss_db < 0 → ATTENUATION_PARAM_INVALID.

### 6.10 Fiber Types Catalog (authoritative)
The authoritative set is defined in backend.constants.optical.FIBER_TYPES and surfaced via API. Keys MUST be stable; changing values is a versioned architectural decision.

| key        | mode | standard | attenuation_db_per_km |
| ---------- | ---- | -------- | --------------------- |
| SMF_G652D  | SMF  | G.652D   | 0.35                  |
| SMF_G657A1 | SMF  | G.657A1  | 0.35                  |
| SMF_G657A2 | SMF  | G.657A2  | 0.35                  |
| MMF_OM3    | MMF  | OM3      | 3.50                  |
| MMF_OM4    | MMF  | OM4      | 3.00                  |

UI dropdowns must derive from this list (see API surface below) to avoid drift.

### 6.11 API Surface (optical)
- GET /api/optical/fiber-types → [{ key, mode, standard, attenuation_db_per_km }]
  - Source of truth for available fiber type keys and coefficients used by PhysicalMedium.

## 7. Admin Override System
Field: admin_override_status (null | up | down) on devices & links.
Evaluation order:
1. Compute base status.
2. Apply link overrides (affects whether path considered viable).
3. Apply device overrides (force effective status) with precedence: down > computed > up.
Events: deviceOverrideChanged (with effective_status), linkStatusUpdated (if link forced down).
Validation: If override=up but mandatory path segment missing → log OVERRIDE_CONFLICT.

**Admin Override Conflicts:** When an admin override forces a device to UP status but the device lacks a valid path (e.g., an ONT with no optical path to an OLT), the override takes precedence. The system logs an OVERRIDE_CONFLICT event, but the effective_status remains UP as specified by the override. This allows for diagnostic scenarios where a device might be forced online despite logical inconsistencies.
```
