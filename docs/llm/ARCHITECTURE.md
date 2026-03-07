# UNOC v3 – Architecture Overview

**Spec Revision:** r10.1 (Hybrid Architecture Complete: Optical PathFinder + Status Propagation + Traffic Engine) – 2025‑10‑05

<!-- Added r10.1: Optical PathFinder complete (Day 17), 4,000× speedup, 10-12ms per ONT vs 40s Python -->
<!-- Added r10.0: Complete hybrid Python+Go architecture (Week 3: Batch Operations + Optical Compute), 4 Go services production-ready, 60-120× end-to-end speedup -->
<!-- Added r9.15: Hybrid Python+Go architecture for status propagation (Week 2 complete), 30,000× performance improvement -->
<!-- Added r9.14: Async writes default, no flags -->
<!-- Added r9.12: unified status model, immediate downstream cascade, link.status.changed event, topo_version stamping -->

The **single source of truth** for UNOC v3’s architecture and domain logic.  
This file is the **entry point** and guide to the detailed documents under [`/docs/llm/`](./).

---

## 🎯 Target Architecture (Vision)

UNOC v3 evolves towards a **network emulator** focused on realistic L2/L3 behavior and optical constraints.

Core principles:

- **Stateful interfaces** on every device (including container/passive) with unique MAC addresses, roles (e.g., `p2p_uplink`, `management`), admin status, and multiple IPv4 addresses per interface.
- **Hardware catalog** drives device realization: port counts, default speeds/MTUs, and optical TX/RX parameters originate from selected models (OLTs, switches, routers). Signal budgets and status derive from hardware and link properties.
- **Layer‑2 switching pipeline**: MAC learning per bridge domain, aging, known‑unicast forwarding, flooding for unknown/broadcast.
- **Layer‑3 routing**: Per‑device VRFs and static routes; reachability via longest‑prefix‑match and next‑hop resolution (ARP/neighbor cache), not just the topology graph.
- **Traffic Engine v2**: Flow‑based, with ONT tariffs for asymmetric up/down limits, enforced via interface queues. Overload produces measurable drops and events such as “Upstream Congestion”.

This vision anchors connectivity and utilization in protocol‑like state to enable **realistic diagnostics** (MAC/RIB inspection, path‑based counters) and **authentic behavior** under load and failures.

---

## 📂 Table of contents & links

