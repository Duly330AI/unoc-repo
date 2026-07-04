# UNOC Audit & Fix Backlog

Working backlog from the 2026-07-04 simulation-correctness audit plus items found during
manual QA. Roughly priority-ordered. Shipped items kept for context. Tick items off as done.

## Shipped (audit fix sequence, on `main`)

- **Batch 1 — metrics stale-kill**: authoritative per-tick metric sets + client reconcile. (#4 / #7a / #8)
- **Batch 2 — optical degraded badge**: optical WARNING/CRITICAL → amber DEGRADED ONT badge. (#7b)
- **Batch 3 — OVERRIDDEN node badge**: admin-forced status shown as dashed frame + "OVR" badge. (#1 partial)
- **Batch 4 — EventStore telemetry skip**: ephemeral metrics/congestion events not persisted; fixes
  device-create 500/409 (sequence collision) + eventstore bloat.
- **Batch 5 — deterministic port ordering**: port summaries sorted in natural order; cells no longer jump. (#2)
- **Batch 6 — leaf delivered-primary**: leaf traffic shows delivered + muted `req NNG` when throttled. (#3)
- **Batch 7 — link auto-port**: single-link creation auto-uses default ports; hold Alt to open the port
  picker. NOTE: multi-link (K + multi-select, `createManyToOne`) always auto-creates — no per-pair picker
  exists, so Alt has no effect there; accepted as expected behavior.

## Next up (prioritized)

### Provisioned leaves don't generate traffic until a tariff "Save" · backend · MEDIUM-HIGH · correctness

A freshly created + provisioned + linked leaf (CPE/ONT), UP with an auto-assigned default tariff,
generates NO traffic until the user presses "Save" on its tariff. Confirmed live 2026-07-04: `aon_cpe_3`
and `aon_cpe_4` are BOTH `status=UP`, `provisioned=true`, `tariff_id=4`, each linked to an AON switch
(link `status=UP`/`eff=UP`) — yet `aon_cpe_4` is ABSENT from the Go traffic snapshot while `aon_cpe_3`
(identical API-visible state, but Saved) generates. All `/api/devices` + `/api/links` fields are identical
between generating and non-generating leaves. Observed: one tariff Save appears to activate ALL pending
leaves. Directly breaks the core create→simulate workflow. Root cause needs a focused dig — candidates:
(a) create-time auto-tariff (TASK-407) not actually persisted to the DB `tariff_id` column (API may show a
computed/effective default) so the Go engine's `TariffID.Valid` gate fails until Save persists it;
(b) a mutation-triggered recompute the provision path lacks. Investigate: raw DB `tariff_id` of a
not-saved leaf, the tariff-update (`updateTariffOnly`/PUT) recompute path, and the Go engine tariff read.

### EventStore root fix — atomic sequence · backend · MEDIUM · reliability

`_next_sequence` uses non-atomic `MAX(sequence)+1` (`backend/services/event_store.py`). Batch 4 removed
the constant telemetry writer so collisions are now rare, but concurrent domain-event writes can still
race. Root fix: allocate `sequence` via a Postgres native sequence / IDENTITY (or advisory lock).
EventStore-schema-sensitive (AGENTS.md caution) — own batch, scope carefully.

### Audit findings still open

- **#6 link-defaults hydration** · frontend/backend · LOW-MED. New links show blank `length_km` /
  `physical_medium_id` until an update saves. Backend derives defaults on create and returns them —
  hydrate the create response into the link store, and guarantee a default medium for every FIBER/P2P.
- **#5 drag/drop realtime** · frontend · LOW · likely already fixed. Original ~10 s node-appearance delay
  was probably the EventStore-500 retry storm (resolved by Batch 4). Verify a dragged node now appears
  instantly; if so, close. Otherwise add a `device.created` realtime handler / immediate canvas draw.
- **#1 deprovision + orphan cleanup** · backend+frontend · MEDIUM. No deprovision action; duplicate/orphan
  devices accumulate. Add deprovision (service + endpoint + UI) and make orphan delete obvious.
  NOTE: provisioned-but-DOWN is a correct, realistic state — do NOT gate provisioning on backbone
  reachability (would conflate SERVICE and PHYSICAL truth per AGENTS.md §4).

## UX backlog (manual QA, user-reported 2026-07-04)

- **Bulk multi-select** · frontend · MEDIUM. After bulk-creating many devices (e.g. 100 ONTs) there is no
  select-all / rubber-band multi-select; only shift-click one-by-one. Add marquee + select-all.
- **Node redesign / cockpit sizing** · frontend · LARGE · rising priority. Cockpit content overflows on
  smaller nodes — throttled leaf rows (`1.00 Gbps  req 91.5G`) overlap the UPSTREAM/DOWNSTREAM labels;
  richer rows make it worse. Nodes should get a clear, device-type-dependent structure that auto-sizes to
  content, with later polish (meaningful animated elements). Best as a proper design-first effort before
  adding more per-row info. (OVR badge position also rides on this.)

## Watch / low-priority

- **optical-service reachability blips** · infra · LOW. `/api/debug/go-services` intermittently reports
  `partial_fallback (4/5)` with optical-service on Python fallback during status checks, then recovers to
  `go_active 5/5` (no crash in its err log). Likely a brief health-check timeout. Only investigate if it
  degrades actual optical recomputes; ties into finding #9 (make fallback fail-fast for audits).
