# Active Backlog (curated from early roadmap)

This backlog captures a few valuable items from the early task ledger. All other items have been archived in `./COMPLETED_TASKS.md`.

## 🧪 Epic — Implement Interactive Network Emulation (TASK-300…303)

- Summary: Take the platform beyond static emulation by adding interactive, command-driven diagnostics and progressive protocol simulation.
- Priority: High (after current stabilization/UI work)
- Milestone target: M10+
- Scope (initial milestones)
  - TASK-300 Emulated Diagnostics Layer: ping, traceroute via pathfinding/TTL heuristics; deterministic outputs.
  - TASK-301 Frontend: Interactive Terminal Viewer: UI terminal component to invoke diagnostics and stream structured results.
  - TASK-302 Advanced Emulation: Routing Protocols (planning/prototype for OSPF-like convergence on small graphs).
  - TASK-303 Advanced Emulation: Layer 2 Simulation (MAC learning lifecycle, flooding/aging; STP baseline model).

## 📌 TASK-553 — Tests: Mixed L2/L3 Multi-Hop Forwarding Scenarios

- Priority: High
- Why: Validates the combined L2→L3 forwarding pipeline end-to-end with per-hop metadata and assertions.
- Notes: New topology fixture (End Device → Switch → Router → Destination); extend resolve_flow_path hop metadata; assertions on sequence and final resolution.

## 📌 TASK-562 — Backend: Physical Medium Mapping (infrastructure links)

- Priority: Medium
- Why: Complete allowed-media coverage for Core↔Edge, OLT↔Edge, and AON Switch↔Edge; ensure Link Details UI aligns.
- Notes: Restrict routed_p2p to SMF; define access uplink variants; add focused backend tests and UI verification.

## 🔁 Epic — Implement Ring Protection (TASK-201…217)

- Summary: Emulate STP‑like L2 ring protection: detect cycles, ensure exactly one BLOCKING link per ring in healthy state, handle failover/recovery, suppress flaps, support admin override, emit events/metrics, and visualize in UI.
- Priority: Medium (after ongoing UI and cleanup work)
- Scope (subtasks template)
  - TASK-201 Link model/schema: protection_mode enum, API schemas
  - TASK-202 Ring detection: cycle basis, normalized ring_id
  - TASK-203 Protection service: choose & set BLOCKING (healthy ring)
  - TASK-204 Failover: unblock when another ring member is DOWN
  - TASK-205 Recovery: re‑block after stabilization (delay)
  - TASK-206 Overlapping rings: PER_CYCLE baseline strategy
  - TASK-207 Debounce & flap suppression
  - TASK-208 Admin override: manual block (precedence)
  - TASK-209 Events & ordering: link.protection.updated + docs
  - TASK-210 Metrics/observability: counters, histograms
  - TASK-211 Performance/scale tests (1k links, dense rings)
  - TASK-212 Overlap optimization: MIN_BLOCK_SET (greedy)
  - TASK-213 Frontend visualization: BLOCKING styling (dashed, tooltip ring_id)
  - TASK-214 API /api/rings snapshot
  - TASK-215 Property‑based invariants: exactly one BLOCKING per cycle
  - TASK-216 Audit logging
  - TASK-217 Advanced policies: weighted selection (util/capacity)

## 🧭 Epic — Improve Selection and Deletion Workflow (TASK-107, TASK-108, TASK-109)

- Why: Critical UX. Enables precise link selection, safe device deletion, and clean link deletion with confirmation.
- Scope
  - TASK-107 Frontend: Link selection & highlighting (High)
  - TASK-108 Frontend: Device deletion workflow (High)
  - TASK-109 Frontend: Link deletion workflow (High)

## 📌 TASK-110 — Frontend: Extended selection (marquee & shortcuts)

- Priority: Medium (follow after deletion workflow)
- Notes: Power‑user productivity for building large topologies.

## 📌 TASK-141 — Frontend: IPAM tab re‑implementation

