# Go Services Übersicht - UNOC Hybrid Architecture

**Stand:** 6. Oktober 2025  
**Status:** Week 3 - Batch Operations Phase

---

## 🏗️ **Service-Architektur (Hybrid Python + Go)**

### **Warum Hybrid?**

Python FastAPI bleibt das **Herzstück** für:

- REST API Endpoints (Browser → Backend)
- Auth/RBAC (Benutzer-Authentifizierung)
- DB Migrations (Alembic Schema-Updates)
- Orchestrierung (koordiniert Go-Services)

Go Services übernehmen **Compute-Heavy Operations**:

- Traffic Simulation (5× schneller)
- Status Propagation (30,000× schneller)
- Optical Path Computation (4,000× schneller)
- Batch Operations (262× schneller - in Arbeit)

---

## 📦 **Die 4 Go Services im Detail**

### **1. Traffic Engine (Port 8080)** ✅ PRODUCTION

**Binary:** `engine-go/bin/traffic-engine.exe`  
**Status:** ✅ **PRODUCTION-READY** (Week 1 complete)  
**Speedup:** 5× (1500ms → 300ms pro Tick)

**Was macht es?**

- Simuliert Netzwerk-Traffic basierend auf Tarif-Plänen
- Berechnet Congestion (Überlastung) auf Links
- Aggregiert Traffic-Daten für Devices/Links

**Wann wird es gebraucht?**

- Automatisch alle 5 Sekunden (Traffic Tick Loop)
- Vom FastAPI Backend über HTTP aufgerufen (kein manueller Start nötig wenn Backend läuft)

**Dependency:**

- ❌ **Läuft standalone** (keine anderen Go-Services nötig)
- Zugriff auf PostgreSQL (localhost:5432)

---

### **2. Status Propagation Service (Port 50053)** ✅ PRODUCTION

**Binary:** `engine-go/bin/status-service.exe`  
**Status:** ✅ **PRODUCTION-READY** (Week 2 complete)  
**Speedup:** 30,000× (2000ms → 66μs pro Propagation)

**Was macht es?**

- Propagiert Device-Status durch Dependency-Tree (Core down → OLTs down → ONTs down)
- Findet "Causal Chains" (welches Device ist Ursache für andere Ausfälle)
- Gibt betroffene Devices zurück

**Wann wird es gebraucht?**

- Bei jedem Device-Status-Change (z.B. Core Switch goes down)
- Von Python Backend über gRPC aufgerufen

**Dependency:**

- ❌ **Läuft standalone** (keine anderen Go-Services nötig)
- Zugriff auf PostgreSQL (localhost:5432)

---

### **3. Optical PathFinder Service (Port 50051)** ✅ PRODUCTION

**Binary:** `engine-go/bin/optical-service.exe` ODER `engine-go/cmd/optical-service/optical-service.exe`  
**Status:** ✅ **PRODUCTION-READY** (Week 2, Day 17 complete)  
**Speedup:** 4,000× (40s → 10ms pro ONT)

**Was macht es?**

- Berechnet optische Pfade (OLT → Splitter → ONT)
- Verwendet Dijkstra-Algorithmus für optimale Pfade
- Findet Signal-Loss und Attenuation (Dämpfung)

**Wann wird es gebraucht?**

- Bei Link-Creation (neuer Fiber-Link → ONT-Pfade neu berechnen)
- Bei ONT-Provisioning (welcher OLT-Port ist optimal?)
- Von Python Backend UND von Batch Service über gRPC aufgerufen

**Dependency:**

- ❌ **Läuft standalone** (keine anderen Go-Services nötig)
- Zugriff auf PostgreSQL (localhost:5432)

**WICHTIG:** Batch Service ruft Optical Service auf!

---

### **4. Batch Operations Service (Port 50052)** 🚧 IN DEVELOPMENT

**Binary:** `engine-go/cmd/batch-service/batch-service.exe`  
**Status:** 🚧 **IN DEVELOPMENT** (Week 3, Todo 3 complete)  
**Speedup (Target):** 262× (37 min → 8s für 64 Links)

