# UNOC Documentation

Start here for orientation, then dive into the section you need. This structure favors scale (1k–10k+ devices) and developer velocity.

## 🎯 Active Roadmap

- **[Operation Stable Foundation](roadmap/OPERATION-STABLE-FOUNDATION.md)** — 3-week plan for Hybrid Python+Go architecture (60-120× speedup for Sandbox operations)

## 📚 Core Documentation

### Architecture → **[architecture/INDEX.md](architecture/INDEX.md)**

- architecture/ARCHITECTURE.md — **Start here** (Hybrid Python+Go v2.0)
- architecture/HYBRID-ARCHITECTURE.md — _(TODO: Week 1)_ Go Hybrid design
- architecture/data-model.md
- architecture/topology-engine.md — Go Traffic Engine ✅
- architecture/recompute-pipeline.md — ⚠️ Week 2: Migrate to Go
- architecture/caching-and-snapshots.md
- architecture/events-and-ws.md
- architecture/status_service.md — ⚠️ Week 2: Migrate to Go
- architecture/IPAM-Architecture-Future.md
- architecture/adr/ADR-008-containers-link-rendering.md

### Setup

- setup/local-dev.md — **Quick start** (Python + Go + Vue)
- setup/backend.md
- setup/frontend.md
- setup/database.md
- setup/env.md

### API Reference

- api/README.md
- api/endpoints.md
- api/websocket.md

### Performance & Testing → **[performance/INDEX.md](performance/INDEX.md)**

- performance/HGO-010-LoadTest-Results.md — 200-device ✅
- performance/HGO-011-LoadTest-Results.md — 1000-device ✅
- performance/harness.md
- performance/profiling.md
- performance/metrics.md

### Operations → **[operations/INDEX.md](operations/INDEX.md)**

- operations/runbook.md
- operations/prometheus-grafana-setup.md — **Monitoring ✅ AKTIV**
- operations/GO-SERVICES-DEPLOYMENT.md — _(TODO: Week 3)_
- operations/bootstrap/bootstrap_anchors.md
- operations/planning/Priorities.md
- operations/process/Definition-of-Done.md

### User Guides

- guides/ui/bulk-create-modal.md
- guides/network-design/ipam_gpon_ethernet_dg.md
- guides/network-design/pop_coreSide.md
- guides/l3-auto-provisioning.md
- guides/gpon-odf-acceptance-criteria.md

### Design Decisions

- design-decisions/README.md (see also docs/architecture/adr)

## 🧠 LLM Context (For AI Assistants)

Comprehensive module-by-module summaries:

1. [Domain Model](llm/01_overview_and_domain_model.md)
2. [Provisioning](llm/02_provisioning_model.md)
3. [IPAM & Status](llm/03_ipam_and_status.md)
4. [Signal Budget & Overrides](llm/04_signal_budget_and_overrides.md)
5. [Realtime & UI](llm/05_realtime_and_ui_model.md)
6. [Catalog & Extensions](llm/06_future_extensions_and_catalog.md)
7. [Container Model](llm/07_container_model_and_ui.md)
8. [Ports](llm/08_ports.md)
9. [Cockpit Nodes](llm/09_cockpit_nodes.md)
10. [Interfaces & Addresses](llm/10_interfaces_and_addresses.md)
11. [Traffic Engine & Congestion](llm/11_traffic_engine_and_congestion.md)
12. [Testing & Performance](llm/12_testing_and_performance_harness.md)
13. [API Reference](llm/13_api_reference.md)
14. [Commands Playbook](llm/14_commands_playbook.md)

Also see:

- llm/ARCHITECTURE.md — High-level architecture summary
- llm/ROADMAP.md — Historical roadmap (superseded by `roadmap/OPERATION-STABLE-FOUNDATION.md`)

## 📦 Archive

Historical documentation preserved for reference:

- `archive/2025-10-04-prometheus/` — Prometheus/Grafana early integration docs (superseded by operations/prometheus-grafana-setup.md)
- `archive/2025-10-04-old-roadmaps/` — Previous roadmaps (superseded by roadmap/OPERATION-STABLE-FOUNDATION.md)
- `archive/2025-10-04-legacy-task-system/` — Legacy task tracking (deprecated)
- `archive/2025-09-19-legacy/` — Earlier archive snapshot

**Note:** Prometheus/Grafana are **ACTIVE** in production. Current setup docs: `operations/prometheus-grafana-setup.md`
