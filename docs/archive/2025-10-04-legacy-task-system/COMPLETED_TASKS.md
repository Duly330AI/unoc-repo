# Completed & Archived Tasks

This document consolidates early and mid-phase tasks that are now completed, obsolete, or intentionally deferred. For currently active work, see `./BACKLOG.md`.

Note: This is a high-level consolidation, not a verbatim copy of every checklist.

## ✅ Archived — Completed or Obsolete

- Auto Layout (unnamed) — obsolete. Replaced by container-specific layout and physics workstreams.
- TASK-029 IPAM provisioning test harness — completed. Covered by the current test suite.
- TASK-034, TASK-034B, TASK-034C, TASK-034D (Pathfinding & Resolver suite) — completed. Optical and logical resolvers implemented with deterministic tie-breakers; cache and invalidation integrated.
- TASK-036 (Admin Overrides) — completed across backend and frontend; DEGRADED propagation wired.
- TASK-039 (Optical Signal UI) — completed via “Digital Display” cockpits and optical editing.
- TASK-040A (Scrollbar bugfix) — completed within details panel refactors.
- TASK-041A (Expose AON Switch & AON CPE) — completed; types, palette, and UI present.
- TASK-044, TASK-045, TASK-046, TASK-047 (File-based catalog line) — obsolete. Superseded by the database-backed HardwareModel/PortProfile architecture.
- TASK-048 (Layout persistence) — completed. PATCH `/api/layout/positions` exists.
- TASK-049 (Transactional deletion) — completed (single-transaction device removal, with cascades).
- TASK-051 (Old IPAM Pools) — obsolete. Superseded by VRF/Prefix IPAM.
- Traffic Engine v1 & legacy UI group — completed/obsolete; superseded by Traffic Engine v2 and new cockpits:
  - TASK-052, TASK-052A, TASK-053, TASK-055A, TASK-056, TASK-058, TASK-059, TASK-060
- Cockpit implementations (Digital Display) — completed:
  - TASK-071 through TASK-089
- TASK-111 (Soft ONT dependency) — completed and verified.
- TASK-554 (Traffic Engine v2) — completed.

### Onboarding Q&A — Cross-links

- Q3 (Overview & Domain Model): - DEGRADED vs DOWN (Leaf generation): `backend/services/traffic/v2_engine.py` gating for leaves (UP-only; AON_CPE DEGRADED exception without backbone) and NO_SIGNAL guard; infra aggregation vs admin DOWN in `backend/services/traffic/v2_aggregation.py::compute_device_changes`. - Container roles (POP/CORE_SITE): POP links disallowed and validations in `backend/api/endpoints/links.py`; parenting/placement rules in `backend/utils.py::validate_parent_child`; anchors used as aggregation sinks (not link endpoints) in `backend/services/traffic/v2_engine.py`. - L2/L3 pipeline fallback: Primary BFS over passable links/devices; fallback to `backend/services/forwarding_service.py::resolve_flow_path` within `v2_engine.py::run_tick` when no anchor path exists. - IPAM /31 pending: Management IP allocation in `backend/services/seed_service.py::ensure_ipam_defaults` and provisioning in `backend/services/provisioning_service.py`; no dedicated /31 allocator on router-to-router links; link classification in `backend/api/endpoints/links.py`. - Router cockpit capacity: Max via `backend/services/catalog_effective.py::get_effective_device_capacity_mbps` (exposed in `backend/api/schemas.py` parameters), current via TEv2 snapshot computed in `backend/services/traffic/v2_aggregation.py::compute_device_changes`.

      - Q9 (Container Model & UI):
            - Parent rules (authoritative): `backend/utils.py::validate_parent_child` (OLT/AON_SWITCH parent optional; if set must be POP/CORE_SITE; containers/backbone no parent; CORE_ROUTER no parent; ONT/AON_CPE not directly under POP/CORE_SITE).
            - Container aggregation status/metrics: `unoc-frontend-v2/src/components/cockpits/containers/POPCockpit.vue` and `CoreSiteCockpit.vue` (DOWN > DEGRADED > UP; total bps sum of children).
            - Container drag physics: `unoc-frontend-v2/src/composables/topologyCore/containerBoundsForce.ts` and `simulation.ts` (clamp within bounds, light slot attraction; pinned nodes respected).
            - Link proxy modal logic: `unoc-frontend-v2/src/composables/topologyCore/handlers.ts` (candidates list; toast when none; containers not endpoints; event `unoc:openLinkProxySelector`). Client store guard in `unoc-frontend-v2/src/stores/linksStore.ts`.
            - Link drawing across containers: `unoc-frontend-v2/src/composables/topologyCore/draw.ts` (line from actual device positions; containers in background layer; no clipping at container borders).

- Q5 (IPAM & Status clarifications): - VRF/prefix uniqueness and future transit VRF: `backend/models.py` (InterfaceAddress `UniqueConstraint("prefix_id","ip")`, `UniqueConstraint("vrf_id","ip")`); seeds: `backend/services/seed_service.py`. - Passive device status (happy path): `backend/services/status_service.py::evaluate_device_status` (PASSIVE‑Zweig; `_prop_store.is_up`). - Traversal authority: `backend/services/status_service.py::is_link_passable`; used by TEv2 `backend/services/traffic/v2_engine.py` and propagation `backend/services/status_recompute.py`. - Anchors without IP: roles/anchors in `backend/models.py` (ALWAYS_ONLINE, `derive_role`); dependency checks in `backend/services/dependency_resolver.py`; TEv2 anchor discovery in `backend/services/traffic/v2_engine.py`. - Coalescing window vs. traffic tick: `backend/services/recompute_coalescer.py` (`UNOC_RECOMPUTE_COALESCE_MS`, default 150 ms) vs. `backend/services/traffic/v2_runner.py` (`TRAFFIC_TICK_INTERVAL_SEC`). WS outbox coalescing: `backend/api/endpoints/ws.py`.

- Q6 (Optik & Overrides): - Cache/Invalidierung: `backend/services/pathfinding.py::PathfindingStore.bump_version` (+ optischer Resolver‑Cacheclear); Trigger in `backend/api/endpoints/{links.py,devices.py}` und `backend/services/background.py`. - Resolver/Tie‑Breaker: `backend/services/optical_path_resolver.py::resolve_optical_path` (Sortierung; `OpticalPathResult.segments`). - Optical recompute scope: `backend/services/optical_service.py::recompute_optical_paths_for_affected_onts` (MVP: alle ONTs). - Admin‑Override & Traversal: `backend/services/status_service.py::{evaluate_device_status,is_link_passable}`. - WS Mapping & Coalescing: `backend/api/endpoints/ws.py` (`device.optical.updated` → `deviceSignalUpdated`).

- Q7 (Realtime & UI Modell): - topo_version als Gap‑Detektor und Stale‑Drop: `backend/api/endpoints/ws.py` (Envelope inkl. `topo_version`), `backend/events.py` (Event‑Stempel), `unoc-frontend-v2/src/stores/devicesStore.ts` (Monotonie‑Guard). - Central Canvas Invariant: Geometrie im D3‑Layer (`unoc-frontend-v2/src/composables/topologyCore/draw.ts`, `containerBoundsForce.ts`); Cockpits kürzen/umbrechen Inhalte. - ONT‑Panel Datenfluss: WS liefert Signal‑Summary (`backend/services/optical_service.py`), Detail‑Pfad via REST/Snapshot bei Bedarf. - Hysterese (sticky Overload): Schwellen in `backend/services/traffic/v2_engine.py`/Kongestionslogik (Segmente detect ≥0.95, clear ≤0.85; Geräte/Links clear 0.95). - Event‑Reihenfolge Garantie Optical → Signal → Status: Orchestrierung in `backend/services/optical_service.py` und WS‑Fanout in `backend/api/endpoints/ws.py`.

- Q8 (Katalog & Determinismus & Recovery): - Katalog‑Overrides vs. Defaults: `backend/services/catalog_effective.py` (override → model default → fallback). API spiegelt Werte inkl. `parameters.*`: `backend/api/schemas.py::DeviceOut.from_model()`. - Deterministische Wiederholung: RNG `backend/services/traffic/rand.py::deterministic_rand01`, Tick‑Sequenz in `backend/services/traffic/v2_engine.py::TrafficEngine.run_tick()`, Snapshot‑Facade in `backend/services/traffic_engine.py::get_v2_snapshot()` und `/api/metrics/snapshot` Auswahl. - Debug Injection Ist‑Stand: keine Felder im Code; Aggregation via `v2_engine.py` + `v2_aggregation.py` über `per_device_totals`/`per_link_totals`. - Event‑Lücken & Recovery: per‑Entity Monotonie‑Guards in `unoc-frontend-v2/src/stores/{devicesStore.ts,linksStore.ts}`; Wiederabgleich über REST/Snapshot (`backend/api/endpoints/metrics.py`). - ON HOLD vs. Implementiert: Cockpits + `containerBoundsForce` vorhanden (siehe `docs/llm/COMPLETED_TASKS.md`), Physik‑Roadmap (Abschnitt 17) bleibt zukünftige Erweiterung; Frontend: `unoc-frontend-v2/src/composables/topologyCore/containerBoundsForce.ts`, `draw.ts`.

- Q10 (Ports Summary & Performance): - Cache/TTL/Locks: `backend/api/endpoints/ports.py::get_port_summary` (TTL ~2 s, Key `(topology_version, device_id)`, per‑Key Async‑Lock), Bulk: `get_bulk_port_summary`. - Invalidation: `backend/services/pathfinding.py::PathfindingStore.bump_version` + Resolver‑LRU clear (`backend/services/optical_path_resolver.py`). - Capacity sources: PON via `PortProfile.max_subscribers`, sonst `Interface.capacity` (Seed aus `PortProfile.speed_gbps` in `backend/api/endpoints/devices.py`). - Management‑Ports ausgeschlossen (Dokumentation in `docs/llm/08_ports.md`). - UI polling `usePortSummary.ts` (2 s, Race‑Guard).

- Q11 (Cockpits & Ports Nutzung): - RouterCockpit nutzt keine Ports‑Liste; „TotCap (Gbps)“: actual = upstream + downstream; maximum = `effective_capacity_mbps` (siehe `unoc-frontend-v2/src/components/cockpits/RouterCockpit.vue`). - OLTCockpit rendert PON‑Matrix aus Ports‑Summary (`usePortSummary.ts`, `OLTCockpit.vue`); ONT‑Drilldown optional via `backend/api/endpoints/ports.py::list_onts_under`. - Generic/Container Cockpits: gemeinsame Datenbasis Ports‑Summary; Darstellung laut `docs/llm/09_cockpit_nodes.md`.

- Q12 (Interfaces & Addresses): - Primäradresse implizit (erste) laut Kommentar in `backend/models.py::InterfaceAddress`; PortRole gegenüber legacy `role` bevorzugt (Indices vorhanden). - Management‑Interface‑Erzeugung und optionale IP‑Zuweisung in `backend/api/endpoints/devices.py` (mgmt0, POOL). - CRUD & Validierung in `backend/api/endpoints/interfaces.py`. - MAC‑Vergabe deterministisch über `backend/services/mac_allocator.py` (OUI 02:55:4E).

- Q13 (Traffic Engine v2 – Segmente & Thresholds): - Segment‑ID = f"{pon_if_id}::{odf_id}", Schwellen detect ≥0.95 / clear ≤0.85, Forwarding‑Fallback in `backend/services/traffic/v2_engine.py`. - Kapazitäten PON aus PortProfile/Defaults; Events enthalten Demand/Capacity (detected) ohne fertiges overload‑% Feld.

- Q14 (Tests & Performance Harness): - SQLite vs. Postgres: keine kritischen Unterschiede im aktuellen Pfad; konsolidierte Recompute‑Messung via Timing um Coalescer; asynchrone Stabilisierung durch Status/Snapshot‑Wartepunkte; Profiling manuell, keine automatische Artefaktablage.

- Q15 (API Semantik – Links & Devices): - Kanonische Link‑IDs client‑seitig erzeugt; Server erzwingt Kanonizität und nutzt DB‑Unique zur Race‑Abwehr (`backend/services/links_service.py::canonical_link_id`, `backend/api/endpoints/links.py::_create_link_impl`). - `PUT /devices/{id}` arbeitet feldweise (PATCH‑artig) via `exclude_unset` (`devices.py::update_device`). - `DELETE /devices/{id}` führt die Löschkaskade synchron im Request aus (`devices.py::delete_device`). - `GET /devices?include_interfaces=true` erweitert Payload ohne Paginierung; gezielt einsetzen. - `rule_id` aus `link_rules.py` nur bei POST sichtbar, bei GET bewusst `None` für Performance.

- Q16 (Async & Commands Playbook): - Async‑Modus: Implementiert ist „threading“ (Default) mit `BackgroundTasks`; Koaleszierung via `backend/services/recompute_coalescer.py` (Timer/Lock). Settings: `UNOC_ASYNC_MODE` in `backend/core/config.py` (Default „threading“). - Scripting/Tasks: PowerShell‑freundliche Temp‑Datei‑Pattern in `docs/llm/14_commands_playbook.md`. Nutzung der VS‑Code‑Tasks für deterministische Lint/Test/Build‑Läufe empfohlen. - Encoding/Perf‑Knobs: `PYTHONIOENCODING` für Stabilität; Perf‑Harness mit `PERF_SCALE`, `UNOC_PERF_PROFILE`, `UNOC_PERF_TAG` (siehe `backend/tests/perf/*`).

