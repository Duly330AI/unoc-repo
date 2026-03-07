## 8. Real-time Delta Events

### 8.1 Event Inventory (MVP)

| Event                  | Payload (JSON Shape)                                                        | Trigger                           | Coalesce? | Notes                                                                        |
| ---------------------- | --------------------------------------------------------------------------- | --------------------------------- | --------- | ---------------------------------------------------------------------------- |
| deviceCreated          | { id, type, name, status }                                                  | POST /devices                     | no        | Initial acquisition                                                          |
| deviceStatusUpdated    | { id, status, override? }                                                   | Status recompute                  | yes       | Drop duplicates within tick                                                  |
| deviceSignalUpdated    | { id, received_dbm, signal_status, margin_db? }                             | Signal recompute                  | yes       | Compact payload (no path segments); fetch full breakdown via REST if needed  |
| linkMetricsUpdated     | { tick, items:[{ id, traffic_gbps, utilization_percent, version }] }        | Simulation Phase 2 tick diff      | yes       | Planned Phase 2 (TASK-057); only emitted when link metrics change (see §15). |
| linkUpdated            | { id, length_km, physical_medium_id?, physical_medium_code?, link_loss_db } | Optical attribute patch           | yes       | New for light editing; medium identifies attenuation via FIBER_TYPES         |
| deviceOpticalUpdated   | { id, insertion_loss_db? , tx_power_dbm? , sensitivity_min_dbm? }           | Attribute patch                   | yes       | Passive or OLT/ONT change                                                    |
| linkAdded              | { id, a_device, b_device, type }                                            | POST /links                       | no        |                                                                              |
| linkStatusUpdated      | { id, status, override? }                                                   | Link override / dependency change | yes       |                                                                              |
| deviceOverrideChanged  | { id, override_status, effective_status }                                   | Override mutation                 | no        |                                                                              |
| deviceContainerChanged | { id, parent_container_id } (nullable)                                      | Assignment / move                 | no        | parent_container_id can be null to unassign                                  |

### 8.2 Coalescing Strategy

Maintain an in-memory map keyed by (event_type, id) during a computation tick; flush at end.

### 8.3 WebSocket Contract

- Single endpoint: /api/ws (subprotocol none) – client sends auth placeholder (future) then receives stream. The WS path lives under the global API prefix.
  - Message envelope: { type: string, kind: string, payload: object, **topo_version?: int**, correlation_id?: string, ts: ISO8601 }
  - **topo_version**: Monotonically increasing version number reflecting the current state of the topology. Clients use this to detect missed events (e.g., receiving version 100 then 102 implies missing version 101 events). Clients should trigger a full topology resynchronization when gaps are detected.
  - Mapping (backend → kind):
    - device.provisioned → deviceCreated
    - device.status.changed → deviceStatusUpdated
    - device.optical.updated → deviceSignalUpdated (placeholder payload until optical engine lands)
    - device.provision.warning → deviceProvisionWarning
    - link.created → linkAdded
    - link.deleted → linkDeleted
- Heartbeat (ping/pong) TBD (not MVP) – rely on TCP keepalive initially.

Additional mapping used by the UI (completes the inventory in §8.1):

- link.updated → linkUpdated (optical attribute patch: length_km, fiber_type)
- link.status.changed → linkStatusUpdated (administrative or dependency-driven status)

## 9. UI Interaction Model

Three-column layout: Palette | Canvas | Context Panel + Header (viewer tabs; MVP only Topology).

**Central Canvas Invariant:** A single D3-managed topology canvas exclusively owns spatial transforms (pan, zoom, node position, link geometry). All Vue cockpit components are mounted inside stable `<g>` wrappers that only receive updated reactive data; they MUST NOT directly mutate layout geometry, pan/zoom state, or link paths. (Prevents feedback loops & ensures deterministic layout lifecycle.) **If cockpit content exceeds allocated space (e.g., long device names, dense metrics), Vue components must truncate text with ellipsis or wrap content internally without affecting the D3-managed geometry.**

### 9.1 Core Interactions

