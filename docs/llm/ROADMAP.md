Roadmap: Inkrementelle Sync-/Async-Architektur für p95 < 100 ms

Vision

- Schreib-APIs antworten sofort (202 + Korrelation), Arbeit läuft deterministisch in ≤100 ms Microbatches, nur betroffene Teilgraphen werden inkrementell neu berechnet.
- Lese-APIs bedienen ausschließlich materialisierte Snapshots (ETag, regioniert) mit lokaler Invalidierung.
- Zielwerte: p95 Sync-Antwort < 100 ms; p95 GET devices/links zweistellige ms; Worker-Microbatch p95 < 100 ms.

Leitprinzipien

- Determinismus zuerst: stabile Reihenfolgen (Toposort/BFS), single sequenced Worker, Microbatching, feste Seeds, UTC, stabile Sortierung.
- Lokalisierung: Region-Versionierung (Connected Components/Gates), Dirty-Set statt Full-Scan.
- Entkopplung: Sync-Pfade persistieren + enqueuen; Compute und Read-Model-Updates asynchron.
- Materialisierung: Read-Models als Snapshots (bytes + ETag) pro Region und globaler Union.
- Keine Architektur-Änderungen außerhalb des Scopes; kleine, atomare Schritte mit Tests und Metriken.

Meilensteine

M1: Dirty-Set + Region-Versionierung (Basis für Inkrementalität)

- Ziel
  - Recompute und Generate laufen auf Dirty-Sets innerhalb betroffener Regionen; globale Version wird durch Region-Versionen ersetzt.
- Deliverables
  - backend/services/graph_index.py
    - GraphIndex: build(), neighbors_device(), neighbors_link(), region_id_of_device(), affected_region_for_devices(), dirty_set_for_change()
  - RegionVersionMap: bump(region_id), version(region_id)
  - status_service.py: recompute_dirty(dirty: DirtySet) (Toposort/BFS, in-round Memoization)
  - v2_engine.py: prepare_dirty(dirty), aggregate_dirty(dirty)
- Tests
  - backend/tests/test_dirty_set_minimal.py: gezielte Änderungen treffen nur lokale Nachbarschaft; O(|DirtySet|) ohne globale Scans.
- Akzeptanzkriterien
  - Region-Bumps nur lokal; alte Voll-Recompute weiter kompatibel vorhanden.

Stand der Dinge (2025-09-27)

- GraphIndex + RegionVersionMap sind implementiert (backend/services/graph_index.py) und durch Minimaltests abgedeckt (backend/tests/test_graph_index_minimal.py).
- status_service.recompute_dirty ist umgesetzt: deterministische BFS-Expansion vom Dirty-Set mit in-Runden-Baseline/Memoization; Delegation an recompute_devices_status. Tests verifizieren Lokalität, Determinismus und Parität mit Voll-Recompute (backend/tests/test_recompute_dirty.py). Full Suite grün.

M2: Asynchrones Commit-Muster + Microbatch-Worker

Status: Abgeschlossen (2025-09-26)

- Ziel
  - Schreib-APIs antworten nach Persist + enqueue sofort; Worker coalesced Microbatches ≤100 ms deterministisch.
- Deliverables
  - backend/core/jobs.py: Job, JobQueue (enqueue, next_microbatch(budget_ms=50), complete), JobWorker.run_once()
  - backend/services/job_dispatcher.py: dispatch(job, graph) → DirtySet → recompute_dirty + traffic-dirty + Read-Model-Update
  - API: devices.py, links.py – Async-Write ist permanenter Standard.
    - Links: PATCH override und DELETE delete liefern 202 (\{job_id, accepted:true\}) und werden in die Queue eingereiht.
    - Links: POST create bleibt bewusst synchron (201), um unmittelbare Topologie-Komposition in derselben Request-Sequenz zu erlauben.
  - main.py: Worker starten/stoppen, Microbatch 50–100 ms
  - Konfiguration: UNOC_BATCH_BUDGET_MS=50 (Budget für Microbatches)
- Tests
  - backend/tests/test_async_provision_api.py: 202-Fluss, Queue-Only, WS/ETag-Änderung beobachtbar
- Metriken
  - job_queue_depth, job_batch_duration_ms, dirty_set_size_histogram, p95 worker-phasen
- Akzeptanzkriterien
  - p95 Schreib-APIs < 100 ms; Worker-Batches << 100 ms; deterministische Reihenfolge; keine Starvation.

Stand der Dinge (2025-09-26)