- Q17 (Finale Sammlung & Autorität): - Autorität: Nummerierte Docs + ADRs + Code gewinnen gegenüber Phase‑1‑/Planungsnotizen (`docs/architecture/status_service.md` ist historisch; aktuelle Regeln in `backend/services/status_service.py`). - Redis‑Rolle: derzeitig nicht im Code aktiv (keine Client‑Imports); Kurz‑Caches in‑process (`backend/api/endpoints/ports.py`), Queueing via Coalescer/BackgroundTasks. Docs `overview.md`/`caching-and-snapshots.md` beschreiben die skalierte Zielarchitektur. - L2/L3‑Vision: VRF/Prefix‑IPAM vorhanden (`backend/models.py`, `backend/api/endpoints/ipam.py`); Bridge‑Domains im Modell; dynamische Routing‑Protokolle sind Vision, nicht implementiert. - ODF Phase 2: Segment‑Aggregation/Hysterese umgesetzt (`backend/services/traffic/v2_engine.py`), gemäß ADR‑010. - DoD/Automatisierung: Quality‑Gates via VS‑Code‑Tasks (Ruff/Black/Isort/Pytest/Coverage); keine CI‑Konfig im Repo sichtbar.

- TASK-400 (Epic) — Full-stack: Implement Tariff-based Traffic Simulation — completed/obsolete. Superseded by TrafficEngineV2 and its comprehensive test suite; frontend Tariffs UI implemented. Subtasks 401–406 covered by TASK-401..406 entries below and TEv2.
- TASK-404 Backend: Enhance Traffic Engine — completed. Realized as part of TrafficEngineV2 (bounds, asymmetry, determinism, events) with tests.
- TASK-112 (Backend: Optical recompute service skeleton) — completed. The optical_service is now a fully‑fledged core component beyond an initial skeleton.
- TASK-141B (Fix Metrics Viewer Column Mapping & Formatting) — completed. Metrics viewer overhauled as part of broader UI polish and in a good state.
- TASK-512 (Integrate Prefix-based IPAM into Provisioning) — completed/duplicate. Subsumed by the VRF/Prefix IPAM refactor and follow-ups (see TASK-513, TASK-514); the platform now uses VRFs and Prefixes end‑to‑end.

- TASK-522 (Backend: Integrate Hardware Catalog into Device Lifecycle) — completed. Devices are linked to HardwareModel and interfaces are auto-created from PortProfiles during device creation; verified by seeds and API behavior.

### From task_600-699.md (Milestone 9: Foundational Network Emulation)

- TASK-500 Epic: Interface & Addressing Overhaul — completed. Stateful interfaces with unique MACs, roles, admin status, and InterfaceAddress realized; CRUD + tests in place.
- TASK-510 Epic: IPAM v2 (Interface-bound, VRF-aware) — completed. VRF/Prefix IPAM is authoritative across provisioning and audit.
- TASK-520 Epic: Hardware Catalog & Device Realization — completed. HardwareModel + PortProfile drive device instantiation.
- TASK-530 Epic: L2 Switching Pipeline (Minimal) — completed. Bridge domains and MAC learning implemented with tests.
- TASK-540 Epic: L3 VRF & Routing (Static) — completed. VRFs and static routes available; reachability by LPM/next-hop.
- TASK-550 Epic: Traffic Engine v2 (Flow-based, Tariff-shaped) — completed. Implemented as TEv2 with deterministic ticks and events.
- TASK-551 Backend: Flow model & basic forwarding pipeline — completed. Flow model and forwarding orchestration over L2/L3 present.
- TASK-560 Epic: Optical & Signal Budget Integration — completed. Optical resolver + budget gating affect device/link status; events emitted.
- TASK-570 Epic: Tariffs v2 & Subscriber Lifecycle — completed. Tariffs authoritative for ONT traffic generation and shaping.
- TASK-580 Epic: APIs, UI, and Tooling — completed. CRUD, observability, and UI coverage for the new models delivered.
- TASK-590 Epic: Migration & Feature Flags — completed/obsolete. Dual-engine flags removed post‑migration.

### From task_800-899.md (Maintenance & UI)

- TASK-802 Frontend: Hardware Catalog Viewer and Creation Workflow — completed. Hardware tab and creation flow implemented; palette/bulk dialogs updated.
- TASK-803 Frontend: Visualize Port Occupancy in Details Panel — completed. Ports section renders role-based occupancy and effective_status via `/api/ports/summary`.

### From task_900-999.md (Performance & GPON migration)

- TASK-901 Backend: Port-specific PON aggregation and summary endpoint redesign — completed. Per-port summaries authoritative; subscriber counting moved to backend.
- TASK-903 Frontend: Cockpits consume new per-port summaries (dumb client) — completed. Cockpits render from API; client-side BFS removed; polling stabilized.

## ⏸️ Deferred (Archived as Deferred)

Physics Engine roadmap: partially realized (e.g., container bounds force), remainder deferred as a longer-term goal.

- TASK-091 through TASK-106

## 🗑️ Removed (Redundant)

- TASK-033 (Traffic simulation engine placeholder) — removed as redundant. Replaced by the TEv2 workstream (TASK-554 and related).

---

For active items retained from the early roadmap, consult `./BACKLOG.md`.

# COMPLETED_TASKS.md (Archive)

Archives completed tasks moved from `TASK.md`.

- [x] ID: TASK-001
      Title: Backend: Set up FastAPI project structure
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M1 – The Foundation
      Notes: Initialize clean backend scaffold.
      Subtasks:

  - [x] Initialize FastAPI application entrypoint (main module)
  - [x] Configure settings module (env-based)
  - [x] Create initial folder structure (/api, /services, /models, /core)
  - [x] Add minimal dependency list (FastAPI, SQLModel, Uvicorn)
  - [x] Add placeholder health endpoint /health
  - [x] Add README quickstart snippet
  - [x] Verify server starts locally

- [x] ID: TASK-002
      Title: Backend: Define core SQLModel data models
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M1 – The Foundation
      Notes: Device, Link, Interface domain scope only.
      Subtasks:
- [x] Device model (id, name, type, status, properties JSON, parent_container_id nullable)
- [x] Interface model (id, device_id, name, status, capacity)
- [x] Link model (id, a_interface_id, b_interface_id, status, kind, admin_override_status nullable)
- [x] Define enumerations (DeviceType incl. BACKBONE_GATEWAY, POP; Status, LinkType)
- [x] DeviceRole derivation (active | passive | always_online)
- [x] Basic relational integrity (FKs) & indexes (self FK for parent_container_id) – added unique constraints & index; deferred actual FK constraints until persistent DB
- [x] Pydantic response schemas (read/write separation if needed)
- [x] Local test: create & persist sample objects incl. POP with children

- [x] ID: TASK-003
      Title: Frontend: Set up Vue 3 + TypeScript + Vite baseline
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M1 – The Foundation
      Notes: Basic application shell and layout components.
      Subtasks:
- [x] Initialize Vite project (Vue + TS)
- [x] Add Pinia store setup
- [x] Create layout components (AppLayout, Sidebar, Canvas, DetailsPanel) ✅ (AppLayout.vue, Sidebar.vue, TopologyCanvas.vue, DetailsPanel.vue)
- [x] Add router placeholder (if needed) or confirm single-page layout ✅ (Decided single-page + viewMode store switch, no Vue Router yet)
- [x] Add app-level stylesheet & variables ✅ (global theme tokens in styles/theme.css imported in main.ts)

  - [x] Verify dev server runs

  - [x] ID: TASK-004
        Title: Tooling: Backend-to-Frontend type generation pipeline
        Owner: @duly3
        Priority: high
        Status: done
        Created: 2025-09-07
        Milestone: M1 – The Foundation
        Notes: Generate TypeScript interfaces from Pydantic models.
        Subtasks:
  - [x] Select generation approach (pydantic + custom script)

- [x] Implement generation script (Python) outputs to /unoc-frontend-v2/src/types
- [x] Include Device, Interface, Link models
- [x] Add deterministic ordering & formatting
- [x] Add simple verification step (diff check) manual for now
- [x] Add automated diff verification script (compare regenerated file against committed copy)
- [x] Run once and commit generated types

- [x] ID: TASK-005
      Title: Frontend: Three-column layout scaffold
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M1 – The Foundation
      Notes: Implement base layout (palette | canvas | context panel) with responsive sizing.
      Subtasks:
- [x] Define CSS grid/flex structure
- [x] Placeholder components mount correctly
- [x] Ensure minimum width breakpoints
- [x] Basic light theme variables
- [ ] Optional: Basic dark theme variables

- [x] ID: TASK-006
      Title: Frontend: Header navigation (viewer framework)
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M1 – The Foundation
      Notes: Added header with viewer switch (only D3 Topology active for MVP). Persist last mode deferred.
      Subtasks:

  - [x] Header component shell (implemented in root/App.vue)
  - [x] Viewer state key in store (viewMode) (viewModeStore.ts)
  - [x] Active tab styling (tabs reflect current mode)
  - [x] Future tabs placeholders (disabled Metrics tab present)
  - [ ] (Deferred) Persist last selected mode (localStorage)

- [x] ID: TASK-007
      Title: Frontend: Global selection state & highlight styling (basic)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M1 – The Foundation
      Notes: Initial implementation (single & multi via Shift) integrated in canvas.
      Subtasks:

  - [x] Pinia store: selection[] (device/link IDs with type)
  - [x] Single click sets selection
  - [x] Clear on canvas background click
  - [x] Basic highlight (glow/border) style tokens

- [x] ID: TASK-008
      Title: Frontend: Drag & drop device creation mechanics
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M1 – The Foundation
      Notes: Underpins device creation workflow prior to palette logic finalization.
      Subtasks:
- [x] Drag start metadata (device type)
- [x] Canvas drop coordinate normalization
- [x] Detect drop inside container (POP bounds)
- [x] Include parent_container_id in create action if nested
- [x] Pending visual ghost until API returns
- [x] Error rollback (remove ghost, alert placeholder)
- [ ] Finalize palette logic

- [x] ID: TASK-009
      Title: Backend: Container devices & classification
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M1 – The Foundation
      Notes: Added POP & Backbone Gateway types plus validation matrix.
      Subtasks:

  - [x] Add BACKBONE_GATEWAY & POP to DeviceType enum
  - [x] Implement DeviceRole resolver
  - [x] parent_container_id validation rules
  - [x] Query helper: fetch container children
  - [x] Migration / schema update script (if needed) (not required for in-memory)
  - [x] Simple unit tests (POP with two child OLTs)

- [x] ID: TASK-010
      Title: Backend: Device CRUD API endpoints
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M2 – Core Functionality
      Notes: POST, list, get by id, update, delete.
      Subtasks:

  - [x] Define request/response schemas
  - [x] Implement POST /devices
  - [x] Implement GET /devices (collection)
  - [x] Implement GET /devices/{id}
  - [x] Implement PUT /devices/{id}
  - [x] Implement DELETE /devices/{id}
  - [x] Happy-path local tests

- [x] ID: TASK-011
      Title: Frontend: Device Palette component
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M2 – Core Functionality
      Notes: Drag & drop creation aligned to FTTH hierarchy.
      Subtasks:
  - [x] Fetch available device types (temporary static list if backend not ready)
- [x] Implement palette UI grouping headings
- [x] Add draggable attribute & dragstart metadata payload { type }
- [x] Canvas drop listener creates device
- [x] Pending ghost style until created
- [x] Mark container-capable targets (POP) visually (dashed stroke)
- [x] Error feedback on failure (alert placeholder; will migrate to toast TASK-018)

- [x] ID: TASK-012
      Title: Backend: Link CRUD minimal (create & delete)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M2 – Core Functionality
      Notes: Only POST /links and DELETE /links/{id} for initial graph.
      Subtasks:
- [x] Validate interface endpoints for linking
- [x] Implement POST /links
- [x] Implement DELETE /links/{id}
- [x] Basic checks (no duplicate link; endpoint self check; canonical ordering)

- [x] ID: TASK-013
      Title: Frontend: Link creation workflow
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Two-step selection flow for link creation.
      Subtasks:

  - [x] Add context menu trigger on device/interface node
  - [x] Store first endpoint state
  - [x] Select second endpoint & call POST /links
  - [x] Visual success & error handling

- [x] ID: TASK-014
      Title: Frontend: Basic D3 visualization
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Initial device/link rendering, pan/zoom, styling.
      Subtasks:

  - [x] Fetch devices & links (single load)
  - [x] Map to internal node/edge structures (with parent references)
  - [x] Render nodes & edges
  - [x] Render POP container boundary grouping children
  - [x] Distinct style for Backbone Gateway
  - [x] Basic styling & labels
  - [x] Simple pan/zoom support

- [x] ID: TASK-015
      Title: Frontend: Bulk device creation modal
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-07
      Milestone: M2 – Core Functionality
      Notes: Right-click on palette device type opens count input dialog; enables rapid lab topologies. Updated 2025-09-08 to expand validation & UX subtasks.
      Subtasks:
