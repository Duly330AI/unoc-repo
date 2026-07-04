# UNOC Audit & Fix Backlog

Working backlog from the 2026-07-04 simulation-correctness audit plus items found during
manual QA. Roughly priority-ordered. Shipped items kept for context. Tick items off as done.

## Shipped (audit fix sequence, on `main`)

- **Batch 1 — metrics stale-kill**: authoritative per-tick metric sets + client reconcile; DOWN
  devices/flows clear instead of showing stale last-known traffic. (findings #4 / #7a / #8)
- **Batch 2 — optical degraded badge**: optical WARNING/CRITICAL renders as amber DEGRADED on the ONT
  node badge; operational status + traffic unchanged. (#7b)
- **Batch 3 — OVERRIDDEN node badge**: admin-forced status shown as dashed frame + "OVR" badge, distinct
  from a real fault. (#1 partial — state-hygiene visibility)
- **Batch 4 — EventStore telemetry skip**: ephemeral metrics/congestion events no longer persisted to
  the EventStore; fixes intermittent device-create 500/409 (sequence collision) + eventstore bloat.
- **Batch 5 — deterministic port ordering**: port summaries sorted in natural order (shared helper);
  subscriber / PON port-matrix cells no longer jump between refreshes. (#2)
- **Batch 6 — leaf delivered-primary**: leaf traffic rows show delivered as the hero value + a small
  muted `req NNG` label when throttled (was "1.0G / 92G" which read as loss). (#3)

## Next up (prioritized)

### EventStore root fix — atomic sequence · backend · MEDIUM · reliability

`_next_sequence` uses non-atomic `MAX(sequence)+1` (`backend/services/event_store.py`). Batch 4 removed
the constant telemetry writer so collisions are now rare, but concurrent domain-event writes can still
race. Root fix: allocate `sequence` via a Postgres native sequence / IDENTITY (or advisory lock).
EventStore-schema-sensitive (AGENTS.md caution) — own batch, scope carefully.

### Audit findings still open

- **#6 link-defaults hydration** · frontend/backend · LOW-MED. New links show blank `length_km` /
  `physical_medium_id` until an update saves. Backend derives defaults on create and returns them —
  hydrate the create response into the link store, and guarantee a default medium for every FIBER/P2P.
- **#5 drag/drop realtime** · frontend · LOW. No `device.created` realtime handler in `devicesStore` and
  no periodic device poll; new devices appear via optimistic push only. Add a created handler / ensure
  the canvas draws from the store push immediately.
- **#1 deprovision + orphan cleanup** · backend+frontend · MEDIUM. No deprovision action; duplicate/orphan
  devices accumulate. Add deprovision (service + endpoint + UI) and make orphan delete obvious.
  NOTE: provisioned-but-DOWN is a correct, realistic state — do NOT gate provisioning on backbone
  reachability (would conflate SERVICE and PHYSICAL truth per AGENTS.md §4).

## UX backlog (manual QA, user-reported 2026-07-04)

- **Bulk multi-select** · frontend · MEDIUM. After bulk-creating many devices (e.g. 100 ONTs) there is no
  select-all / rubber-band multi-select; only shift-click one-by-one. Add marquee + select-all.
- **Link create: auto/default port** · frontend · LOW-MED. Linking two devices always pops the port picker
  requiring manual confirm even when "auto"/"default" is wanted. Add an auto-confirm/default path; only
  prompt when the port choice is genuinely ambiguous.
- **Node redesign / cockpit sizing** · frontend · LARGE · rising priority. Cockpit content overflows on
  smaller nodes — e.g. throttled leaf rows (`1.00 Gbps  req 91.5G`) overlap the UPSTREAM/DOWNSTREAM
  labels; richer rows make it worse. Nodes should get a clear, device-type-dependent structure that
  auto-sizes to content, with later polish (meaningful animated elements). Best tackled as a proper
  design-first effort before adding more per-row info. Until then, band-aids (smaller/wrapped labels)
  are deferred. (OVR badge position also rides on this.)

## Watch / low-priority

- **optical-service reachability blips** · infra · LOW. `/api/debug/go-services` intermittently reports
  `partial_fallback (4/5)` with optical-service on Python fallback during status checks, then recovers to
  `go_active 5/5` (no crash in its err log). Likely a brief health-check timeout. Only investigate if it
  starts degrading actual optical recomputes; ties into finding #9 (make fallback fail-fast for audits).