- In-Memory JobQueue + Worker-Skelett ist implementiert (backend/core/jobs.py, backend/services/worker.py) und durch Minimaltests abgedeckt (backend/tests/test_job_queue_minimal.py). Ordnung ist deterministisch (FIFO), Microbatching ohne Zeitabhängigkeit in Tests.
- Async-Write für Link-Pfade ist jetzt permanenter Standard: `PATCH /api/links/{id}/override` und `DELETE /api/links/{id}` enqueuen Jobs (`202 {accepted:true, job_id}`), Persistenz erfolgt deterministisch im Worker. `POST /api/links` bleibt synchron (201) für deterministische Komposition.
- Worker-Lifecycle ist unter FastAPI-Lifespan verdrahtet (backend/main.py): single-sequenced Loop, Microbatch-Budget via `UNOC_BATCH_BUDGET_MS` (Default 50 ms), Backoff bei Idle. Fehler sind fail-safe (keine Crashes im Lifespan).
- Prometheus-Metriken ergänzt (backend/api/endpoints/metrics.py):
  - `job_queue_depth` (Gauge)
  - `job_worker_batch_size` (Histogram)
  - `job_worker_batch_duration_seconds` (Histogram)
  - `jobs_processed_total{kind}` (Counter)

Update (2025-09-27)

- Policy-Klarstellung: `POST /api/links` bleibt synchron (201). `PATCH /api/links/{id}/override` und `DELETE /api/links/{id}` liefern 202 mit `job_id` als permanenter Standard.
- Provisioning: OLT-Guard prüft jetzt direkte strukturelle Adjazenz zu Routern (CORE/EDGE/BACKBONE), keine L3-Diagnostik zur Provisioning-Zeit; End-to-End-L3 wird später durch Status/Traffic erzwungen. Damit sind passive Inline-Kettentests stabil.
- Lint/CI: Import-Order bereinigt; Quality Gates (ruff + Tests) grün.

M3: Materialisierte Read-Models (devices/links)

- Ziel
  - GET bleibt zweistellig ms-stabil über Caches; nur lokale Invalidierungen bei Änderungen.
- Deliverables
  - backend/services/read_models.py
    - DeviceListSnapshotStore, LinkListSnapshotStore: get(region_id)->(bytes, etag), update(), invalidate()
  - Regionierte Snapshots + globaler Union-Snapshot (bytes concat + sort deterministisch)
  - ETag: Hash aus Region-Versionen; lokale Updates aktualisieren Union-ETag punktgenau
  - API-Handler nutzt Read-Model-Facade (Backward-kompatibel)
- Akzeptanzkriterien
  - p95 GET /devices, /links zweistellige ms; hohe ETag-Hitrate unter Last.

Stand der Dinge (2025-09-26)

- Vorarbeit vorhanden: Vorserialisierte Caches + ETag für /devices und /links (global).
- Nächste Schritte: Regionierte Snapshot-Stores und unionisierter Snapshot mit deterministischer Sortierung.

M4: Layout entkoppeln (optional, orthogonal)

- Ziel
  - positions aus Hot-Path; UI friert nicht.
- Deliverables
  - Sync: schnelle deterministische Positionen (grid/tree/line)
  - Async: “nice layout” Job; materialisierter, versionierter Layout-Snapshot; nur betroffene Teilbäume neu layouten

Architektur- und Implementierungsdetails

Dirty-Set und Regionen

- Dependenz-Graph: Device → Interfaces → Links → Neighbor Devices (Reverse-Edges halten)
- L3-Anchor/Reachability: pro Gerät “has_upstream_l3_or_anchor” inkl. Begründungs-Kante
- Dirty-Set-Ermittlung: direkte Änderungen + Nachbarschaft bis zu Gates (z. B. L3)
- Region-Versionierung: RegionVersionMap statt globaler topo_version; Read-Caches invalidieren nur betroffene Regionen
- affected_region_for_devices: wählt die Region des lexikographisch ersten Geräts; bei leerem Set → "r:unknown:0" (deterministisch).
- No-Op-Semantik: Leere Dirty-Sets werden übersprungen (keine Recompute-/Read-Model-Aktivität).

Async-Pfade und Backpressure

- Microbatching: 50–100 ms Tick-Coalescing, harte Budgetgrenze; große Dirty-Sets aufteilen
- UI: “queued + correlation id”, WS-Events nach Commit
- Keine konkurrierenden Voll-Recomputes; ein sequenzierter Worker

Read-Models

- Snapshots: devices_list (mit/ohne interfaces), links_list, layout_positions
- In-Memory + optional persisted (SQLite/JSON blob) je Region-Version
- GET-Pfade liefern nur Snapshots inkl. ETag (Region-Version-basiert), Union-Snapshot vorerst für “list all”