- [x] Context trigger on palette item (right-click)
- [x] Modal shell (title, device type, count field, buttons Create / Cancel)
- [x] Numeric validation (int >=1, max limit configurable e.g. 200, inline error)
- [x] Optional parent assignment selector shown when type ∈ {OLT, AON_SWITCH} & ≥1 POP exists (dropdown of POP ids)
- [x] Random position generator (grid or spiral) with minimal overlap (collision offset)
- [x] Batch API creation loop (sequential, abort on fatal validation error, collect partial successes)
- [x] Error handling: aggregate failures -> toast summary + per-item reason in console
- [x] Progress indicator (count created / total) while running (disable inputs) (simplified spinner via pending toast)
- [x] Summary toast ("N devices created", plus failures if any)
- [x] Undo integration (single bulk undo action groups all created ids)
- [x] ESC / Cancel closes modal (no creations) & resets form
- [x] Accessibility: focus trap, primary button Enter submit, ESC cancel
- [x] Unit test: generator produces positions within viewport bounds
- [x] E2E test stub (playwright) for happy path 5 devices
- [x] Documentation snippet (ARCHITECTURE §9 reference optional) – defer if minor

- [x] ID: TASK-016
      Title: Frontend: Canvas context menu framework
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-07
      Milestone: M2 – Core Functionality
      Notes: Reusable menu for node/link actions (start link, delete later, etc.). Added Playwright spec for open/close (canvas-context-menu.spec.ts).
      Subtasks:

  - [x] Right-click event capture layer
  - [x] Positioning & boundary handling
  - [x] Action dispatch pattern
  - [x] Close on click-away / ESC

- [x] ID: TASK-016A
      Title: Context Menu: Device & multi-select actions (MVP set)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-09
      Milestone: M2 – Core Functionality
      Notes: Implements concrete actions on top of framework.
      Subtasks:
- [x] Delete device(s)
- [x] Start link from primary device (enter link mode)
- [x] Provision single device (if eligible & not provisioned)
- [x] Provision selected subset (multi-select filter eligible)
- [x] Assign POP parent (multi-select with exactly one POP + N children)
- [x] Disable actions with tooltip if not allowed
- [ ] Emit synthetic events for analytics (future)

- [x] ID: TASK-016B
      Title: Context Menu: UX polish & keyboard shortcuts
      Owner: @duly3
      Priority: low
      Status: done
      Created: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Follow-up improvements.
      Subtasks:
- [x] Arrow-key navigation in menu
- [x] Enter activates highlighted
- [x] Persistent subtle fade animation
- [x] Auto-reposition on viewport resize

- [x] ID: TASK-017A
      Title: Frontend: Highlight Multi-Selection (class toggle)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-12
      Completed: 2025-09-12
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Toggled CSS class 'selected' on all selected g.device-node elements via redrawSelection; added :deep() CSS rules in TopologyCanvas.vue for a clear glow highlight; kept data-selected attributes for back-compat. Verified manually and with full frontend test suite.
      Artifacts: unoc-frontend-v2/src/composables/topologyCore/renderHelpers.ts, unoc-frontend-v2/src/components/layout/TopologyCanvas.vue

- [x] ID: TASK-018
      Title: Frontend: Visual feedback & toast system
      Owner: @duly3
      Priority: medium
      Status: in_progress
      Created: 2025-09-07
      Milestone: M2 – Core Functionality
      Notes: Unified success/error transient messaging & pending indicators.
      Subtasks:

      - [x] Toast component & queue store
      - [x] Standard variants (success/error/info)
      - [x] Auto-dismiss & manual close
      - [x] Pending spinner overlay for long actions (provision)

- [x] ID: TASK-019
      Title: Frontend: Multi-select interaction (Ctrl-click)
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Extend selection store to support additive selection (renumbered from reused ID clash).
      Subtasks:

- [x] Detect modifier key (Ctrl/Meta/Shift) on click
- [x] Add/remove element from selection[]
- [x] Visual aggregated highlight style (thicker stroke)
- [x] Display selection count (HUD overlay)

- [x] ID: TASK-019
      Title: Frontend: Canvas interaction polish
      Owner: @duly3
      Priority: low
      Status: done
      Created: 2025-09-07
      Milestone: M2 – Core Functionality
      Notes: Improve usability of panning/zoom and hit targets.
      Subtasks:

      - [x] Constrain zoom min/max

  - [ ] Smooth pan inertia (if trivial)
    - [x] Expand click hit areas for small nodes
    - [x] Debounce resize handling

- [x] ID: TASK-020
      Title: Backend: Provisioning service (context-aware)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Introduced `provision_device` orchestrating dependency checks, IP allocation, defaults.
      Subtasks:

  - [x] Constants extraction (PROVISION_MATRIX, DEVICE_PARENT_POOL_MAP)
  - [x] Dependency validation
  - [x] Management interface creation
  - [x] Default optical attributes assignment
  - [x] Conflict & exhaustion error handling centralization

- [x] ID: TASK-021
      Title: Backend: Lazy IPAM service
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Implemented pool-backed management IP assignment within provisioning flow.
      Subtasks:

  - [x] Base pools constant
  - [x] Address allocation logic
  - [x] Collision avoidance via sequential index

- [x] ID: TASK-022
      Title: Backend: Unified provision endpoint
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Added POST /api/devices/{id}/provision calling service; returns `ProvisionResponse`.
      Subtasks:

  - [x] Endpoint wiring
  - [x] Call provisioning service
  - [x] Return updated device schema

- [x] ID: TASK-023
      Title: (Deprecated placeholder) — skipped / consolidated
      Owner: @duly3
      Priority: low
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Placeholder removed; functionality covered by TASK-020..022.

- [x] ID: TASK-023
      Title: Frontend: Provisioning UI action
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Provision button, badge, toast integration.
      Subtasks:

  - [x] Add button (visible when provisionable)
  - [x] Invoke provision endpoint
  - [x] Update device state on success
  - [x] Show error toast on failure

- [x] ID: TASK-024
      Title: Backend: Define IPAM pool constants & device→pool mapping
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Added `POOL_DEFS`, `POOL_KEY_MAP`; authoritative mapping aligned with ARCHITECTURE §4.1 / §3.11 table.
      Subtasks:

  - [x] Enumerate pool keys & CIDRs
  - [x] Map device types to pool keys
  - [x] Reference docs alignment

- [x] ID: TASK-025
      Title: Backend: Lazy pool creation logic
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Introduced `ensure_pool` with idempotent creation & cursor management; exhaustion raises `POOL_EXHAUSTED`.
      Subtasks:

  - [x] Pool model schema (IPPool)
  - [x] Idempotent allocation helper
  - [x] Cursor increment logic
  - [x] Exhaustion runtime error mapping

- [x] ID: TASK-026
      Title: Tooling: DB reset script & VSCode task
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Provide easy dev database reset and seeded sanity data.
      Subtasks:
- [x] Python script scripts/reset_dev_db.py (drops file, recreates tables)
- [x] Optional seed data flags (--seed minimal)
- [x] VSCode task "db: reset dev file" wiring
- [x] Update README quickstart section
- [x] Add note in TASK-010 about reset usage

- [x] ID: TASK-027
      Title: Testing: Autouse fixture for DB reset
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Ensure each test function gets clean in-memory DB.
      Subtasks:
- [x] conftest.py with autouse fixture sets UNOC_PERSISTENCE=inmemory
- [x] Calls reset_db() before each test
- [x] Remove manual reset calls from tests
- [x] Update docs (testing section)

- [x] ID: TASK-030
      Title: Backend: Status & propagation logic
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-09
      Milestone: M4 – Simulation & Real-time
      Notes: Implemented two-phase status engine. Phase 1 marks provisioned active devices and always_online roles UP (unless admin override=DOWN). Phase 2 adds passive propagation via UP-link BFS from seeds (always_online + provisioned actives) using a snapshot store behind ENABLE_STATUS_PROPAGATION; passive defaults remain UP when disabled. Emitted device.status.changed events on transitions; added unit tests (propagation seeds, BFS reachability, admin override). Coverage raised to ~90%.
      Artifacts: backend/services/status_service.py, backend/services/status_recompute.py, backend/services/status_propagation_store.py, tests/test_status_propagation_phase2.py

- [x] ID: TASK-030B
      Title: Backend: Provision dependency path checks
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Implemented logical & optical upstream path validation with strict vs relaxed modes; added positive & negative tests.
      Artifacts: test_path_validation.py (7 tests), pathfinding classification refactor.

- [x] ID: TASK-031
      Title: Backend: WebSocket delta emitter
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-09
      Milestone: M4 – Simulation & Real-time
      Notes: Implemented event bus emitters with stable envelopes, correlation_id passthrough, backpressure and heartbeat; fanout verified.
      Artifacts: backend/api/endpoints/ws.py, backend/events.py, tests/test_ws_transport.py, tests/test_ws_fanout_and_correlation.py

- [x] ID: TASK-032
      Title: Frontend: WebSocket listener & state updates
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-09
      Milestone: M4 – Simulation & Real-time
      Notes: Implemented realtime event handlers in Pinia; immutable store updates; reconnect handling; unit tests passing.
      Artifacts: unoc-frontend-v2/src/stores/realtimeStores.ts, tests/realtimeStores.spec.ts

- [x] ID: TASK-034A
      Title: Backend: Pathfinding core graph layer
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-08
      Milestone: M4 – Simulation & Real-time
      Notes: Implemented optical/logical graph builders, version store, synthetic relaxed edges, tests.
      Subtasks:

  - [x] build_optical_graph(devices, links)
  - [x] build_logical_graph(devices, links, relaxed)
  - [x] topo_version increment & snapshot struct
  - [x] Unit tests (graph membership & version bump)

- [x] ID: TASK-034B
      Title: Backend: Optical path resolver implementation
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-10
      Milestone: M4 – Simulation & Real-time
      Notes: Implemented attenuation-weighted Dijkstra with deterministic tie-break (attenuation, hops, OLT id, path signature). Returns segment list and total loss; handles no-path sentinel. Ensured enum normalization and graph cache invalidation on topology changes.
      Artifacts: backend/services/optical_path_resolver.py, backend/services/pathfinding.py, tests/test_optical_path_resolver.py

- [x] ID: TASK-035
      Title: Backend: Signal budget computation & classification
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-10
      Milestone: M4 – Simulation & Real-time
      Notes: Added received power and margin computation using optical path resolver; classified into OK/WARNING/CRITICAL/NO_SIGNAL with thresholds (OK ≥6 dB, WARNING 3–<6 dB, CRITICAL 0–<3 dB, NO_SIGNAL when margin <0 or no path). Persisted on Device (signal_power_dbm, signal_margin_db, signal_status) and emitted device.optical.updated. Wired recompute on OLT/ONT optical param edits and link CRUD.
      Artifacts: backend/services/optical_service.py, backend/models.py (SignalStatus, fields), backend/api/schemas.py (fields), tests (optical resolver + WS), tools/gen_ts_types.py (updated types)

- [x] ID: TASK-037
      Title: Backend: Optical model field extensions
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-09
      Milestone: M4 – Simulation & Real-time
      Notes: Added tx_power_dbm, sensitivity_min_dbm, insertion_loss_db to Device; length_km and fiber_type on Link; validations and TS types updated.
      Artifacts: backend/models.py, backend/api/schemas.py, tools/gen_ts_types.py

- [x] ID: TASK-038
      Title: Backend: Optical path & signal engine integration
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-10
      Milestone: M4 – Simulation & Real-time
      Notes: Integrated path resolution, attenuation accumulation, RX power and margin computation, classification, and ONT status gating with ordered events (optical before status).
      Artifacts: backend/services/optical_service.py, backend/services/pathfinding.py, tests (backend/tests/test_optical_recompute_hook.py, backend/tests/test_optical_events_on_link_crud.py)

- [x] ID: TASK-039A
      Title: Frontend: UX Polish for Optical Editing
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-10
      Completed: 2025-09-10
      Milestone: M4 – Simulation & Real-time
      Notes: Added save success toasts, error toasts with backend messages, inline validation, and disabled Save when invalid; stretched tasks for dynamic fiber-type list deferred.
      Artifacts: unoc-frontend-v2/src/components (optical editors), toast store and related tests

- [x] ID: TASK-040
      Title: Frontend: DeviceDetails panel (context-aware)
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-07
      Milestone: M5 – Advanced Features
      Notes: Dynamic section rendering by device type & status.
      Subtasks:

  - [x] Layout skeleton
  - [x] Bind selected device store
  - [x] Show provisioning/action buttons region (basic rename/delete)
  - [x] Show properties list (Basisfelder)

- [x] ID: TASK-041
      Title: Integrate status_service into device responses
      Owner: @duly3
      Priority: medium
      Status: in_progress
      Created: 2025-09-08
      Milestone: M4 – Status & Events
      Notes: Apply evaluate_device_status on read + recompute hook after provisioning.
      Subtasks:

      - [x] Apply evaluate_device_status in device GET endpoints
      - [x] Recompute status after provisioning and on link CRUD
      - [x] Emit device_status_changed events on transitions
      - [x] Unit tests for status transitions (up/down/unknown/admin_override)
      - [x] Docs: API response examples and status matrix (see docs/llm/03_ipam_and_status.md)

- [x] ID: TASK-042
      Title: Event broadcaster hooks
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-08
      Milestone: M4 – Status & Events
      Notes: Implemented event emission (device/link lifecycle), metrics endpoint, topo_version tagging.
      Artifacts: /api/metrics/events, events tests

