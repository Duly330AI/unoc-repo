---
title: ADR-011 – Upstream L3 Semantics, Passive Status Refactor & BFS Deprecation Path
status: Proposed
date: 2025-09-24
deciders: Architecture Guild, Backend, Frontend
reviewers: Ops, QA
---

# Context

Legacy dynamic device status combined multiple heuristics:

1. Provisioning flag (provisioned ? UP : DOWN for active types).
2. A breadth-first (BFS) reachability snapshot from anchor devices (e.g., backbone gateways) to infer pseudo "reachable" state for intermediate / passive elements.
3. Ad‑hoc optical signal gating for ONTs.

This produced false-positive UP states, notably:

- Routers marked UP despite missing a valid routed L3 path (default route / neighbor chain) to an anchor.
- Passive elements (ODF, SPLITTER, NVT, HOP) always optimistically UP even when structurally isolated or lacking a downstream terminator (ONT / AON_CPE / BUSINESS_ONT) or an upstream L3-capable chain.
- Traffic simulation (TrafficEngine v2) occasionally generating flows for leaves whose upstream L3 chain was broken.

# Problem Statement

We need authoritative, deterministic device status semantics that:

- Guarantee a device shown as UP has a valid, policy-compliant upstream pathway (L3 for routers/active, structural + downstream termination for passives).
- Prevent traffic generation for leaves lacking upstream L3 viability.
- Provide introspectable diagnostics (why a device is DOWN / DEGRADED) without guessing from side effects.
- Decouple status correctness from the legacy BFS snapshot to enable its retirement.

# Goals

- Strict L3 semantics for router classes (CORE_ROUTER, EDGE_ROUTER, BACKBONE_GATEWAY) – no UP without a traced routed path to an anchor.
- Unified upstream viability helper usable by any device type (returns chain + reason codes).
- Passive status logic that is structural (upstream + downstream) rather than BFS-derived optimism.
- Traffic gating: suppress leaf (ONT, BUSINESS_ONT, AON_CPE) generation when upstream L3 invalid.
- Deterministic, testable diagnostics (machine & human friendly) exposed in snapshots.
- Phased path to fully delete BFS reachability reliance.

# Non-Goals

- Full removal of BFS in this ADR (tracked as Phase 2 follow-up).
- Introducing advanced optical splitter tree modelling (covered by other ADRs if needed).
- Performance micro-optimizations (will be addressed post semantic stabilization).

# Decision

1. Implement a deterministic L3 path trace for routers (`trace_l3_path_to_anchor`):
   - Validates presence of management interface, VRF, default route or neighbor path, and disallows loops.
   - Produces ordered chain and granular failure reasons (e.g., `no_default_route`, `missing_neighbor_interface`).
2. Introduce `has_upstream_l3_or_anchor(device)` unified helper:
   - For routers: delegates to strict L3 trace.
   - For non-routers: walks upstream logical graph until anchor or router chain, collecting reason codes; returns success only if a valid chain terminating in an anchor or strict router path exists.
3. Revise passive device status evaluation:
   - Passive types (ODF, SPLITTER, NVT, HOP) are DOWN unless BOTH conditions hold:
     a. There exists an upstream chain culminating in an L3-capable device with valid upstream L3 (or direct anchor).
     b. There is at least one downstream terminator (ONT / BUSINESS_ONT / AON_CPE) reachable through passable links.
   - DEGRADED is reserved for internal evaluation errors (diagnostic safety net) to avoid silent false UP.
4. Maintain conservative ONT gating: ONTs go/stay DOWN when upstream L3 invalid beyond a simple missing_router_path (prevents premature UP during partial builds).
5. Gate TrafficEngine v2 leaf generation on `upstream_l3_ok` from diagnostics.
6. Persist diagnostics in status snapshot payloads: `upstream_l3_ok`, `chain`, `reason_codes` (enumerated, stable string identifiers).
7. Document and begin phased BFS deprecation: BFS no longer influences passives; remaining usage limited to a legacy degradation heuristic for some active, non-router devices (to be removed in Phase 2).

# Detailed Semantics by Device Class

| Class                                              | Status Requirements (absent admin override)                                                                  |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| ALWAYS_ONLINE (POP, CORE_SITE, BACKBONE_GATEWAY\*) | Always UP (gateway still must satisfy strict L3 for dependent routers, but itself presented as UP)           |
| CORE_ROUTER / EDGE_ROUTER                          | Provisioned AND strict L3 path trace success → UP; else DOWN (no DEGRADED masking)                           |
| OLT / AON_SWITCH                                   | Provisioned AND upstream L3 success (via helper) → UP; else DOWN (temporary DEGRADED only on internal error) |
| ONT / BUSINESS_ONT / AON_CPE                       | Provisioned, optical/signal OK, upstream L3 success → UP; no signal or upstream L3 failure → DOWN            |
| PASSIVE (ODF, SPLITTER, NVT, HOP)                  | Structural rule (upstream L3 chain + downstream terminator) satisfied → UP; else DOWN                        |

