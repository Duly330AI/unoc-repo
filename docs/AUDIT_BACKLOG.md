# UNOC Audit & Fix Backlog

Working backlog from the 2026-07-04 simulation-correctness audit plus items found during
manual QA. Roughly priority-ordered. Shipped items kept for context. Tick items off as done.

## Shipped (on `main`)

- **Batch 1 — metrics stale-kill**: authoritative per-tick metric sets + client reconcile. (#4 / #7a / #8)
- **Batch 2 — optical degraded badge**: optical WARNING/CRITICAL → amber DEGRADED ONT badge. (#7b)
- **Batch 3 — OVERRIDDEN node badge**: admin-forced status shown as dashed frame + "OVR" badge. (#1 partial)
- **Batch 4 — EventStore telemetry skip**: ephemeral events not persisted; fixed device-create 500/409.
- **Batch 5 — deterministic port ordering**: natural-sorted port summaries; cells no longer jump. (#2)
- **Batch 6 — leaf delivered-primary**: leaf traffic shows delivered + muted `req NNG` when throttled. (#3)
- **Batch 7 — link auto-port**: single-link auto-uses default ports; Alt opens the port picker.
- **Batch 8 — provision persists status**: provision calls Go status-service so leaves generate
  immediately (no manual Save).
- **Batch 9 — link.created carries length_km/physical_medium_id**: new links show length/medium
  immediately (was blank until Save — frontend event-payload gap). (#6)
- **Batch 10 — L3 logical-graph caching**: version-keyed graph reuse; dropped O(N) override fingerprint +
  redundant provision coalescer recompute. (perf foundation)
- **Batch 11 — L3 router-chain caching**: memoize `trace_l3_path_to_anchor` per recompute pass
  (session-scoped). **Benchmarked: L3 recompute over 200 leaves 24,600ms → 285ms (~85×)**; L3 recompute is
  now O(N). Reusable harness: `backend/tests/perf/bench_l3_recompute.py` (isolated sqlite; run on two
  branches to compare).

## Performance (big area — measure with `bench_l3_recompute.py` / py-spy)

### Debug full-snapshot is expensive & polled · backend/frontend · MEDIUM

`/api/debug/full-snapshot` (`gather_full_snapshot`) runs optical Dijkstra for ALL ONTs — ~26% CPU while
the Debug tab / topology view polls on a large topology. Don't poll it (or cache per topo-version / make
it cheaper). NOTE: with Batch 10/11 the L3 recompute is no longer the provision bottleneck — re-profile a
real bulk provision (Debug tab closed) to find the next real hotspot (optical recompute is a candidate).

### EventStore root fix — atomic sequence · backend · MEDIUM · reliability

`_next_sequence` uses non-atomic `MAX(sequence)+1`. Batch 4 removed the constant telemetry writer so
collisions are rare, but concurrent domain-event writes can still race. Use a Postgres native sequence /
IDENTITY. EventStore-schema-sensitive (AGENTS.md caution) — own batch.

## Audit findings still open

- **#5 drag/drop realtime** · frontend · LOW · likely already fixed (was the EventStore-500 storm). Verify.
- **#1 deprovision + orphan cleanup** · backend+frontend · MEDIUM. No deprovision action; orphans
  accumulate. Add deprovision (service + endpoint + UI). NOTE: provisioned-but-DOWN is a correct state —
  do NOT gate provisioning on backbone reachability.

## UX backlog (user-reported)

- **Bulk multi-select** · frontend · MEDIUM. No select-all / rubber-band for many devices.
- **Node redesign / cockpit sizing** · frontend · LARGE · rising. Cockpit content overflows small nodes;
  device-type-dependent structure that auto-sizes to content; design-first effort.

## Watch / low-priority

- **optical-service reachability blips** · infra · LOW. Intermittent `partial_fallback (4/5)` during status
  checks, recovers to `go_active 5/5`. Likely a brief health-check timeout.
