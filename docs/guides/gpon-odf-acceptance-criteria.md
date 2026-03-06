# GPON ODF-as-Aggregator – Acceptance Criteria (Phase 1 & 2)

Last updated: 2025-09-20
Status: Draft for Review
Owners: Backend, Frontend, QA
Related: ADR-010 – ODF-as-Aggregator GPON

## Phase 1 – Topology & Link Rules

Goal: Enforce realistic GPON pairing by treating ODF as the mandatory aggregation point between OLT PON ports and ONTs. Prevent invalid links and guide users in the UI.

### Functional Requirements

- Disallow direct OLT↔ONT links (HTTP 400 with specific error code, e.g., LINK_INVALID_PAIRING).
- OLT PON-port can connect upstream-only to exactly one ODF (default 1:1). Attempts to connect to non-ODF targets are rejected.
- ONT can connect upstream-only to exactly one ODF. Attempts to connect to OLT or any non-ODF node are rejected.
- ODF has exactly one upstream link to a single OLT PON-port. Multiple upstreams are rejected.
- ONT has exactly one upstream link (to an ODF). Multiple upstreams are rejected.
- Existing general link validations remain intact (no self-links, interface type compatibility, etc.).

### Error Handling & Messages

- Provide deterministic error codes/messages:
  - LINK_INVALID_PAIRING: “Direct OLT↔ONT links are not allowed. Connect via an ODF.”
  - LINK_INVALID_UPSTREAM: “ODF must connect upstream to an OLT PON-port, not {actual}.”
  - LINK_MULTIPLE_UPSTREAMS: “{device} already has an upstream link. Only one upstream is allowed.”
- Errors include offending device IDs and interface IDs for debuggability.

### Frontend UX Requirements

- Link creation modal enforces allowed targets:
  - From OLT: filter targets to ODFs; preselect PON ports as source.
  - From ONT: filter targets to ODFs; preselect ONT uplink interface.
- If a forbidden pairing is attempted (e.g., via API or deep link), surface backend error and keep the modal state for quick correction.
- Topology view visually shows OLT→ODF→ONT flow (no direct OLT↔ONT edges).

### Observability

- Emit a domain event on link-create rejection with reason (debug level) for audit in dev.
- Perf log records validation time (already available via SQL/req timers).

### Test Plan (Phase 1)

- Backend unit/API tests:
  - Creating OLT↔ONT link returns 400 LINK_INVALID_PAIRING.
  - OLT↔ODF accepted; ONT↔ODF accepted.
  - ODF upstream linked to non-PON port rejected.
  - Multiple upstreams for ODF rejected; multiple upstreams for ONT rejected.
- Frontend unit/e2e:
  - Link modal filters options correctly from OLT and ONT contexts.
  - Attempted OLT↔ONT creation blocked and shows correct error.

Acceptance: All tests pass; UI/UX validated manually on demo topology.

---

## Phase 2 – Aggregation, Shaping, Status, Telemetry

Goal: Aggregate ONT demand per PON Segment (OLT PON-port ↔ ODF), apply capacity models, shape under congestion, and reflect segment status and metrics in UI/API.

### Functional Requirements

- Segment identity: (OLT PON-port ID, ODF ID); metrics are attached to ODF and reference the PON-port.
- Capacity model per PON-port (catalog-based):
  - GPON: 2.5 Gbps downstream / 1.25 Gbps upstream by default.
  - XG-PON, XGS-PON supported via capabilities.
- Demand aggregation:
  - Sum ONT downstream and upstream demand separately per segment.
  - Update on ONT attach/detach, topology changes, tariff updates, periodic ticks.
- Shaping / Fairness under congestion:
  - If aggregate demand > capacity, distribute fair share across ONTs (simple equal share).
  - Optional future: weights/profiles; not required for acceptance.
  - Apply hysteresis thresholds to set/clear congestion to avoid flapping (e.g., enter at >95%, clear at <85%).
- Status propagation:
  - Segment status becomes CONGESTED when in shaping; otherwise UP (unless other faults apply).
  - ONTs in congested segment get DEGRADED or CONGESTED badge without being DOWN.
  - Independent segments (other PON ports) unaffected.
- Occupancy and headroom:
  - Maintain subscriber count N and maximum allowed (e.g., 64) → display N/64.
  - Compute headroom = capacity - used (per direction).

### API & UI Requirements

- Metrics snapshot includes, per ODF segment:
  - subscribers_count, subscribers_max
  - capacity_down/up, demand_down/up, used_down/up
  - congested (bool), headroom_down/up
  - reference to olt_id, pon_port_id
- UI displays on ODF card and ONTs:
  - Occupancy (N/64), capacity, segment total throughput, congestion badge, headroom bars.
- Events:
  - Emit events on segment congestion state changes (enter/exit), ONT attach/detach, occupancy threshold crossings (e.g., 80%, 100%).

### Observability & Profiling

- SQL black-box timings continue to log segment computations.
- Optional Prometheus counters/gauges for segment metrics.
- pyinstrument/py-spy profiling illustrates segment aggregation cost on demo topology.

### Test Plan (Phase 2)

- Engine/Unit tests:
  - Aggregate demand across multiple ONTs on same ODF; shaping kicks in when > capacity.
  - Congestion hysteresis behaves as expected (no flapping around threshold).
  - Independent ODF on another PON-port unaffected under high load on first segment.
- API tests:
  - Metrics snapshot returns expected fields and consistent totals.
  - Status endpoints show CONGESTED/DEGRADED as specified.
- UI tests:
  - ODF/ONT tiles reflect occupancy, throughput, congestion state, and headroom.

Acceptance: All tests green; performance acceptable on demo topology; profiling shows negligible overhead compared to baseline.

---

## Non-Goals (for this release)

- Modelling physical splitter cascades.
- DBA/QoS profiles per ONT.
- Multi-ODF-per-PON default support (may be added via config in later iteration).

## Rollout & Migration

- Behind a feature flag; migrate any existing invalid OLT↔ONT links by inserting ODF and re-wiring ONTs.
- Provide a CLI script to audit and auto-fix demo data.

## Risks & Mitigations

- Risk: Hidden direct links in existing data → Mitigation: migration script and strict validation.
- Risk: UI confusion around new constraints → Mitigation: guided modals and clear error copy.
- Risk: Performance regression under large subscriber counts → Mitigation: coalesced recompute, simple fair share, and targeted profiling.

## Sign-off Checklist

- [ ] ADR-010 accepted
- [ ] Backend validations implemented and tested
- [ ] Segment aggregation, shaping, and status implemented and tested
- [ ] Metrics exposed in snapshot and rendered in UI
- [ ] Migration script executed on demo data
- [ ] Documentation updated (user guide, troubleshooting)
