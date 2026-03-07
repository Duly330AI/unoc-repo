---
title: ADR-010 – ODF-as-Aggregator GPON Topology & Capacity Model
status: Proposed
date: 2025-09-20
deciders: Architecture Guild, Backend, Frontend
reviewers: Ops, QA
---

# Context

Our current link rules are permissive and model direct OLT↔ONT links, which does not reflect real GPON constraints and complicates capacity/congestion modelling. The legacy project used a pragmatic abstraction: treat ODF (Optical Distribution Frame) as the logical aggregation point for a single PON port. All ONTs connected “through” an ODF share the same OLT PON-port capacity and occupancy budget.

Key real-world considerations we want to emulate:

- ONT never connects directly to an OLT PON port; passive plant sits in between.
- Each PON port has asymmetric capacity (e.g., GPON 2.5G/1.25G, XGS-PON 10G/10G).
- ONTs sharing a PON port compete for the same capacity; congestion should degrade the segment, not unrelated segments.

# Decision

Adopt the “ODF-as-Aggregator” GPON model:

- Disallow direct OLT↔ONT links (backend validation + frontend guidance).
- Enforce that an OLT PON port connects upstream-only to exactly one ODF (1:1 by default).
- Enforce that an ONT uplink connects upstream-only to exactly one ODF.
- Treat each OLT PON-port ↔ ODF pair as a PON Segment. All ONTs attached to that ODF share the segment capacity and occupancy.
- Surface occupancy (e.g., 10/64), aggregate throughput (up/down), congestion flag with hysteresis, and headroom on the segment (ODF) and propagate status to member ONTs.

# Consequences

Positive:

- Realistic-enough modelling of GPON without complex splitter trees.
- Clear capacity aggregation boundary → simpler TrafficEngine logic and UI.
- Deterministic validation rules simplify UX and API usage.

Trade-offs:

- ODF doubles as “logical splitter.” It’s an abstraction; not every passive element is modelled.
- Default 1:1 PON↔ODF simplifies capacity reasoning; advanced deployments (one PON feeding multiple ODFs) are deferred to a future phase.

Out of Scope (for this ADR; may be later ADRs):

- Physical splitter hierarchy modelling (1:2, 1:4, … cascades).
- DBA profiles and QoS classes for ONT flows.
- Multi-ODF-per-PON as a first-class feature (can be phased in later).

# Scope (Phased)

Phase 1 – Topology & Link Rules

- Backend validation rules preventing OLT↔ONT and guiding OLT PON↔ODF, ONT↔ODF only.
- Frontend link creation enforcing/auto-selecting valid targets and ports.
- API errors are explicit and consistent (typed error codes, messages).

Phase 2 – Aggregation, Shaping, Status, Telemetry

- Aggregate ONT demands per PON Segment (ODF), separately for downstream and upstream.
- Apply segment capacity caps (from OLT PON port profile: GPON, XG-PON, XGS-PON, etc.).
- Implement simple fair share in congestion: min(ONT demand, remaining_share), with hysteresis to prevent flapping.
- Propagate segment congestion to ODF and to ONTs as CONGESTED (or DEGRADED), not DOWN.
- Export metrics (occupancy, capacity, demand, used throughput, headroom, congestion flag) and emit events on threshold crossings.

# Architecture Notes

- Source of truth for capacities lives in port capabilities (catalog). The segment inherits from the OLT PON-port.
- Segment identity = (OLT PON-port ID, ODF ID). Operationally, we will attach metrics to the ODF entity for simplicity, and reference the OLT PON-port in metadata.
- Validation lives server-side (backend) and is mirrored client-side for UX. Backend is authoritative.
- Existing coalesced recompute and TrafficEngine v2 carry the load; we add a segment aggregator layer over ODF membership.

# Alternatives Considered

1. Introduce a new PON_SEGMENT node instead of using ODF as aggregator.

   - Pros: Semantically pure separation of concerns.
   - Cons: More UI and data model churn; ODF is the operator-facing patchpoint and best UX anchor. Rejected for now.

2. Model splitter trees (1:N cascades).
   - Pros: High fidelity.
   - Cons: Complex for little additional operational value in our app’s scope. Rejected for now.

# Rollout & Migration

- Validation can be introduced behind a feature flag and then turned on by default.
- Migration script (optional): For any existing OLT↔ONT direct link, create an ODF per PON-port, rewire ONTs via the new ODF, then remove invalid direct links.
- Frontend gating: update link modal filters and preselection; show actionable validation errors.

# Test Strategy (high level)

- Unit/API: invalid pairs (OLT↔ONT, ONT↔ONT, ODF↔ODF upstream), valid triplets (OLT→ODF→ONT), occupancy updates, and single-upstream constraints.
- Engine: throughput aggregation, capacity cap, fairness, congestion hysteresis, status propagation.
- E2E/UI: link creation guidance, occupancy display (x/64), congestion badge, metrics snapshot correctness.

# Decision Status

Proposed. Pending sign-off from Architecture Guild and stakeholders. Upon acceptance, implement Phase 1 then Phase 2 as per acceptance criteria document.
