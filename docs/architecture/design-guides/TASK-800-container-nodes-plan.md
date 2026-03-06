# TASK00: Hierarchical Container Nodes (POP & CORE_SITE) with Snap Logic

Status: Proposal (awaiting approval)
Owner: Frontend + Backend squads (shared)
Priority: High
Milestone: M9  Foundational Network Emulation

## Vision

Replace dashed parentchild lines with real nested container nodes. POP and CORE_SITE become firstclass containers that host child devices (OLT, AON_SWITCH, EDGE_ROUTER, CORE_ROUTER, BACKBONE_GATEWAY) with:

- Slotbased snapping (anchor points, not fixed boxes)
- Physics boundaries to keep children inside
- Aggregate metrics and occupancy indicators (e.g., Slots: 4/6)
- Flexible linking (direct and containerproxy) without sacrificing technical correctness

This is a platform change: containers become supercockpits with layout rules, while existing device cockpits remain as children.

---

## Architecture decisions (confirmed)

- Containment rules
  - CORE_SITE holds BACKBONE_GATEWAY, CORE_ROUTER, EDGE_ROUTER (edge can be here in collapsed designs)
  - POP holds AON_SWITCH, OLT, EDGE_ROUTER (edge often lives here)
  - Flexible: Edge may be in POP or CORE_SITE.
- Snap design: Slots are anchor points (coordinates) defined by the container model. Child cockpits keep their size. Container spacing ensures no overlap.
- Linking: Always draw links between the actual device interfaces (Option B). Provide a userflow for containerproxy selection but persist and render the real endpoints.
- Optional POP/CORE usage: UI organization feature, not a hard backend dependency. Devices may exist uncontained for labs/debugging.
- Status/metrics: Container shows aggregates (occupancy, sum bps, health badge computed from children).

---

## Data model (Backend)

- DeviceType: add `CORE_SITE` (passive_container role like POP)
- Device fields unchanged; `parent_container_id` remains the single source of truth for nesting.
- New tables: none initially. Slots defined via JSON schema in FE catalogue; server can optionally expose presets later.
- Validation (soft):
  - Provide validation helpers (not hard errors at creation unless feature flag enabled).
  - Expose a lint endpoint: `GET /api/containers/validate` returning warnings for invalid placements.
- Propagation & status: Unchanged logic; containers are conduits only for reachability. (POP/CORE_SITE are ALWAYS_ONLINE containers.)

---

## APIs (Phaseable)

1. Read

- `GET /api/devices?type in [POP, CORE_SITE]` (existing)
- `GET /api/devices/{id}` returns `children: string[]` computed serverside (optional convenience)

2. Write

- `PATCH /api/devices/{id}`: set/unset `parent_container_id`
- Optional (future): `POST /api/containers/{id}/slots/layout` to upload custom slot layouts (JSON)

3. Validation/Lint (optional)

- `GET /api/containers/validate`  list of {device_id, issue, severity}

---

## Frontend model & state

- Add container descriptors (catalog):
  - POP: default slot count, slot anchor coordinates (relative to container center), allowed child types
  - CORE_SITE: same idea, different layout/padding
- Stores:
  - devicesStore: add fast selectors: childrenOf(containerId), isContainer(device), allowedTypes(containerType)
  - layoutStore: track percontainer layout frame (x,y,w,h), computed from slot anchors and margin

---

## Rendering & Interaction

- New components
  - `POPCockpit.vue` (container supercockpit)
  - `CoreSiteCockpit.vue`
- Nested rendering (draw.ts)
  - Render containers first  zorder behind children
  - Child device coordinates = container.origin + slotAnchor + jitter(0) (no animation at snap time)
  - Keep existing device cockpits intact
- Physics
  - Custom force keeps children within container bounds (clamp + mild spring to slot center)
  - Drag rules
    - Drag over container  highlight valid slots
    - Drop on valid slot  PATCH parent_container_id; place device at slot center
    - Invalid drop  revert to original position
    - Drag out of container  parent_container_id = null (if allowed)
- Snap logic
  - Slots are points; no size normalization of child cockpits necessary
  - Minimum spacing in slot layout accounts for largest cockpit footprint

---

## Linking UX

- Direct link (current behavior): device A  device B, port to port
- Containerproxy link (new)
  - Flow: select leaf (e.g., CPE)  click container (POP)  modal lists compatible targets inside (e.g., AON_SWITCH ports)  user picks one  link created devicetodevice (keeps real endpoints)
  - Validation uses existing link rules
- Rendering
  - Always draw lines between real endpoints (may visually cross container border)
  - Optional cosmetics: show a faint tunnel marker on container border when a link crosses

---

## Phasing and Tasks

### Phase 0  Design artifacts and guards

- Write slot layout presets (JSON) for POP and CORE_SITE
- Containers are permanently enabled (no feature flag). Keep `CONTAINER_PROXY_LINKING` as a UX flag.
- Update docs and ADR entry

Deliverables

- `docs/container-layouts.json` with example slot anchors
- ADR: rationale, tradeoffs (truthful links vs hubandspoke drawing)

Acceptance

- Maintainers sign off on layouts and UX flows

---

### Phase 1  Backend enablement (minimal)

