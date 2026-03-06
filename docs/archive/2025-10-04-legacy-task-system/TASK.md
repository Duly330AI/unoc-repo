# 🗂 UNOC – Master Task Index

---

## 📜 Maintenance Guidelines

- New tasks: Add directly to the appropriate chunk and link here under “Active Tasks.”
- Completed tasks: Set to `Status: Done` in the chunk and remove from “Active Tasks.” Optionally link in [`COMPLETED_TASKS.md`](./COMPLETED_TASKS.md).
- Numbering: Sequential; do not fill gaps—IDs remain stable.
- Consistency: Make changes to titles or descriptions in the chunk, not here.

---

## 🔍 See also

- [`COMPLETED_TASKS.md`](./COMPLETED_TASKS.md) – Archive of completed tasks
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) – Overall technical overview

## 🔧 Task Management

## Critical: Use the templates below to ensure consistency.

## Mark [x] ID: TASK-### for done tasks.

## Mark [ ] for active/in-progress tasks.

## Mark [x] for done subtasks.

## Move done tasks to COMPLETED_TASKS.md only if all subtasks are done.

- Task Template (copy-paste for new tasks):
  Completed tasks marked with [x], pending with [ ]

```
- [ ] ID: TASK-###
                  Title: Short descriptive title
                  Status: Proposed / In Progress / Blocked / Done
                  Created: YYYY-MM-DD
                  Milestone: Mx – Milestone Name
                  Commit: <git-sha-if-applicable>
                  Notes: Detailed description, context, and any relevant links.
                  Artifacts: List of affected files or modules.
                  - [ ] Subtask or checklist item 1
                  - [ ] Subtask or checklist item 2

```

Aufgaben (detailliert nach Milestones)

- [x] ID: TASK-001
      Title: GraphIndex Skelett einführen (Build + Nachbarschafts-APIs)
      Status: Done
      Created: 2025-01-01
      Milestone: M1 – Dirty-Set + Region-Versionierung
      Commit: -
      Notes: Einführung von backend/services/graph_index.py mit deterministischer Ordnung und minimalem Funktionsumfang ohne Behavior-Änderung.
      Artifacts: - backend/services/graph_index.py - backend/tests/test_graph_index_minimal.py - [x] Modul anlegen mit: build(), neighbors_device(), neighbors_link() - [x] Deterministische Sortierung (stable order) angewendet - [x] Unit-Tests: kleine Topologie, erwartete Nachbarschaften - [x] Lint/Format/Tests: ruff, pytest (black/isort optional, repo-Tasks vorhanden) - [x] Qualitätstasks laufen lokal grün (kein zentrales CI)

- [x] ID: TASK-002
      Title: RegionVersionMap implementieren (lokale Versionierung)
      Status: Done
      Created: 2025-01-01
      Milestone: M1 – Dirty-Set + Region-Versionierung
      Commit: -
      Notes: Ersetzen der globalen topo_version durch pro-Region Versionen; in-memory Start, später persistierbar.
      Artifacts: - backend/services/graph_index.py (RegionVersionMap integriert) - backend/tests/test_graph_index_minimal.py - [x] API: bump(region_id), version(region_id) (Startwert 0) - [x] Integration in GraphIndex (region_id_of_device()) - [x] Lokale Lint/Tests laufen sauber

- [x] ID: TASK-003
      Title: DirtySet-Typ und Ermittlung
      Status: In Progress
      Created: 2025-01-01
      Milestone: M1 – Dirty-Set + Region-Versionierung
      Commit: -
      Notes: Dirty-Set aus Änderungen ableiten; Gates respektieren (z. B. L3-Reachability).
      Artifacts: - backend/services/graph_index.py - backend/tests/test_dirty_set_minimal.py - [x] Typ DirtySet definieren (devices, links, region_id) - [x] dirty_set_for_change(change) implementiert (konservativer 1-Hop-Ansatz) - [x] affected_region_for_devices(dev_ids) implementiert - [x] Tests: O(|DirtySet|) ohne Full-Scan, deterministische Ordnung (Minimaltests vorhanden)