Schnittstellen und Dateien

- Writes
  - devices.py: POST/PUT/PATCH/POST provision (Phase 2: async 202)
  - links.py: POST/PUT/PATCH/DELETE
- Services
  - status_service.py, v2_engine.py, pathfinding.py (PATHFINDING_STORE ggf. regionieren)
  - backend/services/graph_index.py (neu)
  - backend/core/jobs.py (neu)
  - backend/services/job_dispatcher.py (neu)
  - backend/services/read_models.py (neu)
- Startup
  - main.py: Worker-Lifecycle deterministisch

Observability und Metriken

- dirty_set_size_histogram (optional in Iteration 1)
- job_queue_depth, job_batch_duration_ms (optional in Iteration 1)
- read_model_update_ms per Region (optional)
- p95: status_dirty, traffic_dirty, readmodel_update (optional)
- ETag-Hit-Rate, Invalidations pro Region (optional)

Risiken und Gegenmaßnahmen

- Komplexität Dirty-Graph/Regionen → inkrementell umsetzen (erst Dirty-Set, dann Regionen)
- Eventual Consistency → WS-Events + “Applying changes…” UX, hohe gefühlte Responsivität
- Testbarkeit → Unit-Tests für Gates, Microbatch-Order, Eventualitätsfenster
- Cache-Fallen → Memoization nur in-Runde; Aggregatscache erst nach funktionierender Inkrementalität

Nicht-Ziele

- Mehrere parallel arbeitende Worker (Lock-/Invalidation-Kosten, deterministische Ordnung gefährdet)
- Harte Global-Caches als Ersatz für Inkrementalität

Rollout-Plan

- Async-Write ist dauerhaft aktiviert; es gibt kein Rollout-Flag mehr.
- Der frühere Header `X-Async-Write` wurde entfernt.
- `POST /api/links` bleibt synchron (201).

Akzeptanzmetriken (Endzustand)

- p95 Sync-Provision/Link-Write: < 100 ms (Response 202 sofort)
- Worker: Microbatch p95 < 100 ms; Queue stabil (Durchsatz ≥ Eingangsrate)
- GET /devices, /links: p95 zweistellige ms; lokale Invalidierungen; hohe ETag-Hitrate

Validierungsschritte (klein & testbar)

- GraphIndex + RegionVersionMap + Unit-Tests (ohne Behavior-Änderung)
- JobQueue/Worker-Skelett + Dispatcher (noch unverdratet)
- Feature-Flag + 202-Pfad (Queue-Only), Sync-Pfad via X-Async-Write: 0
- Worker verdrahten: Change → DirtySet → recompute_dirty + traffic_dirty (no-op bei leerem DirtySet)
- Read-Model-Facade integrieren; Worker aktualisiert Region- und Union-Snapshots
- Sandbox: Async per Default; Tests behalten Sync über Header

Backend Performance Fokus – V18.0 „Zurück zum Backend“

- Grundlage (Grafana-Daten)
  - status_recompute p95/Max bis zu ~4,5 s bei wachsenden Topologien.
  - generate-Phase (Traffic-Tick) p95/Max bis zu ~2,5 s.
  - Schlussfolgerung: Primäre Flaschenhälse im Backend, nicht im Frontend.
- Zielsetzung
  - Beide Hotpaths unter 100 ms p95 bringen, auch bei 50+ Geräten.
- Phase 1: status_recompute radikal optimieren
  - Mehrschichtige Caches:
    - Cache-Schicht 1: Topologie-versionierter Graph-Cache (bereits vorhanden) als Basis.
    - Cache-Schicht 2: Ergebnis-Cache für has_upstream_l3_or_anchor je Gerät, gekoppelt an topology_version.
  - Traversal-Logik: Vor Expandieren eines Knotens zuerst Ergebnis-Cache prüfen; bei Treffer übernehmen und Ast abbrechen; bei Miss berechnen und Ergebnis im Cache ablegen.
  - Invalidation: Vollständiges Invalidieren/Version-Bump bei Topologie-Änderungen; deterministisch.
- Phase 2: generate-Phase radikal optimieren
  - Pfadfindungs-/Aggregations-Caches einführen, versioniert nach topology_version/Region.
  - Key-Ideen: (src, dst, constraints, region_id, topology_version) → Pfad/Teilstrom; selektive Invalidation.
- Phase 3: Verifizierung
  - Nach jeder Optimierung Lastszenario ausführen (load_test_scenario.py) und Metriken erfassen.
  - Erfolgskriterium: p95 status_recompute und generate < 100 ms bei ≥ 50 Geräten (stabil, reproduzierbar).