- [x] ID: TASK-044
      Title: Optional rule_id enrichment on link list
      Owner: @duly3
      Priority: low
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-10
      Milestone: M4 – Status & Events
      Notes: Superseded by on-create classification; rule_id enrichment no longer needed at list time.
      Artifacts: backend/constants/link_types.py (classification on create), tests

- [x] ID: TASK-046
      Title: Strict path dependency validation
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-10
      Milestone: M3 – Provisioning
      Notes: Duplicate of TASK-030B (dependency/path validation already implemented alongside status/simulation works). Marked done to remove duplication.
      Artifacts: ARCHITECTURE §3.4/§18, backend validation tests

- [x] ID: TASK-047
      Title: WebSocket broadcast integration
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-10
      Milestone: M4 – Status & Events
      Notes: Implemented as part of TASK-031 (backend delta emitter) and TASK-032 (frontend WS listener/state updates). This entry consolidates status.
      Artifacts: backend/api/endpoints/ws.py, backend/events.py, unoc-frontend-v2/src/stores/realtimeStores.ts, tests

- [ ] ID: TASK-050
      Title: Backend: Provisioning Core & Device Flags
      Status: done
      Priority: high
      Notes: Add Device.provisioned, admin_override_status, move if0 auto-create to provisioning, POST /api/devices/{id}/provision.
      Subtasks:

  - [x] Model fields added
  - [ ] Migration helper / recreate in-memory (in-memory ok; persistent TBD)
  - [x] Endpoint skeleton (basic implemented in routes)
  - [ ] Tests (provision ok / double provision)
  - [ ] Move if0 auto-create logic fully under provisioning path
  - [ ] Implement admin_override_status field handling

- [ ] ID: TASK-051A
      Title: Backend: Link Classification for Pathfinding
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Replace temporary raw FIBER inclusion with rule-based mapping (optical_segment / routed_p2p etc.) and adjust tests.
      Subtasks:

  - [x] Define LINK_TYPE_RULES mapping
  - [x] Update pathfinding graph construction
  - [x] Remove temporary FIBER inclusion in graphs
  - [x] Update path validation tests to create appropriate classed links
  - [x] Ensure logical vs optical separation

  - [x] ID: TASK-051B
        Title: Maintenance: Legacy VLAN100 cleanup & archival
        Owner: @duly3
        Priority: low
        Status: done
        Created: 2025-09-07
        Milestone: M7 – Maintenance & Cleanup
        Notes: Remove legacy vlan100 tasks; archive scripts under scripts/legacy.
        Subtasks:
    - [x] Remove tasks from .vscode/tasks.json
    - [x] Move scripts to scripts/legacy
    - [x] Add legacy README rationale - [x] Confirm no remaining references in repo
    - [x] Mark task

- [x] ID: TASK-052
      Title: Optional mgmt IP allocation and defaults
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-08
      Milestone: M3 – Provisioning

- [x] ID: TASK-054
      Title: Backend: Metrics snapshot endpoint
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-07
      Milestone: M4 – Simulation & Real-time
      Notes: Reconnect recovery (full device metrics state).
      Subtasks:

  - [ ] GET /api/metrics/snapshot
  - [ ] Include tick_seq & capacities
  - [ ] Optional filtering (future)
  - [ ] Test: snapshot after multiple ticks

- [x] ID: TASK-054b
      Title: Backend: Provisioning audit record (ProvisioningRecord)
      Owner: @duly3
      Priority: low
      Status: done
      Created: 2025-09-08
      Milestone: M4 – Status & Events
      Notes: Persist timestamp, actor, correlation_id, outcome for each provisioning.
      Subtasks:

  - [ ] Model + migration placeholder
  - [ ] Write on successful provision
  - [ ] Expose list/query endpoint (paginated)
  - [ ] Tests (record exists)

- [x] ID: TASK-054c
      Title: Frontend: Parent container indicator in Details Panel
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Show parent_container_id (or fehlend) for selected device; highlight missing when required.
      Subtasks:

  - [x] Add indicator row (Parent)
  - [x] Warning style when required but missing
  - [ ] Optional: clickable jump-to parent (follow-up)

- [x] ID: TASK-055
      Title: Frontend: Metrics store & WS handler
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Completed: 2025-09-09
      Milestone: M4 – Simulation & Real-time
      Notes: Implemented Pinia metrics store and deviceMetricsUpdated handling with snapshot apply logic and tests.
      Artifacts: unoc-frontend-v2/src/stores/metricsStore.ts, tests

- [x] ID: TASK-055
      Title: Harmonize parent validation (EDGE_ROUTER standalone)
      Completed: 2025-09-09
      Milestone: M3 – Provisioning
      Notes: Backend validation enforces POP parent only for OLT/AON_SWITCH; EDGE/CORE must not have parent; passives optional; ONT/CPE not parented by POP. Updated tests and docs.

- [x] ID: TASK-056
      Title: Link rule L6A (AON_SWITCH↔ROUTER uplink)
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Added classification rule L6A (access_uplink) permitting AON Switch ↔ Router links; updated tests (`test_link_classification_positive.py`). Architecture §3.12 bumped (r6) to document rule.
      Artifacts: backend/constants/link_types.py, tests/test_link_classification_positive.py

- [x] ID: TASK-057
      Title: Link rule L6B (OLT↔ROUTER uplink)
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Added classification rule L6B (OLT↔Router) using access_uplink class; updated tests & architecture (r7). Shares non-optical semantics with L6A (no attenuation impact).
      Artifacts: backend/constants/link_types.py, tests/test_link_classification_positive.py, ARCHITECTURE.md (r7)

- [x] ID: TASK-061
      Title: Backend: Config endpoint consolidation
      Status: done
      Milestone: M5 – Ops Readiness
      Notes: Consolidated configuration into a unified /api/config endpoint with flags and metadata.

- [x] ID: TASK-075
      Title: Frontend: D3/Vue boundary refactor (mount cockpit components)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Replace text/primitive nodes with Vue cockpit components inside <g>.
      Subtasks:

  - [ ] Node wrapper <g> retains transform
  - [ ] Cockpit props minimal (id only)
  - [ ] Migration path for existing labels
  - [ ] Smoke test 500 nodes

- [x] ID: TASK-077A
      Title: Full-stack: Link Metrics Snapshot
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-09
      Milestone: M4 – Simulation & Real-time
      Notes: Extend /api/metrics/snapshot to include link metrics and wire to frontend store.
      Subtasks:

      - [x] Backend: include links dict in snapshot payload
      - [x] Backend: service get_snapshot() export _last_links
      - [x] Backend: tests for links snapshot correctness
      - [x] Frontend: apply links snapshot to linkMetricsStore
      - [x] Frontend: tests for snapshot application

- [x] ID: TASK-081
      Title: Frontend: Tooltip Engine (global overlay + D3 hover integration)
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-10
      Completed: 2025-09-10
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Added Pinia tooltip store with hysteresis (show 80ms, hide 120ms), global Tooltip.vue mounted in App.vue, and D3 wiring for links and devices (mouseenter/move/leave). Unit tests cover store delays and component positioning.

- [ ] ID: TASK-078
      Title: Frontend: Signal cockpit elements (ONT/CPE)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-07
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Received power, margin chip, status ring.
      Subtasks:

  - [ ] Signal badge component
  - [ ] Color + icon dual encoding
  - [ ] Placeholder when NO_SIGNAL
  - [ ] Tooltip path breakdown integration

- [x] ID: TASK-079
      Title: Frontend: Port matrix (OLT / AON Switch)
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-07
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Column layout with overflow handling.
      Subtasks:

  - [ ] Grid layout (≤ PORT_MATRIX_MAX_VISIBLE)
  - [ ] Overflow scroll/tooltip
  - [ ] Occupancy color buckets
  - [ ] Large port virtualization hook (future stub)

- [x] ID: TASK-080
      Title: Frontend: Passive device cockpit
      Owner: @duly3
      Priority: low
      Status: done
      Created: 2025-09-07
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Minimal design with insertion loss.
      Subtasks:

  - [ ] Loss formatting (-0.5 dB)
  - [ ] Overflow safe text
  - [ ] Visual distinction for types
  - [ ] Edge case negative loss highlight

- [x] ID: TASK-081
      Title: Frontend: Tooltip engine (links & devices)
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-07
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Global host + hysteresis.
      Subtasks:

  - [ ] Global component mount
  - [ ] rAF-throttled position update
  - [ ] Delay management (enter/leave)
  - [ ] Accessibility (focus triggers)

- [x] ID: TASK-081A
      Title: Bugfix: Remove native title tooltips from nodes
      Owner: @duly3
      Priority: critical
      Status: done
      Created: 2025-09-12
      Completed: 2025-09-12
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Removed all native HTML/SVG title tooltips from node rendering to avoid conflicts with the global Tooltip.vue overlay (duplicate or stuck tooltips). Verified via manual hover checks and full frontend test suite (vitest) passing. Build produced only d3.event export warnings (known, non-blocking).
      Subtasks: - [x] Remove D3-appended <title> from node groups in draw.ts - [x] Ensure all cockpit components contain no title attributes - [x] Verify: only custom Tooltip.vue appears on hover; no native tooltip; no stuck empty tooltip boxes

- [x] ID: TASK-081A1
      Title: Bugfix: Fix Ghost Tooltip on Page Load and Pan
      Owner: @duly3
      Priority: critical
      Status: done
      Created: 2025-09-12
      Completed: 2025-09-12
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: On refresh, an empty black tooltip box appears and may stick after panning. Root cause: tooltipStore not initialized/reset cleanly and timers not canceled. Ensure default hidden state, add robust reset(), and hide/reset on app init and pan/zoom start.
      Subtasks: - [x] tooltipStore.ts: default isVisible=false and sane defaults for content/x/y (nullable) - [x] tooltipStore.ts: add reset() to restore all state and cancel pending timers - [x] Tooltip.vue: render guard on isVisible (no DOM when hidden) - [x] App init: call tooltip.reset() on mounted (App.vue) - [x] Canvas interactions: call tooltip.hide()/reset() on pan/zoom start and during drag - [x] Tests: ensure store timing behavior stays green - [x] Verify manually: no ghost on load; hover→pan hides; no stuck boxes on canvas

- [x] ID: TASK-081B
      Title: Bugfix: Fix Ghost Tooltip on Page Load and Pan
      Owner: @duly3
      Priority: critical
      Status: done
      Created: 2025-09-12
      Completed: 2025-09-12
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Hardened tooltipStore with null content default, reset(), defensive timers; Tooltip.vue render guard; reset on App mount; hide on zoom/drag start. Manual verification and tests green.
      Artifacts: unoc-frontend-v2/src/stores/tooltipStore.ts, unoc-frontend-v2/src/components/ui/Tooltip.vue, unoc-frontend-v2/src/composables/useTopologyCanvasCore.ts, unoc-frontend-v2/src/composables/topologyCore/drag.ts

- [x] ID: TASK-101
      Title: Frontend: Node drag reposition & layout persistence
      Owner: @duly3
      Priority: high
      Status: in_progress
      Created: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Implements manual layout anchoring for topology; groundwork for later force layout.
      Subtasks: - [x] Pointer drag single node - [x] Multi-selection drag propagation - [x] Differential DOM updates (no full redraw) - [x] Debounced batched PATCH /api/layout/positions - [x] Snapshot GET on load - [x] Undo/Redo (Ctrl+Z / Ctrl+Y) - [x] Offline queue retry (localStorage) - [x] Visual pin styling - [x] Force auto-layout (unanchored only) button

- [ ] ID: TASK-111
      Title: Backend: Soft ONT dependency mode
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-08
      Milestone: M3 – Provisioning
      Notes: Allow provisioning ONT/Business ONT without reachable OLT path when STRICT_ONT_DEPENDENCY=0 emitting warning event.
      Subtasks:

  - [x] Flag evaluation (STRICT_ONT_DEPENDENCY false path)
  - [x] Warning event device.provision.warning (reason=missing_olt_path)
  - [x] Tests (strict vs soft)
  - [x] Docs update (ARCHITECTURE §3.11 & §3.4)

- [x] ID: TASK-103
      Title: Frontend: Quick Action Mini Toolbar
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-08
      Milestone: M2 – Core Functionality
      Notes: Floating toolbar (Undo, Redo, Link Tool, Auto Layout) with state indicators; persistence deferred.
      Subtasks: - [x] Design compact button group - [x] Integrate actions (force layout, undo, redo, link toggle) - [x] Live enable/disable states - [x] Basic styling & hover feedback - [ ] Persistence of collapsed state (deferred)

- [x] ID: TASK-141D
      Title: Bugfix: Link Tooltip shows undefined / Util 0%
      Owner: @duly3
      Priority: high
      Status: done
      Completed: 2025-09-13
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Use endpoint device names (fallback to ids) and robust metrics fallback (— when missing). Also migrated D3 handlers to event args (no d3.event). Verified in UI; vitest suite green.

- [x] ID: TASK-141E
      Title: Link Details: Live Utilization Fields
      Owner: @duly3
      Priority: high
      Status: done
      Completed: 2025-09-13
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Show combined/utilization %, bps (and directional where available) in the Link Details panel; hydrate from linkMetricsStore and update reactively.

- [x] ID: TASK-141F
      Title: Link Rendering: Status Color Precedence
      Owner: @duly3
      Priority: medium
      Status: done
      Completed: 2025-09-13
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Apply hierarchy: any endpoint DOWN → red; unprovisioned → grey; else color by utilization scale.

