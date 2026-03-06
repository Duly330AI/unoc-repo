# Container Model & UI (POP, CORE_SITE)

Spec Revision: r9.6 — 2025‑09‑21

This document consolidates the container feature: what containers are, which rules apply (parent/child, linking), and how the UI behaves (cockpits, slots, drag‑and‑snap, link proxy).

Related docs for deeper context:

- Provisioning rules and device classes: 02_provisioning_model.md
- IPAM pools and status semantics: 03_ipam_and_status.md
- Realtime events and UI interactions: 05_realtime_and_ui_model.md
- Traffic Engine and congestion: 11_traffic_engine_and_congestion.md
- Canonical pathfinding notes: 06_future_extensions_and_catalog.md

---

## At a glance

- Containers visually group devices. Supported types: POP, CORE_SITE.
- Containers cannot be link endpoints; a link to a container prompts you to pick an internal device (proxy). Backend enforces this with error code POP_LINK_DISALLOWED when a container is used as an endpoint.
- OLT and AON_SWITCH may be top-level or inside a POP; if a parent is provided, it must be POP. Containers themselves have no parent.
- Drag near slot anchors to snap. A gentle containment force keeps children within bounds.
- Realtime event on re-parent: deviceContainerChanged with nullable parent_container_id.

Success criteria

- Valid parent/child relationships are enforced server-side and reflected in the UI.
- Linking via container uses a real internal device as endpoint.
- Metrics in container cockpits summarize occupancy/health without altering network semantics.

---

## 1. Concept and Scope

- Container devices visually group other devices and provide a dedicated cockpit UI. Currently supported container types:
  - POP
  - CORE_SITE (new; r9.4)
- Containers are purely organizational/visual constructs:
  - They do not act as link endpoints.
  - They contribute no L2/L3 semantics on their own (no bridging/routing).
  - They expose metrics and occupancy to aid navigation and capacity planning.

Implementation notes:

- Containers have regular device identity/IDs, and devices reference their parent via `parent_container_id`.
- The authoritative parent rules live in backend provisioning constants (see 02_provisioning_model.md).

---

## 2. Parent/Child Rules (Authoritative in Backend)

- Containers (POP, CORE_SITE)
  - Cannot have a parent (i.e., `parent_container_id` must be null).
  - Can contain other devices.
- OLT and AON_SWITCH
  - Parent is optional. If provided, it must be of type POP (see `backend/utils.py::validate_parent_child`).
  - They can exist at top level (without container) and still be provisionable.
- ONT family and AON_CPE
  - Cannot be parents of any device (i.e., must not have children).
- Other devices
  - Default: may be top‑level or be contained where allowed by the provisioning matrix.

