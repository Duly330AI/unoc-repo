# AGENTS.md

## 1. System Overview

UNOC is a distributed network simulation system. It simulates telecom and network infrastructure such as OLTs, AON switches, ONTs, CPEs, links, ports, optical paths, provisioning, and analytics.

UNOC separates system state into three explicit truth layers:

- `PHYSICAL_TRUTH`: devices, ports, links, topology
- `SERVICE_TRUTH`: subscribers, provisioning, ONT/CPE mapping
- `ANALYTICS_TRUTH`: derived counts, utilization, aggregation

## 2. Repository / Worktree Context

Main working path used during recovery:

```powershell
C:\noc_project\recovery_workspaces\unoc_repo_2026_03_run_audit
```

Current stabilization PR:

- PR #7

Important: future agents must inspect the current git state and must not assume old reports are still current.

## 3. How to Start the System

Preferred full logged startup:

```powershell
.\scripts\start-stack-logged.ps1 -IncludeOptionalGoServices
```

Status check:

```powershell
.\scripts\status-stack.ps1
```

Stop stack:

```powershell
.\scripts\stop-stack.ps1 -Force
```

Default ports:

- Backend/FastAPI: `5001`
- Frontend/Vite: `5173`
- Traffic engine: `8080`
- Optional Go/gRPC services: `50051-50054`

The logged startup may open several service windows or log files. Prefer logs and status scripts over guessing whether services are running.

## 4. Architecture Truth Rules

The system separates `PHYSICAL_TRUTH`, `SERVICE_TRUTH`, and `ANALYTICS_TRUTH`.

- Physical truth owns topology: devices, ports, links.
- Service truth owns L4 provisioning: ONTs, CPEs, subscribers.
- Analytics truth owns derived metrics: counts, utilization, aggregation.
- No layer may silently overwrite another.
- Debug endpoints explain mismatches instead of hiding them.

Important current state:

- EventStore exists and write paths are instrumented.
- The system is still a dual-write system: DB writes remain operational, and EventStore records audit/write-path events.
- Do not assume the system is fully event-sourced unless a later PR explicitly completes that migration.
- EventStore hard enforcement may exist but should not be enabled casually.

## 5. Write Path Rules

Existing DB writes remain the operational mutation path. Mutations should emit EventStore write-path events.

EventStore logging is best-effort unless explicitly changed in a future migration. EventStore failures must not silently be treated as business logic failures.

Do not bypass backend services for topology or provisioning mutations.

## 6. Go Services

Go services exist for traffic, status, optical, and port-summary style computations. Some Go services are optional depending on local setup.

If optional Go services are unavailable, backend fallback or degraded behavior may still work. Do not rewrite Go services unless the task specifically targets Go behavior.

If debugging Go, verify actual process/listening ports and backend health/fallback state.

## 7. Debugging Strategy

Important endpoints:

- `/api/health`: backend health check
- `/api/debug/full-snapshot`: broad debug snapshot
- `/api/debug/subscriber-model`: L4 subscriber model and mapping decisions
- `/api/debug/device-state`: layered device state plus validation
- `/api/debug/optical-state`: optical path/debug state
- `/api/debug/layer-leak-report`: layer isolation violations
- `/api/debug/aggregation-audit`: subscriber aggregation audit
- `/api/debug/count-semantics`: physical/provisioned/effective count semantics
- `/api/debug/truth-model`: physical/service/analytics truth snapshots and conflicts
- `/api/debug/event-log`: deterministic simulation event log view
- `/api/debug/projections`: replay-derived physical/service/analytics projections
- `/api/debug/replay?from=0&to=20`: bounded event replay debug view
- `/api/debug/event-store-health`: EventStore/backfill/projection health

Use debug endpoints before changing code. If UI values look wrong, first verify backend truth/debug endpoints. Do not infer source of truth from UI alone.

## 8. Known System Behaviors

- OLT PON ports have capacity limits, for example `128`.
- AON is not infinite capacity; it uses `1:1` access-port semantics.
- Physical count, provisioned count, and effective count may differ.
- Example known case: physical/provisioned AON CPE count may be `2` while effective AON count is `1` if two CPEs share one access port.
- `-` in UI often means missing/unknown mapping or display fallback, not necessarily backend absence.
- Passive optical devices such as HOP, ODF, and Splitter may require optical/debug validation before assuming UI display is correct.

## 9. Common Pitfalls for Agents

- Do not assume missing UI values mean missing backend logic.
- Do not rewrite architecture when fixing display bugs.
- Do not introduce new abstraction layers unless explicitly requested.
- Do not continue EventStore migration unless explicitly requested.
- Do not treat EventStore as fully authoritative unless current code proves it.
- Do not modify many unrelated files in one bugfix.
- Avoid broad refactors.
- Prefer small, scoped PRs after this stabilization PR.

## 10. Safe Change Rules

Allowed:

- focused bug fixes
- missing aggregation fixes
- UI display corrections
- debug/instrumentation improvements when explicitly requested
- small tests/validation additions

Not allowed without explicit instruction:

- architecture redesign
- replacing the DB model
- changing EventStore direction
- rewriting simulation engine
- rewriting Go services
- changing public API contracts unnecessarily

## 11. Validation Checklist for Agents

Before reporting success, run relevant checks:

```powershell
git status --short --branch
git diff --check
.\scripts\status-stack.ps1
```

Run relevant `curl` checks for backend and debug endpoints.

For backend changes, run Python compile checks on touched modules.

For frontend changes, run the appropriate frontend type/build check if dependencies are available. If frontend checks are blocked by known unrelated dependency issues, report that honestly.

## 12. Final Principle

System priority order:

1. Correctness of simulation
2. Deterministic behavior
3. Observability through debug endpoints
4. Performance
5. UI polish

Do not optimize or polish before correctness and observability are verified.