- [x] ID: TASK-141G
      Title: Link Animation: rAF-based Flow by Util/Traffic
      Owner: @duly3
      Priority: medium
      Status: done
      Completed: 2025-09-13
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Notes: Replace rudimentary dash transitions with requestAnimationFrame-driven flow. Speed/thickness/color map to utilization/traffic; zero traffic = solid green, no animation.

- [x] ID: TASK-200
      Title: Ring Protection: Feature flags & LinkStatus.BLOCKING enum
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-08
      Completed: 2025-09-09
      Milestone: M4 – Simulation & Real-time
      Notes: Added ENABLE_RING_PROTECTION and related flags; extended Status enum with BLOCKING. Docs follow-up pending for §19.
      Artifacts: backend/constants/config.py, backend/models.py (Status update), tests for enum wiring

- [x] ID: TASK-216
      Title: Frontend Test Fix devicePalette.types.spec (path ESM import)
      Completed: 2025-09-09
      Milestone: M2 – Core Functionality
      Notes: Switched to Vite `?raw` import and added TS shim to avoid Node ESM fs/path issues in Vitest.

- [x] ID: TASK-217
      Title: ESLint Cleanup IpamTab.vue
      Completed: 2025-09-09
      Milestone: M2 – Core Functionality
      Notes: Removed unused code and corrected WS path to /api/ws; cleaned up types and error handling.

- [x] ID: TASK-218
      Title: Harmonize UTILIZATION_BUCKETS with Architecture
      Completed: 2025-09-09
      Milestone: M4 – Status & Events
      Notes: Buckets set to [50,70,90,100] and tests adjusted accordingly.

- [ ] ID: TASK-401
      Title: Backend: Tariff Data Model
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-10
      Milestone: M5 – Advanced Features & Polish
      Notes: Create Tariff model and reference on Device.
      Subtasks:

  - [x] New Tariff model (models.py): { id, name, max_up_mbps, max_down_mbps }
  - [x] Add Device.tariff_id (nullable FK → Tariff)
  - [x] Pydantic schemas & validation (>= 0 values)
  - [x] Migration note (in-memory now; future migration TBD)
  - [x] Tests: model validation and default behaviors

- [ ] ID: TASK-402
      Title: Backend: Tariff CRUD API
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-10
      Milestone: M5 – Advanced Features & Polish
      Notes: Manage tariff catalog via REST. Implemented alongside TASK-401 (see COMPLETED_TASKS: TASK-401 combines model + CRUD).
      Subtasks:

  - [x] Endpoints: GET/POST/PUT/DELETE /api/tariffs
  - [x] List & filter (by name)
  - [x] Input validation & error codes (duplicate name → 409)
  - [x] Tests for CRUD paths and errors

- [x] ID: TASK-403
      Title: Backend: Assign Tariff to Device
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-10
      Milestone: M5 – Advanced Features & Polish
      Notes: Allow assigning tariff_id via device update.
      Subtasks:

  - [x] Extend PUT /api/devices/{id} to accept tariff_id
  - [x] Validate tariff existence; allow null to unassign
  - [x] Emit device.updated event including tariff_id
  - [x] Tests for happy path and invalid id

- [ ] ID: TASK-405
      Title: Frontend: Tariff Management UI
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-10
      Milestone: M5 – Advanced Features & Polish
      Notes: Add Tariffs tab for viewing/creating/editing tariffs.
      Subtasks:

  - [x] New view/tab "Tariffs" with list + form
  - [x] Integrate with /api/tariffs CRUD
  - [x] Validation and toasts; optimistic updates
  - [x] Tests: store/actions and component basics

- [x] ID: TASK-405A
      Title: Frontend: Tariff Management UI (parent)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-11
      Completed: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: Parent for Tariffs UI; completed with TASK-405 and TASK-406 children.
      Subtasks: - [x] TASK-405 (child) - [x] TASK-406 (child)

- [x] ID: TASK-406
      Title: Frontend: Tariff Assignment in Device DetailsPanel (leaf devices)
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-11
      Completed: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: Tariff dropdown for ONT/Business ONT/AON CPE; persisted via PUT /api/devices/{id} with tariff_id; tests included.
      Artifacts: unoc-frontend-v2/src/components, unoc-frontend-v2/src/stores/tariffsStore.ts

- [x] ID: TASK-407
      Title: Intelligent Default Tariff System
      Milestone: M6 – Commercial Basics
      Status: done
      Notes: Added `Tariff.technology` enum (GPON/AON), idempotent default seeding, and deterministic defaults during device creation (ONT/BUSINESS_ONT → GPON, AON_CPE → AON). Frontend filters tariff dropdown by technology. Backend tests cover seeding and assignment.

- [x] ID: TASK-513
      Title: Backend: Make IPAM Seeding Idempotent
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-10
      Completed: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: Refactored ensure_ipam_defaults to no-op on existing VRFs/Prefixes; allows repeated calls without UNIQUE errors.
      Subtasks: - [x] Check-exist then insert for VRFs (by name) and Prefixes (by vrf_id+prefix) - [x] Preserve custom test prefixes; only backfill descriptions when empty - [x] Remove manual DB resets from tests where used as seeding workaround - [x] Verify full backend suite passes on repeated runs

- [x] ID: TASK-514
      Title: Critical Fix: Enforce Global IP Address Uniqueness (VRF-scoped) & Provisioning Audit Records
      Owner: @duly3
      Priority: critical
      Status: done
      Created: 2025-09-11
      Completed: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: Added VRF-scoped uniqueness constraint for InterfaceAddress.ip, updated provisioning to retry on conflicts, and persisted ProvisioningRecord audit entries on IP assignments.
      Subtasks: - [x] Model: UniqueConstraint (vrf_id, ip) on InterfaceAddress - [x] Model: ProvisioningRecord audit table - [x] Service: VRF-aware allocation & retry - [x] Service: Create ProvisioningRecord on success - [x] Tests: uniqueness, cross-VRF reuse, audit logging - [x] Refactor fixtures to avoid overlapping prefixes - [x] ID: TASK-532
      Title: Backend: Implement MAC Learning and Forwarding Logic
      Milestone: M9 – Foundational Network Emulation
      Notes: Implemented `L2_service.process_frame` with MAC learning, unicast forwarding, and controlled flooding; tests added.

- [x] ID: TASK-542
      Title: Backend: Implement L3 Forwarding Decision Logic
      Priority: high
      Status: done
      Milestone: M9 – Foundational Network Emulation
      Notes: Implement service function that performs longest-prefix match in device's default VRF, resolves next-hop via Neighbor table, and returns a structured forwarding decision.

- [x] ID: TASK-554
      Title: Backend: Generate and forward tariff-based traffic flows
      Priority: high
      Status: done
      Completed: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: Refactored the traffic engine to produce asymmetric, tariff-driven flows per tick, forward upstream via L2/L3, aggregate per-device/link, and emit utilization events; folded metrics_service behavior into the engine.
      Subtasks: - [x] Generate upstream/downstream within tariff bounds per online leaf; forward upstream via forwarding_service - [x] Aggregation reflects resolved upstream paths across devices/links - [x] Emit deviceMetricsUpdated and linkMetricsUpdated with capacity-based utilization - [x] Tests for generation ranges, forwarding, and aggregation; existing suite remains green

- [x] ID: TASK-554A
      Title: Tests: Comprehensive Validation for TrafficEngineV2
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-11
      Completed: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: Dedicated test suite for TrafficEngineV2 covering tariff-based generation, aggregation across devices and links, congestion detection with hysteresis, and snapshot endpoint correctness (including links). Gating removed in TASK-556; tests now part of main suite.
      Subtasks: - [x] Tariff-based generation bounds and asymmetry - [x] Multi-hop device/link aggregation - [x] Congestion detected/cleared with hysteresis - [x] Snapshot endpoint returns v2 data with links

- [ ] ID: TASK-555 (Status: Unknown)
      Title: Backend: Implement Congestion Detection and Events
      Owner: @duly3
      Priority: high
      Status: active
      Created: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: After per-tick aggregation, detect when devices/links exceed effective capacity and emit detected/cleared events with overload percentage; add unit tests.
      Subtasks: - [ ] Extend TrafficEngine to maintain congestion state per device/link - [ ] Emit device.congestion.detected/cleared and link.congestion.detected/cleared - [ ] Unit tests for detected, cleared, and below-capacity paths

- [x] ID: TASK-556
      Title: Refactor: Remove Legacy TrafficSimulationEngine
      Owner: @duly3
      Priority: high
      Status: done
      Created: 2025-09-11
      Completed: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: Removed legacy TrafficSimulationEngine, dropped TRAFFIC_V2 flag, set TariffTrafficRunner as sole ENGINE_SINGLETON, ungated v2 tests, and cleaned dead code.
      Subtasks: - [x] Tombstone legacy_engine.py and remove references (physical file removal pending) - [x] Remove TRAFFIC_V2 flag usages - [x] Make v2 the only engine in facade - [x] Ungate v2 tests - [x] Lint/size/tests all green

- [x] ID: TASK-561
      Title: Fix & Enhance: Context-Aware Physical Medium & Link Defaults (Phase-out legacy fiber_type)
      Owner: @duly3
      Priority: high
      Status: done
      Completed: 2025-09-13
      Milestone: M8 – Optical & Physical Medium Cleanup
      Notes: Backend migrated attenuation and link handling to PhysicalMedium (no more persisted fiber_type), added deterministic defaults and on-demand seeding with safe fallback; updated debug snapshot to include physical_medium_id. Frontend removed legacy fiber_type UI and store/types, updated Link Details to edit only length_km and physical_medium_id, and refactored tests. Verified: backend 191 tests passing, frontend vitest suite passing.
      Artifacts: backend/services/optical_path_resolver.py, backend/models.py, backend/api/schemas.py, unoc-frontend-v2/src/components/layout/DetailsPanel.vue

- [x] ID: TASK-581
      Title: Frontend: Display VRF and Prefix in DetailsPanel
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-11
      Milestone: M9 – Foundational Network Emulation
      Notes: Surface device default VRF and interface address prefix strings in the DetailsPanel Interfaces tab.
      Subtasks: - [x] Backend: Add device_default_vrf_name to DeviceOut and prefix_string to interface addresses API - [x] Backend: Enrich GET /api/devices and /api/interfaces/{id}/addresses - [x] Frontend: Render VRF name and address prefix strings in Interfaces tab - [x] Types: Regenerate TS types - [x] Tests: Extend frontend unit test and backend API tests

- [x] ID: TASK-600
      Title: Refactor: Resolve Deprecation Warnings in Backend
      Owner: @duly3
      Priority: medium
      Status: done
      Created: 2025-09-12
      Completed: 2025-09-12
      Milestone: M7 – Maintenance & Cleanup
      Notes: Completed refactor: migrated FastAPI lifecycle to lifespan in `backend/main.py` (with early broadcaster wiring), updated Pydantic usage (replaced `copy()` with `model_copy()` and removed legacy Config), and modernized SQLModel queries to `session.exec(select(...))`. Verified via CI: ruff clean and all tests passing. See commit for details touching `backend/main.py`, `backend/models.py`, and WebSocket tests.
      Subtasks: - [x] Migrate FastAPI lifecycle to lifespan context manager in backend/main.py - [x] Replace class-based Config in Pydantic models with model_config = ConfigDict(...) - [x] Replace BaseModel.copy(...) with model_copy(...) - [x] Replace session.query(...) with session.exec(...)

- [x] ID: TASK-602 — Fix Full Simulation Causal Chain (Device → Link → Traffic) - Status: done - Priority: critical - Milestone: M11 – Reliability & Observability - Owner: Backend Platform - Summary: Repair the broken causal chain so that device effective status propagates to link effective status and is strictly enforced by the traffic engine. Ensure leaves only generate when effectively UP, aggregation only counts UP devices/links along resolved paths, and link metrics are zeroed when links become inactive.

- [x] ID: TASK-603 — Refactor: Finalize "Strict by Default" & Remove Feature Flags - Status: done - Priority: high - Milestone: M7 – Maintenance & Cleanup - Owner: Platform (Backend) - Summary: Perform a Flag Amnesty to remove temporary/experimental feature flags now that the causal chain and provisioning logic are correct and stable. Make strict behavior the default and only behavior: status propagation (including DEGRADED for active devices) is always on; provisioning is always path-aware and strict. Delete zombie code for relaxed/disabled paths and refactor tests to run green with the unified defaults.

- [x] ID: TASK-700
      Title: Debug Viewer: Full Snapshot (dev-only) and UI Tab
      Owner: @duly3
      Priority: medium
      Status: done
      Completed: 2025-09-14
      Milestone: M7 – Maintenance & Cleanup
      Notes: Implemented GET /api/debug/full-snapshot (gated by UNOC_DEV_FEATURES) with sections filter, pretty, and caps. Snapshot now includes devices, interfaces, addresses, links, VRFs, prefixes, routes, MAC tables, metrics_v2, tariffs, and enriched optical (per-ONT metrics and resolved path). Frontend dev-only Debug tab renders raw JSON with Refresh. Added backend tests for gating, sections filtering, and content.