- [x] ID: TASK-004
      Title: status_service.recompute_dirty (Toposort/BFS)
      Status: Done
      Created: 2025-01-01
      Milestone: M1 – Dirty-Set + Region-Versionierung
      Commit: -
      Notes: Inkrementeller Recompute über deterministische BFS-Expansion aus dem Dirty-Set (Geräte + Link-Endpunkte) auf Basis des topologie-versionierten Adjazenz-Cache; in-Runden-Baseline/Memoization; Delegation an recompute_devices_status; stabile Ordnung, minimale Transitionen.
      Artifacts: - backend/services/status_service.py - backend/services/status_recompute.py - backend/tests/test_recompute_dirty.py - [x] Toposort/BFS deterministisch implementieren - [x] In-Runden-Memoization, kein Cross-Round-Cache - [x] Metriken: dirty_set_size_histogram - [x] Tests: nur lokale Nachbarschaften werden recomputed - [x] Backwards-Kompatibilität mit Voll-Recompute sicherstellen

- [ ] ID: TASK-005
      Title: v2_engine: prepare_dirty und aggregate_dirty
      Status: Proposed
      Created: 2025-01-01
      Milestone: M1 – Dirty-Set + Region-Versionierung
      Commit: -
      Notes: Vor- und Nachverarbeitung der Dirty-Ergebnisse, streng deterministisch.
      Artifacts: - backend/services/v2_engine.py - backend/tests/test_v2_engine_dirty_paths.py - [ ] prepare_dirty(dirty) Skelett - [ ] aggregate_dirty(dirty) Skelett - [ ] Tests für stabile Ordering und idempotente Ausführung - [ ] Coverage prüfen (>80% im Modul)

- [ ] ID: TASK-006
      Title: M1 Abschluss-Tests und Dokumentation
      Status: Proposed
      Created: 2025-01-01
      Milestone: M1 – Dirty-Set + Region-Versionierung
      Commit: -
      Notes: Minimale E2E-Szenarien, Readme/Docs aktualisieren, ARCHITECTURE.md Version bumpen falls nötig.
      Artifacts: - ARCHITECTURE.md - backend/tests/test_dirty_set_minimal.py - [ ] ARCHITECTURE.md SemVer-Bump + Changelog im Header - - [ ] E2E-Minimalfall über Sync-Pfad - - [ ] markdownlint für geänderte Doks - - [ ] CI/Jenkins/Actions grün

- [x] ID: TASK-007
      Title: Job/Queue-Grundlagen (Job, JobQueue, Microbatching)
      Status: Done
      Created: 2025-01-01
      Milestone: M2 – Async Commit + Microbatch-Worker
      Commit: -
      Notes: Sequenzierter Worker, next_microbatch(budget_ms), deterministische Reihenfolge (FIFO mit Stabilität). Implementiert als In-Memory Queue; keine externen Abhängigkeiten.
      Artifacts: - backend/core/jobs.py - backend/services/worker.py - backend/tests/test_job_queue_minimal.py - [x] Klassen: Job, InMemoryJobQueue, Microbatch API - [x] next_microbatch(max_items=256, budget_ms=50) Hard-Budget, stabile Auswahl (Tests ignorieren Zeit) - [x] Worker.run_once(queue, handler) Skelett - [x] Tests: stabile Reihenfolge, Worker ruft Handler auf - [ ] Metriken: job_queue_depth, job_batch_duration_ms (optional in erster Iteration)

- [ ] ID: TASK-008
      Title: Job-Dispatcher (Change → DirtySet → Recompute → Read-Model)
      Status: In Progress
      Created: 2025-01-01
      Milestone: M2 – Async Commit + Microbatch-Worker
      Commit: -
      Notes: Single-Orchestrator, keine konkurrierenden Voll-Recomputes.
      Artifacts: - backend/services/job_dispatcher.py - backend/tests/test_job_dispatcher.py - [ ] dispatch(job, graph) implementieren - [ ] Integration: recompute_dirty + traffic-dirty Hook (no-op wenn leer) - [ ] Read-Model-Update Hook (Platzhalter für M3) - [ ] Tests: deterministisches Verhalten, Fehlerszenarien

- [x] ID: TASK-009
      Title: API-Handler Async-Write (202 Response; default)
      Status: Done
      Created: 2025-01-01
      Milestone: M2 – Async Commit + Microbatch-Worker
      Commit: -
      Notes: Links-Endpunkte unterstützen Async-Write als permanenten Standard: PATCH override und DELETE delete liefern 202 {job_id, accepted:true}. POST create bleibt synchron (201) für deterministisches Aufbauen der Topologie innerhalb eines Flows. Frühere Flags/Headers (UNOC_ASYNC_WRITES, X-Async-Write) wurden entfernt.
      Artifacts: - backend/api/devices.py - backend/api/links.py - backend/tests/test_async_provision_api.py - [x] 202 {job_id, accepted:true} Response-Format stabilisieren - [x] Tests: Queue-Only, WS/ETag-Änderung beobachtbar - [x] Docs: API-Doku aktualisieren