| Action                      | Mechanism                              | Result                       | Feedback                          |
| --------------------------- | -------------------------------------- | ---------------------------- | --------------------------------- |
| Create Device (single)      | Drag from Palette → Canvas             | POST /devices                | Ghost → solid on success          |
| Create Devices (bulk)       | Right-click Palette item → modal count | Multiple POSTs               | Toast summary "N devices created" |
| Select                      | Left click                             | selection[] update           | Highlight (glow)                  |
| Multi-select                | Ctrl+Click additional                  | Append selection             | Combined panel details            |
| Start Link                  | Context menu "Create Link From Here"   | Enter link mode              | Cursor change / hint              |
| Complete Link               | Click target device                    | POST /links                  | Flash new link                    |
| Provision                   | Button in Context Panel                | POST /devices/{id}/provision | Spinner → status badge            |
| Multi-Provision (selection) | Context menu "Provision Selected"      | POST each eligible device    | Batch toasts / aggregated result  |
| Assign POP Parent (batch)   | Context menu "Assign Parent POP"       | PATCH /devices parent change | Success toast / per-failure toast |
| Edit Link Optical Props     | Select link → form inputs              | PATCH /links/{id}            | Inline validation + toast         |
| Edit Passive Loss           | Select passive → numeric field         | PATCH /devices/{id}          | Immediate recompute (delta)       |
| View ONT Optical Analysis   | Select ONT                             | (read-only analysis panel)   | Live updated after deltas         |
| Move Device (future)        | Drag device node                       | PATCH position (future)      | Smooth transition                 |

### 9.2 State Model (Frontend High-Level)

```
store: {
devices: Device[],
links: Link[],
selection: string[],
ui: { viewMode: 'topology' },
pending: { deviceCreates: Set, linkCreates: Set, opticalEdits: Set }
}
```

### 9.3 Feedback Principles

- Non-blocking toasts for errors.

### 9.4 Bulk device creation modal (contract)

- Trigger: right-click a device type in the palette to open the modal.
- Inputs: count (>=1, enforced max); required container parent for OLT/AON_SWITCH when POP/CORE_SITE exist.
- Accessibility: focus trap, ESC to close, Enter to confirm, autofocus on count.
- Undo: removes all devices created in the batch.
- Placement: auto-layout to reduce overlap; persisted via /api/layout/positions.

### 9.5 Ports & interfaces summary (API box)

Endpoint: `GET /api/ports/summary/{device_id}` →

```
{ device_id, total, by_role: { ROLE: { total, used, max_subscribers? } } }
```

Rules for `used` counters:

- ACCESS/UPLINK: number of interfaces with matching role that are endpoints of any Link.
- PON (on OLT): number of provisioned ONTs whose resolved optical path terminates at this OLT (aggregated across PON ports).
- MANAGEMENT: 1 if a management interface exists on the device; else 0.

UI: The device Details panel reads this endpoint to render occupancy badges.

- Inline optimistic creation (ghost state) reverted on failure.
- Aggregated bulk results.
- Optical edit optimistic update: show provisional loss & revert if error.
- Undo toasts: bulk device creation emits a toast with an action button ("Undo") valid for a short window (default 5s) performing reverse-order deletion of created ids; partial failures summarized.

### 9.4 Panels (Detailed Requirements)

1. **Link Details Panel** (when a single link selected):
   - Editable: physical medium (dropdown from /api/optical/fiber-types by code), length_km (float, step 0.01).
   - Read-only: computed link_loss_db.
   - Validation: inline (red border + tooltip) for invalid values.
   - Save strategy: debounce 500ms or explicit save button (decide early; MVP explicit save).

Cross-reference: See optical catalog in §6.11 (04 Signal Budget) and backend endpoint `/api/optical/fiber-types` for authoritative keys.

2. **Passive Device Panel** (ODF / NVT / HOP / Splitter):

   - Editable: insertion_loss_db (step 0.1, min 0).
   - Immediate PATCH on change (debounced) for fluid workflow.

- SPLITTER-specific UI: shows a small "Ports [used/total]" badge sourced from `DeviceOut.parameters.splitter` (not from `/api/ports/summary`). See 07_container_model_and_ui.md §12 and 13_api_reference.md.

3. **OLT Panel**:

   - Editable: tx_power_dbm (range slider -10..+10 plus numeric input).
   - Shows number of dependent ONTs (count) and last recompute timestamp.