- [x] ID: TASK-701 — Bugfix: Make Debug Tab Visible in UI (re-activating) - Status: done - Priority: critical - Milestone: M11 – Developer Experience & Observability - Owner: Frontend Platform - Summary: Ensure the developer Debug tab is visible and functional in the main navigation for dev builds to unblock diagnostics. Temporarily remove gating conditions so the button and page render reliably; keep wiring through `viewModeStore` to switch to the `debug` view and render `DebugPage`.

- [x] ID: TASK-801
      Title: Backend: Implement Port Management Foundations
      Completed: 2025-09-14
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Implemented the backend foundations for port management. Extended `PortProfile` and `Interface` models with `PortRole` enum and `max_subscribers` for PON capacity. Created an idempotent seeding service (`ensure_default_hardware_models`) for default OLT, AON, and Router models. Implemented a flag-gated (`AUTO_ASSIGN_DEFAULT_HARDWARE`) auto-assignment of these default models upon device creation. Added new API endpoints `GET /ports/summary/{device_id}` and `GET /ports/ont-list/{device_id}` to provide port occupancy data to the frontend.
      Artifacts: backend/models.py, backend/services/seed_service.py, backend/api/endpoints/devices.py, backend/api/endpoints/ports.py

- [x] ID: TASK-805
      Title: Backend: Correct Port Occupancy Calculation by Role
      Owner: @duly3
      Priority: high
      Status: done
      Completed: 2025-09-14
      Milestone: M9 – Foundational Network Emulation
      Notes: Rewrote GET /ports/summary used counts to reflect real occupancy. ACCESS/UPLINK now count interfaces that are endpoints of links; MANAGEMENT reports used=1 when mgmt0 exists; PON counts provisioned ONTs whose resolved optical path terminates at the OLT. Preserved response shape and added legacy MGMT alias handling. Full backend suite green (210/210). See also the brief API box in 05 (UI model).

- [x] ID: TASK-806
      Title: Frontend: Implement Intelligent, Role-Based Interface Selection for Link Creation
      Owner: @duly3
      Priority: high
      Status: done
      Completed: 2025-09-14
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Refactored the frontend link creation workflow to be intelligent and role-aware. The `linksStore` now implements a sophisticated, prioritized selection logic to automatically choose the most appropriate available interfaces (e.g., preferring unused uplink ports) when a user creates a link. Proactively fixed a latent bug by aligning the client-side link ID generation with the backend's canonical format, preventing future synchronization issues. This completes the core logic for binding links to correct, role-specific ports.
      Artifacts: unoc-frontend-v2/src/stores/linksStore.ts

- [x] ID: TASK-807
      Title: Frontend: Implement Link Creation Modal with Interface Override
      Completed: 2025-09-14
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Completed the link creation workflow by implementing a confirmation modal. After the intelligent interface selection logic pre-selects the source and target ports, a modal now appears, allowing the user to confirm or override the choices from a filtered list of valid, available interfaces. The link is only created after user confirmation, using the final selected interface IDs. This provides a robust and user-friendly workflow for creating correctly configured links.
      Artifacts: unoc-frontend-v2/src/stores/linksStore.ts, unoc-frontend-v2/src/components/layout/TopologyCanvas.vue

- [x] ID: TASK-809
      Title: End-to-End Fix: Stabilize Device Lifecycle, Link Creation, and Status Propagation
      Completed: 2025-09-15
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Performed a comprehensive, end-to-end stabilization of the core device lifecycle. Fixed a critical "provisioning deadlock" by making the provisioning of core routers idempotent and decoupling interface creation from the provisioning step. Resolved a fundamental bug in the `optical_path_resolver` that prevented ONTs from coming UP by correctly mapping link endpoints to their parent devices. Addressed multiple data inconsistencies, including ensuring the `backbone_gateway` is seeded with a full hardware model and normalizing the serialization of `admin_status` enums for the frontend. The entire workflow, from hardware-aware device creation to intelligent, role-based link creation and correct status propagation, is now robust and functional.
      Artifacts: backend/services/provisioning_service.py, backend/services/optical_path_resolver.py, backend/services/seed_service.py, backend/api/endpoints/devices.py, unoc-frontend-v2/src/stores/linksStore.ts

- [x] ID: TASK-810
      Title: Bugfix: Restore and Enhance Link Traffic Animations
      Completed: 2025-09-15
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Fixed a logical regression where link traffic animations were only displayed for links in an "overload" state. The animation logic was decoupled from the overload status. Now, any link with positive utilization (> 0%) and an effective status of 'UP' will display a flowing animation, providing a much more intuitive and accurate visualization of traffic flow across the entire network, not just on leaf links. The link color continues to independently represent the link's state (e.g., red for overload).
      Artifacts: unoc-frontend-v2/src/composables/topologyCore/draw.ts

- [x] ID: TASK-811
      Title: Frontend: Implement High-Fidelity "Digital Display" BackboneGatewayCockpit
      Completed: 2025-09-15
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Implemented the first high-fidelity "Smart SVG Cockpit" for the BACKBONE_GATEWAY. The new component is significantly larger and features a "digital display" aesthetic with a multi-row layout showing key network-wide metrics like Status, Upstream/Downstream Throughput, and total Online Subscribers. The design includes a status-aware colored frame and header LEDs, setting the visual standard for all future cockpit components.
      Artifacts: unoc-frontend-v2/src/components/cockpits/BackboneGatewayCockpit.vue, unoc-frontend-v2/src/composables/topologyCore/draw.ts

- [x] ID: TASK-812
      Title: Bugfix: Ensure Correct "Downstream Degrade" Propagation
      Completed: 2025-09-15
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Fixed a critical bug where forcing the BACKBONE_GATEWAY down did not correctly propagate a DEGRADED status to all downstream devices. The status propagation logic was refactored to correctly prioritize the BACKBONE_GATEWAY as the primary reachability anchor. Additionally, the traffic engine was hardened to ensure that leaf devices (ONTs/CPEs) behind a downed anchor cease all traffic generation, resulting in a consistent and realistic network failure simulation.
      Artifacts: backend/services/status_recompute.py, backend/services/status_service.py, backend/services/v2_engine.py

- [x] ID: TASK-813
      Title: Containers Phase 0: Implement Feature Flags and Design Artifacts
      Completed: 2025-09-15
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Completed the foundational preparatory work for the Hierarchical Container Nodes feature. Initially added `CONTAINERS_ENABLED` and `CONTAINER_PROXY_LINKING` flags and exposed them via `/api/config`. As of 2025-09-16, `CONTAINERS_ENABLED` has been permanently enabled and removed (containers are always on); `CONTAINER_PROXY_LINKING` remains as a UX flag. Created the `container-layouts.json` design document with slot presets for POP and CORE_SITE, and an ADR documenting the "true endpoint" link rendering strategy.
      Artifacts: backend/core/config.py, backend/api/endpoints/config.py, unoc-frontend-v2/src/stores/configStore.ts, docs/container-layouts.json, docs/ADR-008-containers-link-rendering.md

- [x] ID: TASK-814
      Title: Containers Phase 1: Implement Backend Enablement for CORE_SITE
      Completed: 2025-09-16
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Completed the minimal backend enablement for hierarchical containers. Added `CORE_SITE` to the `DeviceType` enum and updated the role derivation logic to classify it as a `passive_container`, identical to `POP`. The core parent-child validation logic was updated to recognize `CORE_SITE` as a valid container for specific device types. Added a new test suite to verify the creation of `CORE_SITE` containers and the ability to move devices in and out of them via API PATCH requests, ensuring the backend is fully prepared for the frontend implementation.
      Artifacts: backend/models.py, backend/utils.py, backend/tests/test_core_site_container.py

- [x] ID: TASK-815
      Title: Containers Phase 2: Implement Frontend Rendering and Snapping
      Completed: 2025-09-16
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Completed a major visual and interactive upgrade by implementing hierarchical container rendering. New `POPCockpit` and `CoreSiteCockpit` components now render as large container nodes. The rendering engine was refactored to draw child devices visually nested within their parent containers, positioned at predefined slot anchors. A full drag-and-snap workflow was implemented, including slot highlighting on hover and updating the device's `parent_container_id` via API PATCH on drop. The legacy dashed lines for parent-child relationships have been completely removed.
      Artifacts: unoc-frontend-v2/src/composables/topologyCore/draw.ts, unoc-frontend-v2/src/composables/topologyCore/drag.ts, unoc-frontend-v2/src/composables/topologyCore/drop.ts, unoc-frontend-v2/src/components/cockpits/containers/

- [x] ID: TASK-816
      Title: Containers Phase 3: Implement Physics Boundaries
      Completed: 2025-09-16
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Enhanced the D3 physics simulation by implementing a custom force (`containerBoundsForce`) to enforce container boundaries. Child nodes are now physically constrained within the visual bounds of their parent container (POP or CORE_SITE). The force clamps child coordinates, dampens velocity to prevent bouncing, and applies a weak attraction towards the assigned slot anchor without overriding user-pinned positions. This makes the layout significantly more stable and intuitive, especially when moving containers or during dynamic layout adjustments.
      Artifacts: unoc-frontend-v2/src/composables/topologyCore/containerBoundsForce.ts, unoc-frontend-v2/src/composables/topologyCore/simulation.ts

- [x] ID: TASK-817
      Title: Containers Phase 4: Implement Container-Proxy Linking
      Completed: 2025-09-16
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Implemented the "Container-Proxy Linking" feature to significantly improve the link creation user experience. When a user selects a container (POP or CORE_SITE) as the target for a new link, a modal dialog (`LinkProxyModal`) now opens. This modal presents a filtered list of valid, compatible child devices within that container. The final link is then correctly created between the original source device and the user-selected target device, ensuring topological accuracy while providing an intuitive workflow. Direct linking to container devices is explicitly blocked.
      Artifacts: unoc-frontend-v2/src/composables/topologyCore/handlers.ts, unoc-frontend-v2/src/components/modals/LinkProxyModal.vue, unoc-frontend-v2/src/stores/linksStore.ts

- [x] ID: TASK-818
      Title: Containers Phase 5: Implement Aggregated Metrics and Status
      Completed: 2025-09-16
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Enhanced the container cockpits (`POPCockpit` and `CoreSiteCockpit`) to function as "super-cockpits" by displaying live, aggregated metrics. Each container now shows its slot occupancy (e.g., "Slots: 4 / 6"), the total traffic throughput of all its child devices, and a summary health status badge (UP/DEGRADED/DOWN) derived from the status of its children. The data is calculated efficiently using reactive selectors from the Pinia stores, providing a high-level, at-a-glance overview of a site's health and load.
      Artifacts: unoc-frontend-v2/src/components/cockpits/containers/POPCockpit.vue, unoc-frontend-v2/src/components/cockpits/containers/CoreSiteCockpit.vue

- [x] ID: TASK-819
      Title: Frontend: Implement High-Fidelity "Digital Display" RouterCockpit
      Completed: 2025-09-16
      Milestone: M8 – Smart SVG Cockpits & Visualization
      \n+#### Cross-links for Onboarding Q1 topics

- Asynchronous recompute & coalescer: `backend/api/endpoints/devices.py` (coalesced recompute scheduling), `backend/tests/conftest.py` (coalescer quiesce), `backend/db.py` (DDL lock guards).
- Effective status & traversal: `backend/services/status_service.py` (evaluate_device_status/evaluate_link_status/is_link_passable), `backend/services/status_recompute.py`, `backend/services/status_propagation_store.py`.
- GPON ODF-as-Aggregator rules: `backend/api/endpoints/links.py` (POP disallow, ODF↔ODF cascade block, OLT/ONT pairing guards, ONT↔passive BFS in ODF‑headed path).
- Traffic Engine V2 generation/aggregation & PON segments: `backend/services/traffic/v2_engine.py` (+ `v2_aggregation.py`).
- Port roles, media & defaults: `backend/models.py` (PortRole/PortProfile), `backend/api/endpoints/ports.py`, `backend/services/links_service.py`, `backend/link_rules.py`.
- Containers & pinning: `unoc-frontend-v2/src/composables/topologyCore/containerBoundsForce.ts`, `unoc-frontend-v2/src/composables/topologyCore/simulation.ts`, `unoc-frontend-v2/src/stores/layoutStore.ts`.
  Commit: <final-git-sha>
  Notes: Refactored the `RouterCockpit.vue` to the new high-fidelity "Digital Display" standard, consistent with the `BackboneGatewayCockpit`. The new, larger cockpit is now mounted for both `CORE_ROUTER` and `EDGE_ROUTER` devices. It features a status-aware frame, header with status LEDs, and a multi-row layout displaying key metrics: Status, Upstream/Downstream Throughput, and Total Capacity. The associated unit test was updated to validate the new data-driven presentation.
  Artifacts: unoc-frontend-v2/src/components/cockpits/RouterCockpit.vue, unoc-frontend-v2/src/tests/cockpits/routerCockpit.spec.ts

#### Cross-links for Onboarding Q3 topics