- DeviceType: add `CORE_SITE`
- API: nothing new mandatory; reuse `PATCH /devices/{id}` for `parent_container_id`
- Validation helper (optional, nonblocking): `/api/containers/validate`

Tasks

- Extend enum + derive_role() to mark CORE_SITE as ALWAYS_ONLINE
- Add test: creating CORE_SITE & assigning children
- Add test: moving device in/out of containers via PATCH

Acceptance

- Unit tests: pass
- No breaking changes to existing endpoints

---

### Phase 2  Frontend containers & snapping

- Render containers (POPCockpit/CoreSiteCockpit) with border, title, occupancy metric
- Draw children inside bounds using their slot anchors
- Dragover highlight; Snap on drop; PATCH parent_container_id; redraw
- Remove dashed parentchild lines

Tasks

- Add `isContainer` flag in palette and renderer switch
- New components for containers
- Slot highlighter overlay and hittesting
- Snap controller (keyboard cancel, ESC)
- Update stores: childrenOf(), moveDeviceToContainer(), removeFromContainer()
- Tests: drop valid/invalid, snap to nearest, undo to previous position

Acceptance

- A device can be snapped into/out of POP/CORE_SITE reliably
- Children stay inside bounds during regular simulation

---

### Phase 3  Physics boundaries

- Implement a custom force (D3) to nudge children toward slot center
- Clamp children to container padding on every tick
- Respect manual user placements (dont fight user when stationary)

Tasks

- Force module: containerBoundsForce.ts
- Integrate with simulation lifecycle
- Tests: large containers with many children remain stable

Acceptance

- Children dont escape containers; layout is stable under movement

---

### Phase 4  Containerproxy linking

- Add modal flow to pick a target inside a container when clicking the container as the second step of link creation
- Filter list by compatibility (based on existing link rules)
- Create real link endpoints; emit events; redraw

Tasks

- Add `LinkProxyModal.vue`
- Extend link tool: if target is container  open modal with compatible inner devices
- Validate on create; error UI for invalid choices

Acceptance

- User can link CPE  POP  AON_SWITCH without hunting pixels; result is a real devicetodevice link

---

### Phase 5  Aggregates and metrics

- Container shows: Slots used/total; aggregate device bps (sum), min/max health of children
- Hover tooltip: breakdown per type (e.g., 2 OLT, 4 AON_SWITCH)

Tasks

- Selector for children metrics aggregation
- UI badges in container cockpits
- Tests: aggregation correctness with updates

Acceptance

- Aggregates update live with children metrics and statuses

---

### Phase 6  Optional strict validation mode

- Toggle to enforce containment rules on write (400 on invalid parent assignment)
- Lint endpoint returns actionable errors

Acceptance

- Strict mode blocks invalid placements
- Lint lists all issues when strict mode off

---

### Phase 7  Polish & docs

- Keyboard shortcuts: hold Alt to bypass snap; Shift to multiselect; Delete to clear slot
- Context menu on container: Clear slot #, Auto layout children, Resize container
- Docs & examples; demo presets (6 slot POP, 20 slot POP)

Acceptance

- Demo scenario reproducible; handbook updated

---

## Risks & mitigations

- Overlap of large cockpits: mitigate by generous slot spacing; allow percontainer layout presets
- Performance with many children: batch DOM updates; use layers; throttle physics
- Confusion about link rendering: clarify in docs; add subtle border markers when crossing
- Backward compatibility: optional containers; no mandatory containment

---

## Acceptance criteria (E2E)

- User can create POP/CORE_SITE, snap devices into slots, remove them, and everything stays inside
- Links render between true endpoints; proxy flow works and creates correct links
- Container aggregates reflect live metrics and occupancy
- All unit/integration tests pass in CI

---

## Rollout plan

- Feature flags default off in prod; on in dev
- Merge phases incrementally; keep PRs small (13 files where possible)
- Migration not required; existing topologies continue to work

---

## Appendix: Slot layout JSON (example)

```json
{
  "POP": {
    "padding": 24,
    "slots": [
      { "id": "slot_1", "x": 120, "y": -80, "allow": ["AON_SWITCH", "EDGE_ROUTER"] },
      { "id": "slot_2", "x": 120, "y": 0, "allow": ["AON_SWITCH", "OLT", "EDGE_ROUTER"] },
      { "id": "slot_3", "x": 120, "y": 80, "allow": ["AON_SWITCH", "OLT", "EDGE_ROUTER"] },
      { "id": "slot_4", "x": -120, "y": -60, "allow": ["OLT"] },
      { "id": "slot_5", "x": -120, "y": 60, "allow": ["OLT", "EDGE_ROUTER"] }
    ]
  },
  "CORE_SITE": {
    "padding": 32,
    "slots": [
      { "id": "core_1", "x": 0, "y": -60, "allow": ["BACKBONE_GATEWAY"] },
      { "id": "core_2", "x": -120, "y": 40, "allow": ["CORE_ROUTER", "EDGE_ROUTER"] },
      { "id": "core_3", "x": 120, "y": 40, "allow": ["CORE_ROUTER", "EDGE_ROUTER"] }
    ]
  }
}
```

Notes: Coordinates are relative to container center; spacing must accommodate largest child cockpit.