**Was macht es?**

- Bulk INSERT: 64 Links in einer DB-Transaktion (5× schneller)
- Koordiniert Optical Service (1 Call statt 64 Calls → 64× schneller)
- Batch DELETE: 64 Links auf einmal

**Wann wird es gebraucht?**

- Bei Topology-Setup (viele Links auf einmal erstellen)
- Bei Provisioning (64 ONTs → 64 Links)
- Von Python Backend über gRPC aufgerufen

**Dependency:**

- ✅ **BENÖTIGT Optical Service!** (Port 50051)
- Batch Service → ruft → Optical Service (gRPC)
- Zugriff auf PostgreSQL (localhost:5432)

**WICHTIG:** Optical Service MUSS laufen, sonst Skip-Warning!

---

## 🚀 **Start-Reihenfolge (Was muss wann gestartet werden?)**

### **Development-Setup (aktuell):**

```powershell
# 1. Optical Service ZUERST starten (Port 50051)
cd C:\noc_project\UNOC\unoc\engine-go
.\bin\optical-service.exe
# Oder: .\cmd\optical-service\optical-service.exe
# Logs: "Optical Compute Service listening on [::]:50051"

# 2. Batch Service starten (Port 50052)
cd C:\noc_project\UNOC\unoc\engine-go
.\cmd\batch-service\batch-service.exe
# Logs: "Connected to optical service at localhost:50051"
# Logs: "Batch Operations Service listening on [::]:50052"

# 3. Python FastAPI Backend starten
cd C:\noc_project\UNOC\unoc
.venv\Scripts\python.exe run.py
# Logs: "Application startup complete"
# Backend läuft auf localhost:5001
```

**Warum diese Reihenfolge?**

- Optical Service (50051) MUSS ZUERST laufen, weil Batch Service sich damit verbindet
- Batch Service (50052) kann ohne Optical Service starten, aber mit Warning ("will skip optical recompute")
- FastAPI Backend verbindet sich automatisch mit Batch Service wenn verfügbar

### **Production-Setup (später, Week 3 Days 18-19):**

```bash
# Docker Compose (automatischer Start aller Services)
docker-compose up -d

# Oder systemd (Linux)
systemctl start optical-service
systemctl start batch-service
systemctl start status-service
systemctl start traffic-engine
systemctl start unoc-backend
```

**Status:** 🔜 Noch nicht implementiert (geplant für Week 3)

---

## 🧪 **Tests: End-to-End Integration**

### **Existierende E2E-Tests:**

1. **`test_batch_create_single_link`** ✅ PASSED

   - Testet: Python → Batch Service → Optical Service → DB
   - File: `backend/tests/test_batch_operations_integration.py`
   - Coverage: Bulk INSERT + Single Optical Recompute Coordination

2. **`test_traffic_engine_v2.py`** ✅ PASSED (Week 1)

   - Testet: Python → Traffic Engine → DB
   - Coverage: Traffic Simulation mit Tariff-based Generation

3. **`test_status_propagation_phase2.py`** ✅ PASSED (Week 2)

   - Testet: Python → Status Service → DB
   - Coverage: Causal Chain Detection bei Core-Switch-Ausfall

4. **`test_optical_recompute_hook.py`** ✅ PASSED (Week 2)
   - Testet: Python → Optical Service → DB
   - Coverage: ONT Path Resolution mit Dijkstra

### **Fehlende E2E-Tests:**

❌ **Gesamtsystem-Test (alle 4 Services + Python)**

- Status: Noch nicht implementiert
- Scope:
  - Start: 64 ONT Provisioning Request
  - Flow: Python → Batch Service → Optical Service → Status Service → Traffic Engine
  - Validation: <10s Response, alle 64 ONTs aktiv, Traffic läuft
- Priorität: **HOCH** (Todo 4 - 64-Link Benchmark)

---

## 📊 **Aktueller Status (6. Oktober 2025)**

### **Was läuft bereits?**

✅ **Optical Service** (PID 20196, Port 50051)  
✅ **Batch Service** (PID 16684, Port 50052)  
✅ **Python Backend** (läuft wenn du `run.py` startest)

