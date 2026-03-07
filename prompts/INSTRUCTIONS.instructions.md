# 🧠 Copilot Instructions: Go Port Summary Service

## 🎯 Projektziel
Implementiere einen **Go-basierten Port Summary Service** (Port 50054), der Geräte-, Interface- und Link-Informationen performant zusammenfasst und über gRPC bereitstellt.  
Der Service muss **Production-Grade** sein, skalieren auf 10.000+ Devices und Event-Driven Updates aus PostgreSQL verarbeiten.  
Integration erfolgt über das bestehende Python-Backend (FastAPI).

---

## 📋 Roadmap & Task-Management

### Verhalten des Agenten
- Erstelle automatisch eine **Roadmap** mit Phasen:
  - Phase 1: Core Go Service
  - Phase 2: Event-Driven Updates
  - Phase 3: Python Integration
  - Phase 4: Tests & Benchmarks
- Generiere **Tasks pro Phase** (inkl. betroffene Dateien, Status, Testabdeckung).
- Aktualisiere Roadmap & Tasks **ständig selbstständig**:
  - Bei neuen Anforderungen → neue Tasks
  - Bei Code-Änderungen → Fortschritt anpassen
  - Bei Tests → Status aktualisieren
- Markiere erledigte Tasks automatisch als `done`.

---

## 🛠 Implementierungsdetails

### Backend (Go)
- `port_summary.proto` definieren
- gRPC-Methoden:
  - `GetPortSummary(deviceID)`
  - `GetBulkPortSummary(deviceIDs[])`
  - `InvalidateCache(deviceID)`
- In-Memory State:
  - `devices`, `interfaces`, `links`
  - `ponOccupancy` (oltID → ponIfID → count)
  - `opticalPaths` (ontID → ponIfID, precomputed)
- Event Listener (PostgreSQL NOTIFY):
  - `link_created/deleted` → recompute OLT
  - `device_provisioned` → update optical path
  - `topology_version_change` → full reload
- Thread-Safe (RWMutex)

### Python Integration
- gRPC Client: `backend/clients/port_summary_client.py`
- API Endpoint: `/api/ports/summary`
- Fallback-Logik (wie Traffic Engine)

---

## ⚡ Performance-Ziele
| Devices | Current (Python) | Target (Go) | Speedup |
|---------|------------------|-------------|---------|
| 70      | 250–700ms        | 5–10ms      | 50–100× |
| 200     | 2–5s             | 10–20ms     | 200×    |
| 1000    | 10–30s (timeout) | 20–50ms     | 500×    |

---

## 📅 Zeitplan (Week 3)
- **Day 18**: Core Service (Proto, Loader, Counting, gRPC Server)
- **Day 19**: Event Integration (Listener, Cache Invalidation, Precomputation, Tests)
- **Day 20**: Python Integration (Client, API Migration, E2E Tests)

---

## 🧪 Teststrategie
- Unit-Tests für Counting Logic
- Integrationstests (gRPC Client ↔ Go Service)
- E2E Tests (Python → Go → DB)
- Performance-Benchmarks (70, 200, 1000 Devices)

---

## 🚧 Risiken & Mitigation
- **Optical Path Complexity** → Reuse PathFinder Service
- **Memory Usage** (~100MB bei 10k Devices) → akzeptabel
- **Event Race Conditions** → Mutex + Event Queue
- **Integration Issues** → Copy Traffic Engine Client Pattern

---

## 🚀 Agent-Verhalten
- Nutze `#edit`, `#fetch`, `#test`, `#run` für Umsetzung
- Halte Roadmap & Tasks **immer aktuell**
- Ergänze automatisch Dokumentation (README, Docstrings)
- Schlage Refactorings & Optimierungen vor
- Änderungen nur nach Bestätigung anwenden (außer Tests & Task-Updates)

---

## 📣 Beispiel-Task (automatisch generiert)
```json
{
  "task_id": "task_018",
  "title": "Implementiere gRPC Server für Port Summary",
  "status": "in progress",
  "files": ["go/port_summary_service.go", "proto/port_summary.proto"],
  "phase": "Backend",
  "description": "Erstelle gRPC Server mit GetPortSummary und GetBulkPortSummary",
  "test_coverage": "expected ≥ 90%"
}