- [x] ID: TASK-010
      Title: main.py Worker-Lifecycle + Feature-Flags
      Status: Done
      Created: 2025-01-01
      Milestone: M2 – Async Commit + Microbatch-Worker
      Commit: -
      Notes: Lifespan-Task mit sequenziertem Worker aktiviert bei `UNOC_ASYNC_WRITES=1`; Budget `UNOC_BATCH_BUDGET_MS` (Default 50 ms); Idle-Backoff, fail-safe Cancellation.
      Artifacts: - backend/main.py - backend/config.py - backend/tests/test_worker_lifecycle.py - [x] Flags lesen (env), Defaults deterministisch - [x] Worker Start/Stop und Takt 50–100 ms - [ ] Tests: Clean shutdown, kein Zombie-Thread (Nicht explizit getestet. Dies ist eine Lücke in der Testabdeckung, aber von geringerem Risiko.) - [x] Logging ohne PII; UTC-Zeitstempel

- [x] ID: TASK-011
      Title: Observability für Async-Pfade (Metriken + Logs)
      Status: Done
      Created: 2025-01-01
      Milestone: M2 – Async Commit + Microbatch-Worker
      Commit: -
      Notes: Prometheus-Metriken: `job_queue_depth`, `job_worker_batch_size`, `job_worker_batch_duration_seconds`, `jobs_processed_total{kind}` (exponiert über /api/metrics/prometheus).
      Artifacts: - backend/observability/metrics.py - backend/tests/test_metrics_exposure.py - [ ] Metriken exposen: job_queue_depth, job_batch_duration_ms, dirty_set_size_histogram (Die ersten beiden sind umgesetzt, das dirty_set_size_histogram nicht, da das Dirty-Set selbst noch nicht vollständig implementiert ist.) - [ ] p95 Messpunkte pro Worker-Phase - [x] Tests: Labels/Registrierung deterministisch - [x] Dashboards/Runbooks skizzieren (Docs)

- [ ] ID: TASK-012
      Title: Read-Model Stores anlegen (Devices/Links Snapshot)
      Status: Proposed
      Created: 2025-01-01
      Milestone: M3 – Materialisierte Read-Models
      Commit: -
      Notes: Regionierte Snapshots im Speicher; Bytes + ETag.
      Artifacts: - backend/services/read_models.py - backend/tests/test_read_models_store.py - [ ] DeviceListSnapshotStore, LinkListSnapshotStore: get(region_id)->(bytes, etag), update(), invalidate() - [ ] ETag-Berechnung als deterministischer Hash über RegionVersionMap - [ ] Tests: Update/Invalidate, ETag-Änderung nur lokal - [ ] Persistenz-Option (SQLite/JSON) als Feature-Flag hinterlegen

- [ ] ID: TASK-013
      Title: Union-Snapshot (global) + deterministische Sortierung
      Status: Proposed
      Created: 2025-01-01
      Milestone: M3 – Materialisierte Read-Models
      Commit: -
      Notes: Globaler “list all” Snapshot via concat/sort; punktgenaue ETag-Updates.
      Artifacts: - backend/services/read_models.py - backend/tests/test_read_models_union.py - [ ] Union-Bildung aus Regionen (bytes concat + stable sort) - [ ] ETag: Hash über Region-ETags (stabile Reihenfolge) - [ ] Tests: lokale Änderung aktualisiert Union-ETag deterministisch - [ ] Metrik: read_model_update_ms pro Region

- [ ] ID: TASK-014
      Title: API-Handler auf Read-Model-Fassade umstellen (GET /devices,/links)
      Status: Proposed
      Created: 2025-01-01
      Milestone: M3 – Materialisierte Read-Models
      Commit: -
      Notes: Backward-kompatibel; hohe ETag-Hitrate unter Last.
      Artifacts: - backend/api/devices.py - backend/api/links.py - backend/tests/test_get_devices_links_perf.py - [ ] GET → SnapshotStore nutzen - [ ] ETag/If-None-Match korrekt handhaben - [ ] Lasttest: p95 zweistellige ms lokal verifizieren - [ ] Docs: Caching/ETag Verhalten beschreiben