- Leaf generation gating and DEGRADED vs DOWN: `backend/services/traffic/v2_engine.py` (leaf gating in `run_tick`), `backend/services/status_service.py` (status evaluation, `is_link_passable`), `backend/services/traffic/v2_aggregation.py` (admin-DOWN zeroing).
- Containers are not link endpoints: `backend/api/endpoints/links.py` (POP disallow and container blocks), `backend/utils.py` (parenting rules and container semantics).
- Primary traversal vs L2/L3 fallback: `backend/services/traffic/v2_engine.py` (BFS to anchors; preference CORE → BACKBONE → POP), `backend/services/forwarding_service.py` (`resolve_flow_path` for fallback when no anchor is reachable).
- Router cockpit capacity sourcing: `backend/services/catalog_effective.py` (effective capacity resolution), `backend/api/schemas.py` (exposes `effective_device_capacity_mbps`), `backend/services/traffic/v2_aggregation.py` (`bps`/`upstream_bps`/`downstream_bps`, `utilization`).
- IPAM /31 P2P pool status: `backend/services/seed_service.py` (management pools), `backend/services/provisioning_service.py` (mgmt0 allocation), `backend/api/endpoints/links.py` (router↔router `routed_p2p` classification).

#### Cross-links for Onboarding Q4 topics

- Container rules (POP vs CORE_SITE): `backend/utils.py::validate_parent_child`, `backend/constants/provisioning.py::DEVICE_PARENT_POOL_MAP`, `backend/services/provisioning_service.py::provision_device` (Parent‑Typprüfung), `backend/errors.py::ErrorCode.CONTAINER_REQUIRED`.
- Containers not link endpoints (graph transparency): `backend/api/endpoints/links.py` (container disallow), `backend/services/optical_path_resolver.py::_build_records` (Edges aus Device‑Interfaces; keine Container‑Kanten).
- L6B access_uplink semantics: `backend/constants/link_types.py` (L6B Kommentar „non‑optical“), `backend/constants/provisioning.py::PROVISION_MATRIX` (OLT benötigt Upstream‑Core; Router‑Uplink erfüllt Abhängigkeit, nicht Optik).
- Strict ONT provisioning (no soft mode): `backend/constants/provisioning.py` (Flags entfernt, strikt), `backend/tests/test_soft_ont_dependency.py` (Verhalten trotz Flag), `backend/services/provisioning_service.py` (strikte Abhängigkeitsprüfung via dependency_resolver).
- Transaction boundary & async recompute: `backend/services/provisioning_service.py` (Commit + Event), `backend/api/endpoints/provisioning.py` (coalescer + BackgroundTasks), `backend/services/background.py` (Optik‑Recompute Hook; falls vorhanden).

- [x] ID: TASK-820
      Title: Frontend: Implement High-Fidelity "Digital Display" OLTCockpit with Port Matrix
      Completed: 2025-09-16
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Implemented a new, high-fidelity `OLTCockpit` based on the "Digital Display" standard. The cockpit features a status-aware frame, header with status LEDs, and a multi-row layout displaying key metrics like Status, Total Traffic, and Subscriber counts. The most critical new feature is a dynamic Port Matrix that visualizes the status of each PON port as a colored grid cell (Green/Yellow/Red/Gray) based on the status of the ONTs connected to it. Proactively fixed a complex graph traversal bug to ensure that ONTs connected via passive devices (e.g., Splitters) are correctly detected and reflected in the port matrix.
      Artifacts: unoc-frontend-v2/src/components/cockpits/OLTCockpit.vue, unoc-frontend-v2/src/tests/cockpits/oltCockpit.spec.ts
- [x] ID: TASK-821
      Title: Frontend: Implement High-Fidelity "Digital Display" AONSwitchCockpit
      Completed: 2025-09-16
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Implemented a new, high-fidelity `AONSwitchCockpit` based on the "Digital Display" standard, ensuring visual consistency with the `OLTCockpit`. The new component features a status-aware frame, header with status LEDs, and a multi-row layout for key metrics. A dynamic Port Matrix visualizes the status of each ACCESS port based on the status of the connected AON_CPE. The implementation reuses and adapts the robust graph traversal logic from the OLT cockpit to ensure correct status detection, even through passive devices.
      Artifacts: unoc-frontend-v2/src/components/cockpits/AONSwitchCockpit.vue, unoc-frontend-v2/src/tests/cockpits/aonSwitchCockpit.spec.ts

- [x] ID: TASK-822
      Title: Containers: Fully Integrate CORE_SITE Container
      Completed: 2025-09-16
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Completed the full integration of the `CORE_SITE` container. Added a default hardware model for `CORE_SITE` to the backend seeding service, ensuring it is created with a predefined slot layout. Added a new draggable entry to the frontend `DevicePalette`, making `CORE_SITE` containers creatable via the UI. Proactively identified and fixed a critical bug in the `AONSwitchCockpit`'s graph traversal logic that caused "cross-port contamination", ensuring each port's status is now calculated in isolation. The entire container feature is now functionally complete and stable.
      Artifacts: backend/services/seed_service.py, unoc-frontend-v2/src/components/palette/DevicePalette.vue, unoc-frontend-v2/src/components/cockpits/AONSwitchCockpit.vue

- [x] ID: TASK-823
      Title: Frontend: Implement High-Fidelity "Digital Display" ONTCockpit
      Completed: 2025-09-16
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Refactored the `ONTCockpit` to the new high-fidelity "Digital Display" standard. The new component, mounted for both `ONT` and `BUSINESS_ONT` devices, features a status-aware frame and header LEDs. The main content area now displays a multi-row layout with key end-device metrics: Status, RX Power (color-coded by signal quality), Upstream/Downstream Throughput, and the assigned Tariff name. The associated unit test was updated to validate the new data-driven presentation.
      Artifacts: unoc-frontend-v2/src/components/cockpits/ONTCockpit.vue, unoc-frontend-v2/src/tests/cockpits/ontCockpit.spec.ts

- [x] ID: TASK-824
      Title: Frontend: Implement High-Fidelity "Digital Display" AONCPECockpit
      Completed: 2025-09-16
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Completed the end-device visualization by creating a new, dedicated `AONCPECockpit` based on the "Digital Display" standard. This new component is now correctly mounted for `AON_CPE` devices and is visually consistent with the `ONTCockpit` but correctly omits the irrelevant "RX POWER" metric. The implementation includes a dedicated unit test to verify the AON-specific layout, ensuring a clear and accurate representation for both GPON and AON end-devices.
      Artifacts: unoc-frontend-v2/src/components/cockpits/AONCPECockpit.vue, unoc-frontend-v2/src/composables/topologyCore/draw.ts, unoc-frontend-v2/src/tests/cockpits/aonCPECockpit.spec.ts

      - [x] ID: TASK-825
      Title: Containers: Make Feature Permanent by Removing Feature Flag
      Completed: 2025-09-16
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Fully integrated the hierarchical container feature into the core application by removing the `CONTAINERS_ENABLED` feature flag. The flag was removed from the backend configuration, the `/api/config` endpoint, and all corresponding frontend type definitions. All relevant documentation, including ADRs and planning documents, was updated to reflect that containers are now a permanent and always-on feature.
      Artifacts: backend/config.py, docs/ADR-008-containers-link-rendering.md, docs/TASK-800-container-nodes-plan.md

      - [x] ID: TASK-826
      Title: Bugfix: Fix D3 `insertBefore` NotFoundError on Canvas Redraw
      Completed: 2025-09-16
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Fixed a critical rendering bug that caused a "NotFoundError: Failed to execute 'insertBefore' on 'Node'" error during the initial canvas draw. The root cause was identified as an incorrect DOM insertion point for the new `containers-layer`. The logic in `draw.ts` was corrected to ensure the container layer is inserted within the correct parent `g.zoomRoot` node, resolving the cross-parent insertion conflict and stabilizing the rendering pipeline.
      Artifacts: unoc-frontend-v2/src/composables/topologyCore/draw.ts

- [x] ID: TASK-828
      Title: GPON Logic Fix Phase 1: Enforce Port-Specific PON Links
      Completed: 2025-09-17
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Implemented Phase 1 of the GPON logic overhaul to fix incorrect subscriber counts. The backend now enforces a strict validation rule requiring that any optical link originating from an OLT must be bound to an interface with the `PON` port role. The frontend was updated in parallel: the link creation modal now intelligently pre-selects and filters the available interfaces on an OLT, presenting the user only with valid, available `PON` ports for optical connections. This ensures topological correctness at the data layer.
      Artifacts: backend/api/endpoints/links.py, unoc-frontend-v2/src/stores/linksStore.ts

- [x] ID: TASK-829
      Title: Frontend: Fix and Enhance Multi-Link Creation Workflow
      Completed: 2025-09-18
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Fixed a critical bug where the multi-link creation feature was incompatible with the new port-specific linking modal. The `linksStore.createBetweenDevices` function was refactored to support a `headless` mode. The multi-link handler now calls this function in headless mode, leveraging the existing intelligent, role-aware interface auto-selection logic to create multiple links in a single, efficient bulk operation without displaying a UI modal for each link. The single-link workflow remains unchanged and still presents the modal for user override.
      Artifacts: unoc-frontend-v2/src/stores/linksStore.ts, unoc-frontend-v2/src/composables/topologyCore/handlers.ts

- [x] ID: TASK-831
      Title: Architecture: Implement Path-Aware GPON Linking for Passive Chains
      Completed: 2025-09-20
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Enhanced the GPON link creation logic to be fully "path-aware". The system now allows ONTs to be connected to any passive device (Splitter, NVT, HOP) within a valid, ODF-headed optical path. Implemented a graph traversal (BFS) on both the frontend (for interactive guidance) and the backend (for authoritative validation) to ensure that a passive device has a valid upstream path to an OLT-connected ODF before allowing an ONT to be linked. The link creation modal was enhanced to annotate interface options with the parent OLT's context, significantly improving user experience.
      Artifacts: unoc-frontend-v2/src/stores/linksStore.ts, backend/api/endpoints/links.py

- [x] ID: TASK-906
      Title: Architecture: End-to-End System Hardening based on Code Analysis
      Completed: 2025-09-18
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Performed a comprehensive, end-to-end hardening of the application based on an external AI code analysis. Implemented multiple critical fixes and improvements across the stack. Added backend validation for link media types and tariff-technology compatibility. Hardened the link creation endpoint against race conditions. Improved the determinism of the optical path resolver's tie-breaking logic. Implemented version-based guards in the frontend stores to prevent state inconsistencies from out-of-order WebSocket events. Added robust error handling to several key API endpoints. Implemented a lightweight pagination for the OLT cockpit's port matrix to handle high-port-count devices gracefully.
      Artifacts: backend/api/endpoints/links.py, backend/api/endpoints/devices.py, backend/services/optical_path_resolver.py, unoc-frontend-v2/src/stores/devicesStore.ts, unoc-frontend-v2/src/components/cockpits/OLTCockpit.vue

- [x] ID: TASK-907
      Title: Architecture: Migrate Development Environment to PostgreSQL
      Completed: 2025-09-18
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Resolved critical `sqlite3.OperationalError: database is locked` errors by migrating the development environment from SQLite to PostgreSQL. The database configuration is now environment-driven, defaulting to PostgreSQL when a `DATABASE_URL` is provided, while retaining SQLite as a fallback for tests. Added `psycopg` and `asyncpg` as dependencies. Created a `docker-compose.yml` for easy, one-command local database setup. The `README.md` was updated with instructions for the new workflow. This change fundamentally resolves concurrency issues and prepares the application for scalable, production-like performance.
      Artifacts: backend/db.py, requirements.txt, docker-compose.yml, README.md

- [x] ID: TASK-908
      Title: Architecture: Consolidate and Fix VS Code Task Runner Configuration
      Completed: 2025-09-19
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Resolved persistent and critical test execution failures by consolidating a duplicate `tasks.json` file. All frontend and backend tasks are now defined in a single, authoritative `/.vscode/tasks.json` file. The redundant configuration in the frontend sub-directory was removed. This change ensures a stable, predictable, and consistent execution environment for all development and testing workflows, eliminating the root cause of previous hangs and deadlocks.
      Artifacts: .vscode/tasks.json

- [x] ID: TASK-909
      Title: Architecture: Stabilize Test Environment with Isolated In-Memory SQLite DB
      Completed: 2025-09-19
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Resolved critical, persistent test suite deadlocks and failures by completely isolating the test environment. The `conftest.py` fixture was refactored to hardcode the test suite to always use a fast, clean, in-memory SQLite database (`sqlite:///:memory:` with a shared cache and `StaticPool`). All logic for running tests against PostgreSQL was removed, decoupling the test environment from Docker and the `.env` configuration. This change fixed all `ConnectionTimeout`, `UNIQUE constraint`, and `no such table` errors, resulting in a fast (~15s), stable, and 100% green test suite (214 tests passed).
      Artifacts: backend/tests/conftest.py, pytest.ini, requirements.txt

- [x] ID: TASK-910
      Title: Performance: Implement High-Performance Cache for Ports Summary API
      Completed: 2025-09-19
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Implemented a high-performance, in-memory TTL cache for the `/api/ports/summary` endpoint to resolve critical performance bottlenecks caused by frequent UI polling. The cache is intelligently keyed by `(topology_version, device_id)`, ensuring automatic invalidation upon any topology change. The implementation is concurrency-safe, using per-key `asyncio.Lock`s to prevent the "dogpile effect" under heavy load. This change significantly reduces CPU usage on the backend and dramatically improves UI responsiveness.
      Artifacts: backend/api/endpoints/ports.py