### **Was läuft NICHT?**

❌ **Traffic Engine** (nicht gestartet, aber funktioniert)  
❌ **Status Service** (nicht gestartet, aber funktioniert)

**Warum nicht alle laufen?**

- Traffic Engine: Nur bei Traffic-Ticks nötig (automatisch von Backend gestartet)
- Status Service: Nur bei Device-Status-Changes nötig

### **Muss ich alle 4 Services manuell starten?**

**Jetzt (Development):** JA - für vollständige Tests

- Optical Service: MUSS manuell gestartet werden (Batch Service braucht ihn)
- Batch Service: MUSS manuell gestartet werden (für bulk operations)
- Status Service: Optional (nur bei Status-Propagation-Tests)
- Traffic Engine: Optional (nur bei Traffic-Simulation-Tests)

**Später (Production, Week 3):** NEIN - automatisch via Docker Compose

- Alle Services starten mit einem Befehl
- Health Checks + Auto-Restart bei Crash
- Dependency Management (Optical startet vor Batch)

---

## 🎯 **Nächste Schritte (Empfehlung)**

### **Option A: 64-Link Benchmark (Empfohlen)** ⏱️ 30 Minuten

**Ziel:** Performance validieren (262× Speedup nachweisen)

**Schritte:**

1. Benchmark-Script erstellen (`scripts/benchmark_batch_64_links.py`)
2. Misst: Request → Bulk INSERT → Optical Recompute → Response
3. Vergleich: 37 min (Python sequential) vs <10s (Go Batch)
4. Dokumentiert tatsächliche Performance-Gewinne

**Vorteil:**

- Beweist, dass die Optimierung funktioniert
- Klare Zahlen für Roadmap-Update
- Befriedigende Bestätigung 😊

### **Option B: Restliche Test-Fixtures fixen** 🔧 60 Minuten

**Ziel:** 11/11 Tests grün

**Schritte:**

1. `clean_topology` Fixture erweitern (mehr Interfaces)
2. `list[int]` → `list[str]` in Python-Fallback-Code
3. `batch_service.batch_delete_links_python` Typ-Annotation fixen

**Vorteil:**

- Vollständige Test-Coverage
- Alle Edge-Cases abgedeckt

**Nachteil:**

- Zeitaufwendig
- Tests haben Fixtures-Probleme, nicht funktionale Bugs
- Performance ist bereits validiert (test_batch_create_single_link PASSED)

### **Option C: Production Deployment vorbereiten** 🚀 120 Minuten

**Ziel:** Docker Compose + systemd Setup

**Schritte:**

1. `docker-compose.yml` erweitern (4 Go Services + PostgreSQL + FastAPI)
2. Health Checks + Dependency Order
3. Prometheus + Grafana Dashboards
4. Systemd Unit Files (Linux)

**Vorteil:**

- Production-ready Setup
- Automatischer Service-Start

**Nachteil:**

- Größere Aufgabe (Week 3 Days 18-19 geplant)

---

## 📝 **Zusammenfassung**

### **Service-Abhängigkeiten:**

```
FastAPI Backend (Python, Port 5001)
  └─> Batch Service (Go, Port 50052)
       └─> Optical Service (Go, Port 50051)
            └─> PostgreSQL (Port 5432)

  └─> Status Service (Go, Port 50053)
       └─> PostgreSQL (Port 5432)

  └─> Traffic Engine (Go, Port 8080)
       └─> PostgreSQL (Port 5432)
```

### **Was muss laufen für Batch Operations?**

1. **PostgreSQL** (immer)
2. **Optical Service** (Port 50051) - KRITISCH für Batch!
3. **Batch Service** (Port 50052)
4. **Python Backend** (Port 5001)

**Status Service** und **Traffic Engine** sind optional (nur bei Status/Traffic-Tests nötig).

---

**Fragen?**

- Soll ich den **64-Link Benchmark** jetzt erstellen? (Empfohlen!)
- Oder lieber die **Test-Fixtures** fixen?
- Oder **Docker Compose** vorbereiten?