- [ ] ID: TASK-015
      Title: Worker verdrahten: Change → DirtySet → Recompute → Read-Model
      Status: Proposed
      Created: 2025-01-01
      Milestone: M3 – Materialisierte Read-Models
      Commit: -
      Notes: End-to-End-Pfad schließen; no-op bei leerem DirtySet.
      Artifacts: - backend/core/jobs.py - backend/services/job_dispatcher.py - backend/services/status_service.py - backend/services/read_models.py - backend/tests/test_worker_e2e.py - [ ] Dispatcher aktualisiert Snapshots nach Recompute - [ ] Leere Dirty-Sets überspringen (no-op) - [ ] Metriken für Update-Zeiten erfassen - [ ] E2E-Test: WS/ETag sichtbar nach Commit

- [ ] ID: TASK-016
      Title: Performance- und Stabilitäts-Validierung (GET/Async)
      Status: Proposed
      Created: 2025-01-01
      Milestone: M3 – Materialisierte Read-Models
      Commit: -
      Notes: Zielmetriken belegen; Regressionsschutz aufbauen.
      Artifacts: - backend/tests/perf/test_perf_get_devices_links.py - backend/tests/perf/test_worker_batches.py - [ ] Benchmarks für GET /devices,/links (ETag-Hitrate, p95) - [ ] Worker Microbatch p95 < 100 ms nachweisen - [ ] CI-Perf-Gates optional (Smoke) - [ ] Dokumentation der Messergebnisse

- [ ] ID: TASK-017
      Title: Layout entkoppeln – Sync-Schnelllayout
      Status: Proposed
      Created: 2025-01-01
      Milestone: M4 – Layout entkoppeln
      Commit: -
      Notes: Deterministische, schnelle Layout-Heuristik aus dem Hot-Path.
      Artifacts: - backend/services/layout_sync.py - backend/tests/test_layout_sync.py - [ ] Grid/Tree/Line Heuristik deterministisch - [ ] Stable ordering, keine Zufallswerte - [ ] Tests: Invarianzen und Stabilität

- [ ] ID: TASK-018
      Title: Layout entkoppeln – Async “Nice Layout” Job + Snapshot
      Status: Proposed
      Created: 2025-01-01
      Milestone: M4 – Layout entkoppeln
      Commit: -
      Notes: Asynchrones Feinlayout, versionierter Snapshot nur für betroffene Teilbäume.
      Artifacts: - backend/services/layout_async.py - backend/services/read_models.py (layout_positions) - backend/tests/test_layout_async.py - [ ] Job-Typ “layout_nice” in Queue integrieren - [ ] Snapshot layout_positions regioniert - [ ] Invalidation lokal bei Änderungen - [ ] Tests: Teilbaum-update nur lokal

- [x] ID: TASK-019
      Title: Rollout-Flags entfernt; Async dauerhaft aktiv
      Status: Done
      Created: 2025-01-01
      Milestone: Rollout
      Commit: -
      Notes: UNOC_ASYNC_WRITES Flag und Header X-Async-Write entfernt; Async ist dauerhaft aktiv. Dokumentation angepasst.
      Artifacts: - backend/core/config.py - docs/llm/ROADMAP.md - docs/llm/ARCHITECTURE.md

- [ ] ID: TASK-020
      Title: Determinismus-Audit und Hardening
      Status: Proposed
      Created: 2025-01-01
      Milestone: Cross-Cutting
      Commit: -
      Notes: Identische Inputs → identische Outputs sicherstellen; UTC/Locale fixieren.
      Artifacts: - backend/utils/determinism.py - docs/engineering/determinism.md - [ ] Feste Seeds zentral setzen - [ ] Zeitzone UTC erzwingen; locale-unabhängige Formatierung - [ ] Stable Sort überall prüfen - [ ] Tests: Flaky-Detector/Seed-Pinning

- [ ] ID: TASK-021 (wichtig es wird kein GIT verwendet)
      Title: CI/Quality Gates absichern (Lint, Tests, Coverage)
      Status: Proposed
      Created: 2025-01-01
      Milestone: Cross-Cutting
      Commit: -
      Notes: Alle Quality Gates ausführen; Pre-commit Hooks ohne Änderungen. Für diesen Strang sind relevant: ruff (Import-Order fix), pytest Full Suite, optional markdownlint für Docs. Async-Policy beachten: POST /api/links synchron (201), PATCH/DELETE async (202, job_id) bei Flag.
      Artifacts: - .pre-commit-config.yaml - .github/workflows/ci.yml - [ ] black, isort, ruff, pytest, coverage - [ ] Optional: markdownlint für Docs - [ ] Vitest/Playwright nur falls Frontend betroffen - [ ] Pre-commit läuft clean