1. [Overview](./01_overview_and_domain_model.md#overview)
2. [Domain Model & Classification](./01_overview_and_domain_model.md#domain-model--classification)
3. [Provisioning Model & Provision Matrix](./02_provisioning_model.md)
4. [IPAM (Lazy Allocation)](./03_ipam_and_status.md#ipam-lazy-allocation)
5. [Status Simulation & Propagation](./03_ipam_and_status.md#status-simulation--propagation)
6. [Signal Budget Model](./04_signal_budget_and_overrides.md#signal-budget-model)
7. [Admin Override System](./04_signal_budget_and_overrides.md#admin-override-system)
8. [Real-time Delta Events](./05_realtime_and_ui_model.md#real-time-delta-events)
9. [UI Interaction Model](./05_realtime_and_ui_model.md#ui-interaction-model)
10. [Error Codes & Failure Semantics](./05_realtime_and_ui_model.md#error-codes--failure-semantics)
11. [Determinism & Ordering Guarantees](./05_realtime_and_ui_model.md#determinism--ordering-guarantees)
12. [Glossary](./05_realtime_and_ui_model.md#glossary)
13. [Future Extensions / Non‑Goals](./06_future_extensions_and_catalog.md#future-extensions--non-goals)
14. [Reference Catalog (Hardware & Optical Defaults)](./06_future_extensions_and_catalog.md#reference-catalog-hardware--optical-defaults)
15. [Real-time Simulation & Metrics](./06_future_extensions_and_catalog.md#real-time-simulation--metrics)
16. [Smart SVG Cockpits & Real-time Visualization](./06_future_extensions_and_catalog.md#smart-svg-cockpits--real-time-visualization)
17. [Stable Physics Engine (Incremental D3 Force Layout)](./06_future_extensions_and_catalog.md#stable-physics-engine-incremental-d3-force-layout)
18. [Pathfinding Logic](./06_future_extensions_and_catalog.md#pathfinding-logic)
19. [Ring Protection (Failure Link Protection)](./06_future_extensions_and_catalog.md#ring-protection-failure-link-protection)
20. [Container Model & UI (POP, CORE_SITE)](./07_container_model_and_ui.md)
21. [Ports and Interface Summaries](./08_ports.md)
22. [Cockpit Nodes (Components & Rendering)](./09_cockpit_nodes.md)
23. [Interfaces & Addresses (Deep Dive)](./10_interfaces_and_addresses.md)
24. [Traffic Engine & Congestion](./11_traffic_engine_and_congestion.md)
25. [Testing & Performance Harness](./12_testing_and_performance_harness.md)
26. [REST API Reference (Authoritative)](./13_api_reference.md)
27. [Commands Playbook (PowerShell)](./14_commands_playbook.md)
28. [Interactive Network Emulation (Backlog)](./BACKLOG.md)

---

## 🧭 What’s where? (quick map)

| Feature                               | Where to read                                                                                     | Notes                                                                                                                                                                             |
| ------------------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Domain model & device types           | [01_overview_and_domain_model.md](./01_overview_and_domain_model.md#domain-model--classification) | Core entities, types, and relationships                                                                                                                                           |
| Provisioning model & link rules       | [02_provisioning_model.md](./02_provisioning_model.md)                                            | Provision matrix, GPON constraints, POP not a link endpoint                                                                                                                       |
| IPAM, status simulation & propagation | [03_ipam_and_status.md](./03_ipam_and_status.md)                                                  | IP allocation, VRF/Prefix uniqueness, status flow, **Go Status Service (Week 2, 30,000× speedup, production-ready)**                                                              |
| Optical model, fiber types & budget   | [04_signal_budget_and_overrides.md](./04_signal_budget_and_overrides.md)                          | Physical media, signal budget, optical resolver; fiber catalog endpoint in API quick links, **Go Optical PathFinder (Day 17, 4,000× speedup, 10-12ms per ONT, production-ready)** |
| Realtime events & UI model            | [05_realtime_and_ui_model.md](./05_realtime_and_ui_model.md)                                      | Delta payloads, ordering/determinism, error semantics                                                                                                                             |
| Ports summaries & ONT list            | [08_ports.md](./08_ports.md)                                                                      | Per‑interface summaries; container ONT listing; bulk summary                                                                                                                      |
| Cockpit nodes & TotCap label          | [09_cockpit_nodes.md](./09_cockpit_nodes.md)                                                      | Component structure; TotCap (Gbps) formatting; congestion link                                                                                                                    |
| Interfaces & addresses                | [10_interfaces_and_addresses.md](./10_interfaces_and_addresses.md)                                | Interface roles, mgmt0 semantics, multi‑IP, audit & uniqueness                                                                                                                    |
| Traffic Engine v2 & congestion        | [11_traffic_engine_and_congestion.md](./11_traffic_engine_and_congestion.md)                      | Tariffs, aggregation, hysteresis, events                                                                                                                                          |
| Containers (POP, CORE_SITE) & UI      | [07_container_model_and_ui.md](./07_container_model_and_ui.md)                                    | Container behaviors, layouts, selection rules                                                                                                                                     |
| Testing & performance harness         | [12_testing_and_performance_harness.md](./12_testing_and_performance_harness.md)                  | Pytest harness, profiling, reproducibility                                                                                                                                        |
| Active Backlog                        | [BACKLOG.md](./BACKLOG.md)                                                                        | Curated active work items (Interactive Emulation, TEv2 per-port, perf baseline, etc.)                                                                                             |
| Completed & Archived tasks            | [COMPLETED_TASKS.md](./COMPLETED_TASKS.md)                                                        | Historical ledger of completed/obsolete/deferred tasks                                                                                                                            |

## 🔄 Maintenance & versioning

- Changes to detailed documents happen **only** under `/docs/llm/`.
- **ARCHITECTURE.md** is updated only when structure or file paths change.
- Each revision is recorded in the header with date and revision tag.

---

## 🔔 r9.4 changes (codebase alignment)

- Frontend cockpits (Smart SVG) implemented and unified (Digital Display):
  - Router, OLT, AON Switch, ONT, Business ONT, and AON CPE have dedicated cockpits.
  - Container cockpits for POP and CORE_SITE with slot layouts and metrics.
  - Source: `unoc-frontend-v2/src/components/cockpits/*.vue`, mounted via `src/composables/topologyCore/draw.ts`.
- AON_CPE has its own cockpit without an “RX POWER” row (AON has no optical power).
- New container type `CORE_SITE` introduced (backend seeding + frontend palette); containers are not link endpoints (proxy selection in UI).
- Physics/positioning: a gentle containment force is implemented; a full “Stable Physics Engine” remains deferred for now.

Note: Some vision parts (full L2/L3 pipeline, full Traffic Engine v2) remain on the roadmap; details documented in the Overview.

---

Note: This structure is LLM‑friendly and supports targeted loading of individual topic areas.

### 🔌 API quick links (selected)

- Ports
  - GET `/api/ports/summary/{device_id}` → list[InterfaceSummaryOut]
  - GET `/api/ports/summary?ids=dev1&ids=dev2` → { device_id: list[InterfaceSummaryOut] }
  - GET `/api/ports/ont-list/{device_id}` → ONT/AON_CPE under a container
- Optical
  - GET `/api/optical/fiber-types` → authoritative fiber catalog (see 04)

Note: Port summaries use PortRole classification (PON | ACCESS | UPLINK | TRUNK). Containers (POP, CORE_SITE) are organizational only and never link endpoints.

Tip: Utilization for devices is computed against effective device capacity using upstream_bps (not up+down). UIs wanting a “current total” may show upstream_bps + downstream_bps, but should keep utilization consistent with server values.

## 🧪 Dev/Test & telemetry (implementation notes)

- Shared in‑memory SQLite for tests: the pytest harness uses a single in‑memory SQLite engine with shared cache to stabilize concurrent access and maximize speed. Fixtures ensure clean setup/teardown and avoid cross‑test leakage.
- Deterministic async recompute: backend coalesces status/optical/metrics updates per entity within a tick, enforcing a consistent event ordering to the websocket clients.
  - New in r9.14: Async write paths for links (override/delete) are the permanent default. Write endpoints persist minimal state and enqueue a job, responding with `202 {accepted:true, job_id}`. A single sequenced in‑process worker drains the queue in deterministic microbatches (budget via `UNOC_BATCH_BUDGET_MS`, default 50 ms) under FastAPI lifespan. `POST /api/links` remains synchronous (201) to allow immediate topology composition.
  - Job kinds (phase 1): `link.override`, `link.create`, `link.delete`. The dispatcher delegates to the existing synchronous implementations to avoid logic duplication.
  - Prometheus metrics (phase 1): `job_queue_depth` (Gauge), `job_worker_batch_size` (Histogram), `job_worker_batch_duration_seconds` (Histogram), and `jobs_processed_total{kind}` (Counter), exported on the existing `/api/metrics/prometheus` endpoint.
- SQL telemetry & profiling: request middleware publishes timing and query counters to logs (dev mode) to surface N+1 patterns and slow paths early. These hooks are no‑ops in production unless explicitly enabled.

These are contributor‑facing notes; API contracts and UI behavior are specified in the linked topic documents.

Clarification on L2/L3 fallback: Traffic aggregation primarily uses a BFS over passable links/devices to reach an anchor (preference CORE → BACKBONE → POP). Only if no anchor is reachable does the engine consult the L2/L3 forwarding path (resolve_flow_path) as a best‑effort fallback.

---

## 🆕 r9.12 changes (final unified status model)

- Immediate downstream cascade on link admin overrides (synchronous recompute executed inline in the override endpoint; zero-latency propagation to dependents).
- New event `link.status.changed` emitted alongside `device.status.changed`; both carry `topo_version` for ordering and replay consistency.
- ACTIVE device without a valid upstream anchor path now resolves to `DOWN` (no permissive fallback). Anchors: BACKBONE_GATEWAY / POP (ALWAYS_ONLINE scope restricted to these).
- Passive devices (ODF/SPLITTER/NVT/HOP) require both adjacent active chain members plus at least one downstream terminator (ONT/CPE) to be `UP`; otherwise `DOWN` (no intermediate DEGRADED state by default).
- Synchronous recompute strategy (Option A) selected: status recalculation occurs in-request for overrides, guaranteeing UI sees post-change state in the same websocket tick.
- All status-impacting events (device/link status or override) include `topo_version` captured prior to recompute to ensure deterministic sequencing.
- Legacy BFS reachability fully removed from the decision path; diagnostics and traffic gating rely solely on the unified upstream L3 chain + optical checks.
- Reason code set finalized (examples): `NO_ANCHOR`, `UPSTREAM_DEVICE_DOWN`, `OPTICAL_LOSS`, `PASSIVE_CHAIN_BREAK`, `ADMIN_DOWN`.

Refer to `03_ipam_and_status.md` §"Unified Status Propagation" for the canonical algorithm description.