\*BACKBONE_GATEWAY functions as anchor; strict evaluation is used only for dependents, not to mark it DOWN.

# Diagnostics & Reason Codes

`reason_codes` (non-exhaustive, additive list – stable identifiers):

- `no_router_path` – Non-router has no upstream router/anchor chain yet.
- `routers_no_l3` – Upstream router chain exists but a router fails strict L3 requirements.
- `device_not_in_graph` – Device absent from traversal graph context.
- `exception` – Internal error during evaluation (system fault path).
- Router-specific granular reasons (examples): `no_default_route`, `no_mgmt_interface`, `missing_next_hop`, `loop_detected`.

Semantics:

- `upstream_l3_ok=false` + presence of one or more failure codes → device must not be UP (except ALWAYS_ONLINE anchors) — enforced by status logic.
- Passive structural failures will surface using existing codes; passive-specific differentiation (e.g., `no_downstream_terminator`) planned for Phase 2.

# Migration & Rollout (Phased)

Phase 1 (DONE in code – this ADR):

- Strict router L3.
- Unified helper + diagnostics.
- Traffic leaf gating.
- Passive structural status logic.
- ONT conservative gating.

Phase 2 (Planned):

- Remove residual BFS degradation logic for active non-router devices.
- Introduce passive-specific reason codes (`no_downstream_terminator`, `no_upstream_chain`).
- Event schema version bump documenting BFS field removals.
- Performance tuning / caching of upstream helper.

Phase 3 (Planned):

- Expanded observability: counters for reason code occurrences, latency histograms for evaluation.
- UI surfacing of diagnostic chain & reason tooltips.
- Optional: partial-liveness / `DEGRADED` nuanced states once correctness guarantees established.

# Alternatives Considered

1. Retain BFS as a secondary soft signal while adding strict L3.
   - Rejected: perpetuates ambiguity; operators misinterpret UP as fully viable.
2. Precompute per-tick full graph annotated with L3 viability.
   - Deferred: complexity + premature optimization; current on-demand evaluation is performant enough for present scale.
3. Introduce separate PASSIVE_INTERCONNECT status tier.
   - Rejected: adds enum complexity without immediate user value.

# Risks & Mitigations

| Risk                                                | Impact                   | Mitigation                                                     |
| --------------------------------------------------- | ------------------------ | -------------------------------------------------------------- |
| Increased DOWN states during partial builds         | Perceived instability    | Diagnostics explain cause; docs guide expected transitions     |
| Performance regression (multiple helper traversals) | Higher recompute latency | Monitor; introduce caching Phase 2                             |
| UI not yet surfacing diagnostics → confusion        | Support burden           | Fast-follow frontend ticket to expose upstream_l3_ok & reasons |
| Anchor misclassification causing cascaded DOWN      | Broad false negatives    | Type-based anchor list centralized & unit tested               |

# Test Strategy

- Unit/Integration tests added:
  - Strict router L3 failure classification (`test_status_upstream_l3_failures.py`).
  - Optical vs L3 differentiation (`test_status_partial_optical_vs_l3.py`).
  - Traffic gating on upstream L3 (`test_traffic_gating_upstream_l3.py`).
  - Passive structural transitions (`test_passive_status_logic.py`).
- Regression: existing provisioning, optical recompute, WS fanout tests remain green.
- Future: add performance benchmarks post Phase 2.

# Observability / Metrics (Forward Looking)

Proposed counters (Phase 3): `status_evaluations_total{result=}`, `upstream_l3_failures_total{reason_code=}`, gauge for `devices_up_without_diagnostics` (should stay 0), evaluation duration histogram.

# Decision Status

Proposed – implementation already in place; seeking formal acceptance to proceed with Phase 2 (BFS removal) tasks.

# Follow-ups / Action Items

- Phase 2 ticket: Remove BFS dependency & add passive reason codes.
- Frontend: surface diagnostic chain & upstream_l3_ok state.
- Metrics: implement counters & histogram instrumentation (Phase 3).
- Docs: update `03_ipam_and_status.md` §5.1 (this ADR cross-linked) – (in progress).
