# UNOC Audit & Fix Backlog

Working backlog from the 2026-07-04 simulation-correctness audit plus items found during
manual QA. Roughly priority-ordered. Shipped items kept for context. Tick items off as done.

## Shipped (on `main`)

- **Batch 1 — metrics stale-kill**: authoritative per-tick metric sets + client reconcile. (#4 / #7a / #8)
- **Batch 2 — optical degraded badge**: optical WARNING/CRITICAL → amber DEGRADED ONT badge. (#7b)
- **Batch 3 — OVERRIDDEN node badge**: admin-forced status shown as dashed frame + "OVR" badge. (#1 partial)
- **Batch 4 — EventStore telemetry skip**: ephemeral metrics/congestion events not persisted; fixed
  device-create 500/409 (sequence collision) + eventstore bloat.
- **Batch 5 — deterministic port ordering**: natural-sorted port summaries; cells no longer jump. (#2)
- **Batch 6 — leaf delivered-primary**: leaf traffic shows delivered + muted `req NNG` when throttled. (#3)
- **Batch 7 — link auto-port**: single-link auto-uses default ports; Alt opens the port picker.
  (Multi-link `createManyToOne` always auto — no per-pair picker; accepted.)
- **Batch 8 — provision persists status**: provision now calls Go status-service `propagate_status`
  (update_database=True) so freshly provisioned leaves generate traffic immediately (no manual Save).
- **Batch 9 — link.created carries length_km/physical_medium_id**: new links show length/medium in the
  panel immediately (was blank until Save — pure frontend event-payload gap; DB always had the values). (#6)
- **Batch 10 — L3 logical-graph caching (perf foundation)**: `has_upstream_l3_or_anchor` now reuses a
  version-keyed logical-graph snapshot instead of rebuilding per device; dropped the O(N) override
  fingerprint and the redundant provision coalescer recompute. Profiled: `build_logical_graph` 24.5%→1.3%,
  coalescer `recompute_dirty` 55.7%→0%. NOTE: real CPU-waste reduction, but wall-clock provision still
  5-8s — a second O(N) L3 cost now dominates (see below).

## Performance (big area — measure with py-spy, installed in .venv-audit)

### `trace_l3_path_to_anchor` router-chain caching · backend · HIGH · biggest remaining provision cost
After Batch 10, this hop-by-hop L3 routing walk (N+1 DB queries per hop, per router, per device) is now
~40% of provision CPU. Same fix pattern as Batch 10: memoize router L3 chains per PATHFINDING_STORE
version so all device evaluations in a recompute share them. This is the next perf batch.

### Debug full-snapshot is expensive & polled · backend/frontend · MEDIUM
`/api/debug/full-snapshot` (`gather_full_snapshot`) runs optical Dijkstra for ALL ONTs — ~26% CPU while
the Debug tab is open/polling on a large topology. Don't poll it (or cache per topo-version / make it
cheaper). Competes with everything.

### EventStore root fix — atomic sequence · backend · MEDIUM · reliability
`_next_sequence` uses non-atomic `MAX(sequence)+1`. Batch 4 removed the constant telemetry writer so
collisions are rare, but concurrent domain-event writes can still race. Use a Postgres native sequence /
IDENTITY. EventStore-schema-sensitive (AGENTS.md caution) — own batch.

## Audit findings still open

- **#5 drag/drop realtime** · frontend · LOW · likely already fixed. Original ~10 s delay was the
  EventStore-500 retry storm (fixed by Batch 4). Verify a dragged node now appears instantly; if so, close.
- **#1 deprovision + orphan cleanup** · backend+frontend · MEDIUM. No deprovision action; duplicate/orphan
  devices accumulate. Add deprovision (service + endpoint + UI); make orphan delete obvious. NOTE:
  provisioned-but-DOWN is a correct, realistic state — do NOT gate provisioning on backbone reachability.

## UX backlog (user-reported)

- **Bulk multi-select** · frontend · MEDIUM. No select-all / rubber-band for many devices (e.g. 100 ONTs).
- **Node redesign / cockpit sizing** · frontend · LARGE · rising. Cockpit content overflows on small nodes
  (throttled leaf rows overlap labels; OVR badge position rides on this). Device-type-dependent structure
  that auto-sizes to content; design-first effort.

## Watch / low-priority

- **optical-service reachability blips** · infra · LOW. Intermittent `partial_fallback (4/5)` during status
  checks, recovers to `go_active 5/5`. Likely a brief health-check timeout. Ties into finding #9 (strict-Go).