- [x] ID: TASK-911
      Title: Performance: Defer Heavy Recomputations to Background Tasks
      Completed: 2025-09-19
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Resolved critical server-side performance bottlenecks by refactoring the `create_link` and `provision_device` workflows to be fully asynchronous. A new central background task runner was implemented. All time-consuming, cascading operations (status re-computation, optical path updates, event broadcasting) are now executed as background tasks. The API endpoints now return immediately after persisting the initial change, reducing response times from seconds to milliseconds. The entire test suite was refactored and stabilized to correctly handle the new asynchronous and event-driven architecture.
      Artifacts: backend/core/background.py, backend/api/endpoints/links.py, backend/api/endpoints/provisioning.py, backend/services/provisioning_service.py

- [x] ID: TASK-912
      Title: Architecture: Create Automated Performance Test Harness
      Completed: 2025-09-19
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Created a dedicated, scriptable performance test harness to enable automated, data-driven performance analysis. The new test suite, located in `backend/tests/perf/`, includes topology factories for programmatically generating large-scale networks (e.g., 100+ ONTs). Implemented a "Bulk Mode" to suppress intermediate re-computation cascades during test setup, ensuring efficient topology generation. Integrated the `pyinstrument` profiler to automatically generate HTML performance reports when run with an environment flag. The performance tests are correctly marked and excluded from the default CI test run.
      Artifacts: backend/tests/perf/test_large_scale.py, requirements.txt, pytest.ini

- [x] ID: TASK-913
      Title: Architecture: Implement Asynchronous Re-computation and Concurrency
      Completed: 2025-09-19
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Resolved critical performance bottlenecks by re-architecting the application for true concurrency and asynchronous processing. Introduced Gunicorn for multi-process request handling. Implemented a sophisticated "re-computation coalescer" that debounces and merges cascading state updates (status, optical, etc.) into single, efficient background tasks. All "write" endpoints (`/links`, `/devices/provision`, etc.) were refactored to return immediately after persisting the initial change, deferring heavy computations to the background. The test suite was significantly hardened to be compatible with this new asynchronous, event-driven architecture, ensuring both deterministic tests and a highly performant, scalable application.
      Artifacts: backend/core/background.py, backend/core/recompute_coalescer.py, backend/api/endpoints/links.py, backend/api/endpoints/provisioning.py, gunicorn.conf.py, requirements.txt

- [x] ID: TASK-914
      Title: Architecture: Refactor Tests to be Fully Asynchronous-Aware
      Completed: 2025-09-19
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Finalized the asynchronous re-computation architecture by refactoring the test suite to be fully async-aware. Removed all `flush_now()` calls from production code, ensuring re-computations are always efficiently coalesced. Created a new `wait_for_coalescer_idle()` test helper to allow tests to deterministically await the completion of background tasks. All relevant, previously failing tests were converted to `async` and now use this helper, resulting in a fast, stable, and reliable test suite that correctly validates the application's asynchronous behavior.
      Artifacts: backend/tests/conftest.py, backend/tests/async_helpers.py, backend/api/endpoints/links.py, backend/api/endpoints/provisioning.py

- [x] ID: TASK-915
      Title: Architecture: Make ODF-Based GPON Link Rules Permanent
      Completed: 2025-09-20
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Made the strict "ODF-as-Aggregator" GPON link validation rules a permanent and unconditional part of the backend logic. Removed the temporary `UNOC_ENFORCE_GPON_PHASE1` feature flag and enabled the corresponding test suite by default. Proactively refactored multiple legacy test files that still assumed invalid direct OLT-to-ONT connections, aligning the entire test suite with the new, architecturally correct topology.
      Artifacts: backend/api/endpoints/links.py, backend/tests/test_gpon_phase1_rules.py, backend/tests/test_link_classification_positive.py

- [x] ID: TASK-916
      Title: GPON Logic Fix Phase 2: Implement Per-Segment Aggregation and Congestion
      Completed: 2025-09-20
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Completed the GPON logic overhaul by implementing per-segment aggregation and congestion modeling in the backend. The TrafficEngineV2 now correctly aggregates ONT traffic onto specific OLT PON ports via the ODF-as-aggregator model. Implemented a new `CONGESTED` status for segments, triggered by demand exceeding port capacity, with hysteresis to prevent flapping. The metrics snapshot API was extended to include detailed, per-segment metrics (occupancy, capacity, demand, headroom, congestion state). New `segment.congestion.*` events are now emitted.
      Artifacts: backend/services/traffic/v2_engine.py, backend/api/schemas.py, backend/events.py

- [x] ID: TASK-917
      Title: Architecture: Refactor Test Suite to be Fully Asynchronous-Aware
      Completed: 2025-09-20
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Finalized the asynchronous backend architecture by refactoring the entire test suite to be fully async-aware. Removed all remaining synchronous test antipatterns. All timing-sensitive tests were converted to `async` and now use the `wait_for_coalescer_idle()` helper to deterministically await the completion of background re-computation tasks before making assertions. Proactively identified and fixed several subtle bugs in existing tests related to logic and cache invalidation. The entire backend suite (218 tests) is now fast (~17s), stable, and correctly validates the application's asynchronous, event-driven behavior.
      Artifacts: backend/tests/conftest.py, backend/tests/async_helpers.py, backend/tests/test_optical_status_gating.py, backend/tests/test_traffic_segments.py

- [x] ID: TASK-918
      Title: Architecture: Finalize ODF-as-Aggregator Link Logic
      Completed: 2025-09-20
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Finalized the "ODF-as-Aggregator" architecture by implementing a strict, user-driven 1-to-1 mapping between OLT PON ports and ODFs. The frontend link creation workflow was refactored to enforce this exclusivity: the link modal now presents the user with a list of only the available, unlinked PON ports on the OLT, and a PON port is removed from the list once it is assigned to an ODF. The backend was verified to correctly seed passive devices with default `insertion_loss_db` values.
      Artifacts: unoc-frontend-v2/src/stores/linksStore.ts, backend/services/seed_service.py

- [x] ID: TASK-919
      Title: Architecture: Forbid ODF-to-ODF Link Cascades
      Completed: 2025-09-20
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Hardened the "ODF-as-Aggregator" architecture by strictly forbidding the creation of ODF-to-ODF link cascades. Implemented a new validation rule in the backend to reject such links with a `LINK_INVALID_PAIRING` error. A corresponding guard was added to the frontend `linksStore` to block the action on the client-side. Added dedicated backend and frontend unit tests to verify this new, stricter rule, ensuring the topological integrity of the GPON model.
      Artifacts: backend/api/endpoints/links.py, backend/tests/test_links_negative.py, unoc-frontend-v2/src/stores/linksStore.ts, unoc-frontend-v2/src/stores/**tests**/linksStore.spec.ts

- [x] ID: TASK-832
      Title: Bugfix: Fix and Enhance Router Cockpit Capacity Display
      Completed: 2025-09-20
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Fixed a critical bug where `CORE_ROUTER` and `EDGE_ROUTER` cockpits failed to display their total capacity. The backend API was corrected to ensure `effective_capacity_mbps` is always populated from the device's hardware model. The `RouterCockpit` was subsequently refactored to prevent visual text overlap. It now displays the capacity in a "current / max" format (e.g., "2 Gbps / 800 Gbps") with a shortened "TotCap (Gbps)" label and rounded integer values for a clean, readable presentation.
      Artifacts: backend/api/endpoints/devices.py, unoc-frontend-v2/src/components/cockpits/RouterCockpit.vue

- [x] ID: TASK-919
      Title: Documentation: Comprehensive Overhaul and Synchronization with Codebase
      Completed: 2025-09-20
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Performed a comprehensive overhaul of the project's technical documentation to synchronize it with the current, advanced state of the codebase. All core architecture documents (`01` through `07` and `ARCHITECTURE.md`) were reviewed and updated to reflect recent features like the "ODF-as-Aggregator" model, refined linking rules, and new cockpit display logic. Proactively created new, detailed documents for previously undocumented core concepts, including `08_ports.md`, `09_cockpit_nodes.md`, and `10_interfaces_and_addresses.md`. The documentation for congestion and hysteresis was also added, ensuring the entire system is now accurately and professionally documented.
      Artifacts: docs/llm/ (multiple files updated and created)

- [x] ID: TASK-920
      Title: Documentation: Create Authoritative API Reference and Commands Playbook
      Completed: 2025-09-20
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: Dramatically improved developer efficiency and project clarity by creating two new, central documentation files. Created a comprehensive API reference (`13_api_reference.md`) by scanning the codebase, documenting all major endpoints, their expected payloads, and cross-referencing them with other architecture documents. Created a `14_commands_playbook.md` with a collection of copy-paste-ready, robust PowerShell commands for all common development and testing tasks, establishing best practices for interacting with the project's environment.
      Artifacts: docs/llm/13_api_reference.md, docs/llm/14_commands_playbook.md


- [x] ID: TASK-921
      Title: Critical Fix: Resolve API 500 Errors and Harden Container Update Logic
      Completed: 2025-09-21
      Milestone: M11 – Reliability & Observability
      Commit: <final-git-sha>
      Notes: Fixed a critical backend regression that caused numerous 500 Internal Server Error responses across the API, most visibly on the /api/ports/summary endpoint. The root cause was an AttributeError due to a mismatch between the SQLAlchemy AsyncSession and the SQLModel .exec() method call. The fix involved correcting the async session factory in db.py. Additionally, a major validation gap was closed by enforcing parent-child container rules on device updates (PUT /api/devices/{id}), not just on creation, preventing invalid states like placing a BACKBONE_GATEWAY in a container. The frontend was also corrected to send parent_container_id: null when dragging a device out of a container.
      Artifacts: backend/db.py, backend/api/endpoints/devices.py, unoc-frontend-v2/src/composables/topologyCore/drag.ts

- [x] ID: TASK-922
      Title: Architecture: Finalize and Enforce Container Placement Rules
      Completed: 2025-09-21
      Milestone: M9 – Foundational Network Emulation
      Commit: <final-git-sha>
      Notes: Performed a comprehensive refinement and hardening of the hierarchical container placement rules to align the implementation with the authoritative architecture. The validation logic in utils.py was iteratively updated to enforce the final, precise ruleset: OLT/AON_SWITCH must be in a POP; CORE_ROUTER/BACKBONE_GATEWAY can only be in a CORE_SITE; EDGE_ROUTER can be in either or standalone. A significant portion of the backend test suite was systematically refactored to assert this new behavior, ensuring the changes are robust and guarded against future regressions.
      Artifacts: backend/utils.py, backend/tests/test_utils_branches.py, backend/tests/test_parent_validation.py, backend/tests/test_parent_assignment_return_field.py, backend/tests/test_utils_unit.py, backend/tests/test_gpon_phase1_rules.py

- [x] ID: TASK-923
      Title: Frontend: Enlarge Container Visuals and Fix Slot Overlap Issues
      Completed: 2025-09-21
      Milestone: M8 – Smart SVG Cockpits & Visualization
      Commit: <final-git-sha>
      Notes: Addressed multiple visual and usability issues with the container cockpits. The overall size of the POP and CORE_SITE containers was increased by approximately 30% to prevent child nodes from clipping the container boundaries. The internal slot grid was adjusted, and a consistent inset was applied to fix misaligned snap-halos and resolve visual overlap between adjacent snapped devices. These changes significantly improve the clarity and usability of the topology view.
      Artifacts: unoc-frontend-v2/src/composables/topologyCore/containerLayouts.ts, unoc-frontend-v2/src/composables/topologyCore/draw.ts, unoc-frontend-v2/src/composables/topologyCore/drag.ts

- [x] ID: TASK-924
      Title: Architecture: Add Authoritative Matrix Test for Container Rules
      Completed: 2025-09-21
      Milestone: M10 – Ops Readiness & Scalability
      Commit: <final-git-sha>
      Notes: To prevent future regressions in the now-complex container placement logic, a new, dedicated, table-driven test file (test_parent_matrix.py) was created. This single test systematically validates every valid and invalid combination of parent-child device placements via the API, serving as a single source of truth for testing the containment rules. The LLM documentation (02_provisioning_model.md and 07_container_model_and_ui.md) was also updated to reflect the final, correct rules.
      Artifacts: backend/tests/test_parent_matrix.py, docs/llm/02_provisioning_model.md, docs/llm/07_container_model_and_ui.md

Entry Template (append newest at top or use chronological order – decide and remain consistent):

```
- [x] ID: TASK-XXX
      Title: <short title>
      Completed: 2025-09-07
      Milestone: M# <name>
      Commit: <git-sha>
      Notes: <impact / brief summary>
      Artifacts: <optional links>
```

Changelog

---

- 2025-09-08: Added completed tasks for Milestone 1.
- 2025-09-07: Added completed tasks for Milestone 2.
- 2025-09-10: Added completed tasks for Milestone 3.
- 2025-09-09: Added completed tasks for Milestone 4.
- 2025-09-10: Added completed tasks for Milestone 5.
- 2025-09-11: Added completed tasks for Milestone 6.
- 2025-09-12: Added completed tasks for Milestone 7.
- 2025-09-13: Added completed tasks for Milestone 8.
- 2025-09-14: Added completed tasks for Milestone 9.

Notes:

- Legacy grouping headings retained for reference:
- Milestone 9: Advanced Features (Monitoring & Analytics)
- Milestone 8: Smart SVG Cockpits & Visualization
- Milestone 7: Maintenance & Cleanup
- Milestone 6: Commercial Basics
- Milestone 5: Simulation & Real-time
- Milestone 4: Status & Events
- Milestone 3: IPAM & Network Services
- Milestone 2: Core Functionality (Devices & Links)
- Milestone 1: The Foundation