- Priority: Medium
- Notes: Evolve simple IPAM tab into a real analysis tool.

## 📌 TASK-141H — Refactor: Link ID/Format Helpers

- Priority: Low
- Notes: Centralize helpers; client fixed once, but shared utility is cleaner.

## 🧱 Epic — Frontend Scalability & Virtualization

- Why: Needed to scale to 1k+ devices smoothly.
- Includes
  - TASK-141I Performance: Link Visibility & Framerate Guard (Very High)

## 📦 TASK-142 — Frontend: Save/Load Sandbox feature

- Priority: High
- Notes: Crucial UX to save and reuse complex scenarios.

## 🧩 TASK-143 — Full‑stack: Manual VLAN configuration & simulation logic

- Priority: Medium–High (roadmap‑dependent)
- Notes: First step to L2 features beyond MAC learning.

## � TASK-027 — Backend: /31 P2P link allocation logic

- Summary: Allocate /31 point-to-point subnets for router-to-router links and assign addresses to the two uplink interfaces deterministically.
- Why: Core networking realism for multihop routing and IP-level reachability scenarios.
- Subtasks
  - Determine deterministic device ordering
  - Carve next /31 from supernet (skip used)
  - Create two p2p_uplink interfaces
  - Assign lower IP to first device, higher to second
  - Validate exactly two endpoints
- Notes: Pair with TASK-028 for constraints/validation.

## 📌 TASK-028 — Backend: IPAM validation & constraints (subset)

- Summary: Strengthen validation around /31 allocation and unique IP guarantees.
- Subtasks
  - Unique IP constraint
  - Prevent second management interface (mgmt0)
  - Validate /31 fully allocated (no orphan side)
  - Exhaustion error (POOL_EXHAUSTED)
  - Negative tests
- Relationship: Treat as a sub‑task to TASK-027 for planning.

## 📌 TASK-043 — Structured error response schema

- Summary: Introduce `{ code, message, detail? }` envelope while preserving `detail` for backward compatibility.
- Priority: Low; hygiene and DX improvement.

## 📌 Epic — Implement Debug Traffic Injection (from TASK-057, 062–070)

- Summary: Allow controlled traffic overrides for debug scenarios, with API/UI, observability, and micro‑tick support.
- Scope
  - Model fields (value, mode)
  - Application in tick (add vs override)
  - API endpoint with feature flags
  - UI controls in Device Details
  - Observability (metrics, logs)
  - Micro‑tick recompute path
- Priority: Medium

---

For all other historical items, see `./COMPLETED_TASKS.md`.

---

## 🧹 TASK-800 — Tech Debt: Resolve Pylance Type-Checking Warnings

- Priority: Low
- Why: Reduce IDE noise and improve static analysis quality without changing runtime behavior.
- Scope (examples)
  - Use cast(...)/col() patterns to appease SQLAlchemy instrumentation warnings where appropriate.
  - Tighten types across endpoints/services (e.g., Status | str | None) and add isinstance guards before .value access.
  - Keep quality gates green (ruff, pytest) after changes.

## 🔴 TASK-902 — Traffic Engine: Port-specific aggregation and WS payload extension

- Priority: High
- Why: Finalize GPON simulation by rolling ONT traffic into specific OLT PON interfaces; device-level totals remain.
- Scope
  - Authoritative ONT→PON-port mapping via optical resolver helper.
  - Aggregate per-interface metrics for OLTs; retain device totals.
  - Extend WS event (deviceMetricsUpdated) to optionally include per-port metrics.
  - Tests: rollups and event emission.

## 📈 TASK-904 — Establish Performance Baseline and Regression Testing

- Priority: Medium
- Why: Ensure sustained performance after backend migrations; catch regressions early.
- Scope
  - Factory for medium topology (N OLT PON ports, M ONTs distributed).
  - Measure `/api/ports/summary` latency (local target: < 50 ms).
  - Regularly run perf harness; collect pyinstrument flamegraphs; document observations.