4. **ONT Panel – Optical Signal Analysis Section**:
   - Displays: OLT Transmit Power, Total Path Attenuation, Calculated Receive Power, Margin, Signal Status (color-coded chip).
   - Breakdown Table Columns: Order, Element Type, ID, Contribution (dB), Cumulative (dB).
   - Empty State: "No optical path found" (if path unresolved).
   - If override=up and signal would be NO_SIGNAL: warning banner.

- **Note:** The `deviceSignalUpdated` WebSocket payload is intentionally compact and does not include the segment-by-segment path breakdown. When the user opens this section, fetch details on demand via a dedicated endpoint (e.g., `GET /api/devices/{id}/optical-path`). WS keeps tiles live with summary fields (rx power, margin, status); detailed tables are REST-fetched to avoid bloating deltas.

### 9.5 Visualization Enhancements (Optional Early)

- ONT node color ring reflecting signal_status (OK/WARNING/CRITICAL/NO_SIGNAL).
- Hover on ONT shows small tooltip with RX power & margin.

### 9.6 Extensibility (Deferred)

- Multiple OLT path comparison view.
- Graph overlay heatmap of attenuation.
- Automatic suggestion of highest-margin path (if alternate topologies supported).

### 9.6.1 Additional viewer tabs (Deferred)

- Additional viewer tabs (IPAM Dashboard, Signal Monitor).
- Lasso selection.
- Bulk override operations.
- Sandbox diff view.

### 9.7 Bulk Device Creation (Implemented)

Implements TASK-015 core functionality (modal + positioning + undo). Accessibility focus management pending.

Workflow:

1. Right-click palette item → "Bulk Create…".
2. Modal fields: count (1..200), inferred device type, required POP or CORE_SITE parent (OLT/AON Switch), (future) name prefix.
3. Validation: ensures parent for OLT/AON Switch, valid count; aborts early on error.
4. Sequential POST /devices (best-effort; continue after individual failures) while generating clustered positions.
5. Summary toast with Undo action.
6. Undo: reverse-order DELETE of success set; follow-up toast if partial.

Position Algorithm (grid+jitter with spiral fallback):

```
grid = ceil(sqrt(N))
for i in 0..N-1:
r = floor(i / grid); c = i % grid
base = (anchor_x + c*dx, anchor_y + r*dy)
jitter = (rand()-0.5)*dx*0.25 per axis
pos = clamp_to_viewport(base + jitter)
if dense_region: apply small spiral offset (angle=i\*golden_angle, radius += k/N)
```

Testing: unit test for bounds & count; future E2E for create+undo cycle. Future enhancements: name templating, concurrency windowing, dry-run preview overlay, server-side atomic bulk endpoint, automated link wiring heuristics.

### 9.8 Container Link-Proxy UX (Implemented)

Containers (POP, CORE_SITE) are not valid link endpoints. When the user initiates link creation and clicks a container, the canvas intercepts the action and opens a lightweight selector modal listing eligible child devices inside that container (filtered by link rules). The user picks the intended internal device and the link endpoint is proxied to that device. This keeps container nodes as purely visual enclosures while preserving semantically correct link endpoints.

Key behaviors:

- Containers are excluded from hover hints and endpoint hit-testing for link creation; click on a container during link mode triggers the selector.
- The selector lists only devices allowed by `LINK_TYPE_RULES` for the current opposite endpoint; disabled items show a reason tooltip.
- On selection, the interactive rubber-band attaches to the chosen child device; cancel closes the modal and keeps link mode active.
- Error prevention: attempts to POST a link with a container id are rejected server-side with POP/CORE_SITE disallow rules.

### 9.9 Cockpit-to-Device Mapping (Renderer)

The topology renderer mounts SVG cockpits per device type (see `unoc-frontend-v2/src/composables/topologyCore/draw.ts`). Mapping is stable and tested:

- CORE_ROUTER, EDGE_ROUTER → RouterCockpit (Digital Display: STATUS, UPSTREAM, DOWNSTREAM, TOTAL CAPACITY)
- OLT → OLTCockpit (Digital Display + PON matrix)
- AON_SWITCH → AONSwitchCockpit (Digital Display + ACCESS matrix)
- ONT, BUSINESS_ONT → ONTCockpit (Digital Display: STATUS, RX POWER, UPSTREAM, DOWNSTREAM; tariff below)
- AON_CPE → AONCPECockpit (Digital Display: STATUS, UPSTREAM, DOWNSTREAM; tariff below; no RX POWER row)
- Passive inline (ODF, NVT, SPLITTER, HOP) → PassiveCockpit
- POP → POPCockpit (container metrics)
- CORE_SITE → CoreSiteCockpit (container metrics)

Physics & Containment: Child nodes are gently attracted toward slot anchors within their container, and an additional containment force prevents drift outside the bounds. Containers are rendered in a dedicated background layer, ensuring children and links remain visually above.

### 9.10 Link creation constraints & validation

Client-side guards are aligned with backend validation to avoid dead-end interactions:

- Containers (POP, CORE_SITE) are not valid endpoints (see §9.8). UI proxies selection to a child device; server rejects container endpoints.
- Management interfaces are not valid link endpoints. Back-end rejects when either endpoint name is `mgmt0` (see `backend/api/endpoints/links.py`).
- Endpoint combinations are validated against `LINK_TYPE_RULES` (see `02_provisioning_model.md` §3.12). Invalid pairs → `INVALID_LINK_TYPE` with details.
- Determinism: endpoint ordering for routed P2P is canonical (lexicographic by device id) to ensure stable /31 allocation when implemented.

Splitter-specific validation (server-enforced; surfaced as toasts):

- Attempting to attach a second ONT to the same SPLITTER OUT returns LINK_INVALID_UPSTREAM with detail like: "Splitter OUT '{out_if.name}' already serves an ONT; over-subscription is not allowed".
- If connecting another ONT would exceed the splitter's total OUT capacity, the server returns LINK_INVALID_UPSTREAM with: "Splitter capacity exhausted: {downstream_onts}/{ports_total} ONTs already connected".

Errors surfaced as non-blocking toasts with the server-provided error code and context.

### 9.12 Router TotCap rendering and capacity fields (API contract)

- Backend returns effective capacity for devices under two fields for forward/backward compatibility:
  - Nested: `parameters.capacity.effective_device_capacity_mbps`
  - Flattened: `parameters.effective_capacity_mbps`
- RouterCockpit reads one of these fields (prefers flattened if present) and displays a single line:
  - Label: `TotCap (Gbps):`
  - Value: `current / max` where:
    - `current` is the combined upstream + downstream throughput, rounded to an integer Gbps for readability.
    - `max` is the device's effective capacity, shown as an integer Gbps (or integer Mbps if < 1 Gbps).
- Rationale: concise integers prevent cockpit text overlap and keep the digital display clean while still conveying scale.

### 9.11 Link flow animation semantics

Traffic-bearing links animate a subtle dash flow to indicate utilization without implying directionality:

- Activation: a link is flagged for animation when utilization > 0 in the link metrics store; UI sets a `data-animate="1"` attribute on the SVG element.
- Speed: proportional to utilization with a floor, capped to avoid distraction. Current formula: `40 + min(utilization, 2) * 160` px/s.
- Dash length: derived from physical length via `computeDashForLength` so patterns remain consistent across scales.
- Pausing: animation loop is suspended when the tab is hidden to reduce CPU usage.

### 9.13 Congestion & Hysterese (summary)

This app surfaces congestion in a stable, flicker-free way by using hysteresis around utilization thresholds. Utilization is computed as `aggregated_bps / capacity_bps` per item.

- **Device/Link thresholds:**
  - Enter congestion when utilization ≥ 1.00 (100%).
  - Clear congestion when utilization ≤ 0.95 (95%).
- **GPON segment thresholds** (upstream aggregation groups):
  - Enter congestion when utilization ≥ 0.95 (95%).
  - **Clear congestion when utilization ≤ 0.85 (85%).**
- **Intent:** Creates a "sticky" warning state requiring significant utilization reduction to clear, encouraging users to address underlying issues rather than just briefly dipping below 100%.

Eventing and payloads (Phase 2 traffic engine):