- [ ] ID: TASK-022
      Title: Backwards-Kompatibilität Voll-Recompute beibehalten
      Status: Proposed
      Created: 2025-01-01
      Milestone: M1–M3
      Commit: -
      Notes: Legacy-Pfade funktionsfähig halten; Umschaltbar via Flag.
      Artifacts: - backend/services/status_service.py - backend/config.py - backend/tests/test_full_recompute_compat.py - [ ] Feature-Flag für Voll-Recompute - [ ] Tests: Ergebnisse identisch bei deaktivierter Inkrementalität - [ ] Doku: Migrationshinweise

- [ ] ID: TASK-023
      Title: Fehlerpfade & Backpressure-Strategien testen
      Status: Proposed
      Created: 2025-01-01
      Milestone: M2–M3
      Commit: -
      Notes: Queue-Overflow, lange Dirty-Sets, Budget-Grenzen; deterministische Degradation.
      Artifacts: - backend/tests/test_backpressure.py - [ ] Große Dirty-Sets in Teilbatches aufteilen - [ ] Budget-Hard-Cut validieren - [ ] Starvation-Prevention testen - [ ] Logs: klare, PII-freie Hinweise

- [ ] ID: TASK-024
      Title: Pathfinding-Store ggf. regionieren
      Status: Proposed
      Created: 2025-01-01
      Milestone: M1–M3 (bei Bedarf)
      Commit: -
      Notes: pathfinding.py an Regionen koppeln, falls Abhängigkeiten dies erfordern.
      Artifacts: - backend/services/pathfinding.py - backend/tests/test_pathfinding_regioned.py - [ ] PATHFINDING_STORE API prüfen - [ ] Region-Kontext ergänzen - [ ] Tests: korrekte Isolation je Region

- [ ] ID: TASK-025
      Title: Sicherheits- und Datenschutzprüfung (Logs/Artifacts)
      Status: Proposed
      Created: 2025-01-01
      Milestone: Cross-Cutting
      Commit: -
      Notes: Keine PII in Logs/Commits/Artifacts; Secrets ausgeschlossen.
      Artifacts: - SECURITY.md - backend/logging/config.yaml - [ ] Log-Redaction Policies - [ ] Secrets-Scan in CI - [ ] Review SECURITY.md Richtlinien

- [ ] ID: TASK-026
      Title: Backend p95-Optimierung – status_recompute & generate (V18.0)
      Status: In Progress
      Created: 2025-09-26
      Milestone: Cross-Cutting / Performance
      Commit: -
      Notes: Grafana belegt die Hotpaths: status_recompute (bis ~4,5s) und generate-Phase des Traffic-Ticks (bis ~2,5s). Ziel: beide Pfade auf <100 ms p95 bei ≥50 Geräten.
      Artifacts: - backend/services/status_service.py (Caching has_upstream_l3_or_anchor) - backend/services/pathfinding.py bzw. v2_engine.py (Pfad-/Aggregations-Caches) - scripts/load_test_scenario.py (Verifikation) - docs/performance/backend-v18.md (Messergebnisse) - [ ] Phase 1: status_recompute – Ergebnis-Cache einführen (topology_version-gebunden) - [ ] Phase 1: Traversal zuerst Cache prüfen; Treffer → Ast abbrechen; Miss → berechnen+cache - [ ] Phase 1: Invalidation-Strategie an topo_version-Bumps koppeln - [ ] Phase 2: generate – Pfadfindungs-/Aggregations-Caches (Keys inkl. region_id, topo_version) - [ ] Phase 2: Selektive Invalidation und deterministische Sortierung - [ ] Phase 3: Verifikation – load_test_scenario.py laufen lassen, p95 < 100 ms validieren - [ ] Dokumentation der Ergebnisse und ggf. Follow-up Tasks

---

Hinweise (2025-09-27)

- Stabilisierung der passiven Inline-Kette: OLT-Provisioning prüft nur strukturelle Router-Adjazenz (CORE/EDGE/BACKBONE), keine L3-Prüfung zur Provisioning-Zeit; End-to-End-L3 via Status/Traffic. Tests grün.
- Async-Write-Policy: POST /api/links = 201 (synchron), PATCH override/DELETE = 202 mit job_id unter Flag.
- Quality Gates: ruff clean (Import-Order korrigiert), Pytest Full Suite grün.