Validation happens server‑side. The UI reflects validation errors consistently (see 05_realtime_and_ui_model.md#error-codes--failure-semantics).

---

## 3. UI: Cockpits, Slots, Drag‑and‑Snap

- Container Cockpits
  - Show occupancy (child count vs. configured capacity, if any).
  - Surface aggregate traffic/health indicators for quick scanning.
  - Provide quick navigation to contained devices.
- Slot Anchors and Snapping
  - Containers render slot anchors for common child types (e.g., OLT, AON_SWITCH).
  - Dragging a compatible device near a slot gently snaps and highlights a valid drop target.
  - Invalid targets are visually rejected before the drop.
- Drag and Drop
  - Moving a device into/out of a container updates `parent_container_id`.
  - Bulk create flows require providing a valid parent container where mandated (e.g., OLT/AON_SWITCH → POP/CORE_SITE).
- Containment Physics
  - A gentle containment force keeps children within container bounds while allowing natural physics.
  - No rigid group translation; the container frame moves while children maintain their coordinates
  - Children are gently pulled toward slots by the containment force
  - Pinned nodes (with fx/fy set) maintain their fixed coordinates and are only clamped at container edges if necessary

See 05_realtime_and_ui_model.md for general interaction semantics and animation cues.

---

## 4. Linking: Container Link Proxy UX

- Containers cannot be selected as link endpoints.
- When a container is targeted during link creation, a modal prompts to choose an internal device that qualifies as the endpoint.
- The chosen internal device becomes the actual endpoint; the UI displays that mapping clearly to avoid confusion.
- This prevents accidental links to containers and ensures link rules are evaluated against real devices.
  - If a container has no valid internal devices for the attempted link, the UI shows a toast ("No valid targets in container") and resets the link tool without opening an empty selection modal.

Cross‑refs:

- Provisioning and link validity: 02_provisioning_model.md
- Realtime events during link creation: 05_realtime_and_ui_model.md

---

## 5. Events and Realtime Updates

- Device container change

  - Event reflects `parent_container_id` updates (nullable; null when moved to top level).
  - Ordering is deterministic alongside other mutations (see 05_realtime_and_ui_model.md).
  - Example payload:

    {
    "id": "dev_123",
    "parent_container_id": "cont_456"
    }

    Unassign (to top level):

    {
    "id": "dev_123",
    "parent_container_id": null
    }

- Link creation with proxy selection
  - Emits standard link create/update events for the underlying device endpoints.
  - No special container event is emitted for link proxying itself.

---

## 6. Metrics and Health in Containers

- **Container cockpits aggregate child states deterministically**:
  - If any child is DOWN → Container shows DOWN
  - Else, if any child is DEGRADED → Container shows DEGRADED
  - Else → UP
- Example: 9×UP and 1×DEGRADED → Overall status = DEGRADED
- Source: `unoc-frontend-v2/src/components/cockpits/containers/POPCockpit.vue` and `CoreSiteCockpit.vue`, computed `healthLevel` (DOWN before DEGRADED before UP) and summation of "Total Traffic" from child metrics.
- Container cockpits summarize metrics sourced from the metrics store (e.g., occupancy, traffic bands, health flags).
- These are aggregations/roll‑ups for quick situational awareness; underlying device metrics remain the source of truth.

See 11_traffic_engine_and_congestion.md for live device/link metrics and congestion, and 06_future_extensions_and_catalog.md for broader simulation roadmap.

---

## 7. Pathfinding and Status Considerations

- Pathfinding operates on real devices and links only; container membership is not part of the graph. See `backend/services/pathfinding.py`:
  - `PathfindingStore.bump_version()` invalidates graphs on topology mutations.
  - `build_logical_graph(...)` and `build_optical_graph(...)` add nodes/edges by device type and classified link kind; containers are excluded from both projections.
- Status and passability are evaluated per entity, independent of containers:
  - Device status: `backend/services/status_service.py::evaluate_device_status` (admin override precedence; ACTIVE/PASSIVE/ALWAYS_ONLINE rules; ONT optical NO_SIGNAL gating).
  - Link passability and effective status: `backend/services/status_service.py::{is_link_passable,evaluate_link_status}` (admin overrides on link and endpoints, logical UP requirement).
- Optical signal budget is computed per ONT path irrespective of containers:
  - `backend/services/optical_service.py::recompute_optical_paths_for_affected_onts` resolves optical paths and updates per‑ONT `signal_*` fields; events `device.optical.updated` emitted.

References:

- Pathfinding: 06_future_extensions_and_catalog.md
- Status & passability: 03_ipam_and_status.md
- Signal budget: 04_signal_budget_and_overrides.md
- Decision rationale: adr/ADR-008-containers-link-rendering.md

---

## 8. Seeding, Palette, and Defaults

- CORE_SITE is seeded in the backend catalog and appears in the frontend palette alongside POP.
- Default container cockpits ship with sensible slot layouts for common device mixes.
- The palette entry ensures quick creation and consistent default styling.

---

## 9. Edge Cases and Limitations

- Containers are not valid link endpoints by design.
- Invalid parent assignments (e.g., container within container, ONT as parent) are rejected server‑side.
- Slot layouts are UX hints; final acceptance is governed by backend validation.
- Deferred items (tracked in roadmap):
  - Per‑container capacity planning (hard limits and scheduling).
  - Advanced physics (stable incremental layout beyond containment).

---

## 10. API Surface (Summary)

- Device field: `parent_container_id` (nullable UUID/ID)
- Events: `deviceContainerChanged` (payload contains `id`, `parent_container_id`)
- No special link API for containers; proxying is a UI concern resolved to real devices. Attempting to link directly to a container returns a validation error (POP_LINK_DISALLOWED) that the UI converts into the proxy selection flow.

For event formats and error semantics, see 05_realtime_and_ui_model.md.

---

## 11. Contracts and Constraints (quick reference)

- Inputs
  - Drag/drop assignment: device id, target container id (or null to unassign)
  - Link creation via container: selected container id, chosen internal device id
- Outputs
  - Events: deviceContainerChanged for parent changes; standard link events for link ops
  - UI state: cockpit occupancy/metrics update; selection/context panels refresh
- Error modes
  - Invalid parent type → validation error (UI toast + no change)
  - **Linking directly to container → proxy selection modal; if no valid targets exist, a toast appears "No valid targets in container" and the tool resets**
  - Stale container/device ids → 404; no state change
- Invariants
  - Containers have no parent
  - Containers are never link endpoints
  - Backend rules are authoritative; UI hints (slots) must not override validation

---

## 12. Splitter V1: capacity and UI badges

- Scope: Applies to passive device type SPLITTER. Defaults: 1 IN + 32 OUT (split ratio 1:32).
- Capacity rules (enforced by backend link validation):
  - At most one ONT per OUT port (no over-subscription on a single OUT).
  - Total downstream ONTs must not exceed OUT port count (e.g., 32 for default splitter).
- UI surfaces:
  - PassiveCockpit shows a badge "[used/total]" where used = OUT ports currently serving any ONT; total = OUT port count.
  - Details Panel → Overview repeats the same badge for SPLITTER devices.
- API exposure: For SPLITTER devices, DeviceOut.parameters.splitter contains { ports_total, ports_used, downstream_onts } for rendering and audits. See 13. REST API Reference.