- The traffic engine computes per-tick aggregates and publishes detected/cleared events for devices and links with payload fields including: `aggregated_bps`, `capacity_bps`, `utilization`, `overload_percentage`, and `tick`.
- Source of truth: backend/services/traffic/v2_engine.py (aggregation & thresholds) and backend/services/traffic/v2_congestion.py (event emission).

UI semantics:

- Cockpits reflect congestion state using stable badges/indicators that update only when thresholds are crossed (thanks to hysteresis), minimizing oscillation.
- GPON notes: capacities can be asymmetric (e.g., higher downstream than upstream). Aggregation and congestion checks are performed per-direction as provided by the traffic engine.

Cross-reference:

- See also §8 (Realtime events) for delta stream shapes and §9.12 for capacity display conventions.

## 10. Error Codes & Failure Semantics

### 10.1 Centralization

All standardized codes are defined in `backend/errors.py` via the `ErrorCode` enum and raised with the `raise_error` helper. This guarantees a single authoritative source and prevents drift between tests and implementation. To add a new code:

1. Add enum member.
2. (Optional) Map default HTTP status in `_DEFAULT_STATUS`.
3. Use `raise_error(ErrorCode.<NAME>, detail_suffix="context")` where contextual expansion is needed.

Current centrally managed set: `INVALID_PROVISION_PATH`, `ALREADY_PROVISIONED`, `POOL_EXHAUSTED`, `DUPLICATE_MGMT_INTERFACE`, `INVALID_LINK_TYPE`.

| Code                          | Meaning                                               | Typical HTTP        | Notes                                                                  |
| ----------------------------- | ----------------------------------------------------- | ------------------- | ---------------------------------------------------------------------- |
| POOL_EXHAUSTED                | No remaining addresses in pool                        | 409                 | Include pool_key                                                       |
| P2P_SUPERNET_EXHAUSTED        | No /31 left                                           | 409                 | Future when p2p dense                                                  |
| DUPLICATE_MGMT_INTERFACE      | Management iface already exists                       | 400                 | Provision idempotence violation                                        |
| DUPLICATE_LINK                | Link between endpoints already exists                 | 409                 | Consider returning existing id                                         |
| INVALID_PROVISION_PATH        | Context / dependency missing                          | 400                 | E.g. OLT without required upstream                                     |
| INVALID_LINK_TYPE             | Link type not permitted between endpoint device types | 400                 | Reference LINK_TYPE_RULES; include endpoint types & provided link_type |
| OVERRIDE_CONFLICT             | Override cannot be applied logically                  | 409                 | Logged; may still proceed partial                                      |
| ATTENUATION_PARAM_INVALID     | Optical attribute outside allowed range               | 400                 | Field + reason in payload                                              |
| FIBER_TYPE_INVALID            | Unknown fiber_type key                                | 400                 | Provide allowed list                                                   |
| SIGNAL_PATH_INCOMPLETE        | Cannot compute signal (missing segments)              | 200 (with sentinel) | Not an error for provisioning                                          |
| INVALID_DEBUG_INJECTION       | Negative or malformed injection parameters            | 400                 | See §15.19.12                                                          |
| DEBUG_INJECTION_LIMIT         | Injection value exceeds configured maximum            | 400                 | value > TRAFFIC_INJECTION_MAX_GBPS                                     |
| FEATURE_DISABLED              | Feature disabled by configuration                     | 403                 | e.g. injection when TRAFFIC_INJECTION_ENABLED=false                    |
| SANDBOX_LOAD_VERSION_MISMATCH | Sandbox file schema mismatch                          | 422                 | Future sandbox feature                                                 |

## 11. Determinism & Ordering Guarantees

- Device IDs (UUID) – allocation order preserved; IP assignment uses device.id lexical ordering for /31 pairing.
- Management IP sequence strictly monotonic within each pool.
- **Event emission order:** creation → status/signal → container change (if same tick) to ensure consumer stable layering.
- Sorting Key for stable bulk outputs: (device.type_priority, device.created_at, device.id).
- Path selection: minimize total_attenuation_db, tie → olt_id, tie → path_signature (concatenated ordered IDs) lexicographically.
- **Emission ordering within a tick:** linkUpdated/deviceOpticalUpdated → deviceSignalUpdated → deviceStatusUpdated.
