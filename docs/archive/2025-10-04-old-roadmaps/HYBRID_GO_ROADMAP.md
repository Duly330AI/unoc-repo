# Hybrid Go Implementation Roadmap – Option C

**Version:** 1.0  
**Created:** 2025-10-03  
**Owner:** @agent + @duly3  
**Goal:** Scale UNOC backend to **1,000+ devices** with acceptable performance (<2s traffic tick, <1s status recompute)  
**Approach:** **Hybrid Architecture** – Traffic engine in Go, Status engine remains Python

---

## 🎯 Executive Summary

**Why Hybrid Go?**

Option A (Pure Python) load test results @ 200 devices:

- Traffic tick: **2.301s** → Projected 1000 devices: **11.6s** (❌ Target: <2s, Gap: 9.6s)
- Status recompute: **9.901s** → Projected 1000 devices: **50.0s** (❌ Target: <1s, Gap: 49s)

**Decision Rationale:**

1. **Traffic engine** is called **EVERY SECOND** (5s cycle = 17,280 calls/day)
   - Python bottleneck: 11.6s projected @ 1000 devices
   - Go target: <2s (6× speedup required, Go can deliver 10-50×)
   - High-frequency, low-complexity (graph traversal + arithmetic)
2. **Status engine** is called **ON-DEMAND** (~100 calls/day)
   - Python acceptable: 50s projected but infrequent
   - Complex business logic (provisioning, IPAM, dependencies)
   - Python ecosystem advantages (SQLModel, Pydantic, existing code)

**Hybrid Benefits:**

- ✅ **6-10× traffic speedup** (Go compiled, concurrent, no GIL)
- ✅ **Keep Python status engine** (complex logic, existing tests, rapid iteration)
- ✅ **Minimal rewrite** (only traffic, ~3,000 LOC vs 30,000 LOC full rewrite)
- ✅ **Gradual migration** (traffic first, status later if needed)
- ✅ **Best of both worlds** (Go performance + Python flexibility)

---

## 📊 Architecture Overview

### Current Architecture (Python-only)

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI (Python)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌─────────────────────────────┐ │
│  │  Status Engine (Py)  │  │  Traffic Engine (Py)        │ │
│  │  - evaluate_device   │  │  - build_adjacency()        │ │
│  │  - has_upstream_l3   │  │  - generate_flows()         │ │
│  │  - provision logic   │  │  - aggregate_device/link    │ │
│  │  - IPAM, VRF, routes │  │  - run_tick() every 5s     │ │
│  │  [COMPLEX, RARE]     │  │  [SIMPLE, FREQUENT]         │ │
│  └──────────────────────┘  └─────────────────────────────┘ │
│           │                            │                    │
│           └────────────┬───────────────┘                    │
│                        ▼                                    │
│                   PostgreSQL                                │
└─────────────────────────────────────────────────────────────┘
```

**Bottleneck:** Traffic engine called every 5s, Python too slow (2.3s @ 200 devices)

### Target Architecture (Hybrid Go)

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI (Python)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌─────────────────────────────┐ │
│  │  Status Engine (Py)  │  │  HTTP Client → Go Service   │ │
│  │  - evaluate_device   │  │  - POST /tick               │ │
│  │  - has_upstream_l3   │  │  - GET /snapshot            │ │
│  │  - provision logic   │  │  - WebSocket /events        │ │
│  │  - IPAM, VRF, routes │  │                             │ │
│  │  [KEEPS PYTHON]      │  │  [DELEGATES TO GO]          │ │
│  └──────────────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
                 ┌──────────────────────────────┐
                 │  Traffic Engine (Go)         │
                 │  - buildAdjacency()          │
                 │  - generateFlows()           │
                 │  - aggregateDeviceLink()     │
                 │  - runTick() goroutine       │
                 │  [GO PERFORMANCE]            │
                 └──────────────────────────────┘
                               │
                               ▼
                          PostgreSQL
```

**Key Changes:**

1. **Traffic engine** → Standalone Go microservice

   - HTTP/gRPC API for Python ↔ Go communication
   - Reads topology from PostgreSQL (direct connection)
   - Writes metrics/events back to PostgreSQL
   - Runs independent tick loop (no Python involvement)

2. **Status engine** → Remains in Python

   - No changes to business logic
   - Existing tests, provisioning, IPAM all unchanged
   - Can be optimized further if needed (low priority)

3. **Communication:**
   - Python → Go: POST `/tick` (trigger traffic generation)
   - Go → Python: WebSocket `/events` (congestion alerts, status changes)
   - Go → PostgreSQL: Direct read/write (bypass Python ORM overhead)

---

## 🎯 Milestones

### **Phase 1: Go Traffic Engine (Weeks 1-3)**

**Goal:** Implement Go traffic engine with same logic as Python v2_engine

- **M1.1:** Go project setup + PostgreSQL connection (Week 1)
- **M1.2:** Core algorithms (build_adjacency, generate_flows, aggregate) (Week 1-2)
- **M1.3:** HTTP API + Python client integration (Week 2)
- **M1.4:** Unit tests + integration tests (Week 2-3)
- **M1.5:** Load test @ 200 devices (validate <2s target) (Week 3)

**Deliverables:**

- `engine-go/` microservice (standalone binary)
- Python client: `backend/clients/traffic_go_client.py`
- Tests: `backend/tests/test_traffic_go_integration.py`
- Docs: `docs/architecture/TRAFFIC_GO_SERVICE.md`

### **Phase 2: Production Integration (Weeks 4-5)**

**Goal:** Deploy Go service alongside Python, validate production readiness

- **M2.1:** Docker containerization (Week 4)
- **M2.2:** Prometheus metrics + health checks (Week 4)
- **M2.3:** Production deployment (dev → staging → prod) (Week 5)
- **M2.4:** Load test @ 1000 devices (GO/NO-GO decision) (Week 5)

**Deliverables:**

- `docker-compose.yml` with Go service
- Metrics dashboard (Grafana)
- Production deployment guide
- 1000-device validation results

### **Phase 3: Optimization & Monitoring (Week 6)**

**Goal:** Fine-tune Go engine, monitor production, iterate

- **M3.1:** Profiling + optimization (goroutines, memory, DB queries)
- **M3.2:** Alerting + error handling
- **M3.3:** Documentation + runbooks

**Deliverables:**

- Performance tuning report
- Production runbook
- Final architecture docs

---

## ✅ Tasks (Detailed Breakdown)

### 🏗️ **Phase 1: Go Traffic Engine**

#### **HGO-001: Project Setup + PostgreSQL Connection**

**Priority:** 🔥 CRITICAL  
**Effort:** 2-3 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
Initialize Go project with modern tooling and PostgreSQL connection.

**Subtasks:**

1. [ ] Create `engine-go/` directory structure
   - `cmd/traffic-engine/` (main entry point)
   - `internal/` (private packages)
   - `pkg/` (public packages if needed)
   - `config/` (YAML/ENV config)
2. [ ] Go module setup (`go.mod`, `go.sum`)
   - Go 1.21+ (generics, better performance)
   - Dependencies: `github.com/lib/pq` (PostgreSQL driver)
   - `github.com/jmoiron/sqlx` (SQL extensions)
   - `github.com/spf13/viper` (config management)
3. [ ] PostgreSQL connection pool
   - Read DB credentials from ENV vars (match Python)
   - Connection pooling (max 20 connections)
   - Health check query (`SELECT 1`)
4. [ ] Basic logging setup
   - Structured logging (`zerolog` or `zap`)
   - Log levels (DEBUG, INFO, WARN, ERROR)
   - JSON output for production

**Success Criteria:**

- Go binary starts successfully
- Connects to PostgreSQL (same DB as Python)
- Logs connection status
- Graceful shutdown on SIGTERM

**Files:**

- `engine-go/cmd/traffic-engine/main.go`
- `engine-go/internal/db/postgres.go`
- `engine-go/internal/config/config.go`
- `engine-go/go.mod`

**Testing:**

- Manual: `go run cmd/traffic-engine/main.go`
- Check logs for successful DB connection

---

#### **HGO-002: Data Models (Device, Link, Interface, Tariff)**

**Priority:** 🔥 CRITICAL  
**Effort:** 2-3 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
Define Go structs matching Python SQLModel models for topology reading.

**Subtasks:**

1. [ ] Define Go structs for core models

   ```go
   type Device struct {
       ID              string    `db:"id"`
       Name            string    `db:"name"`
       Type            string    `db:"type"` // DeviceType enum
       Status          string    `db:"status"` // Status enum
       EffectiveStatus *string   `db:"effective_status"`
       TariffID        *int      `db:"tariff_id"`
       Provisioned     bool      `db:"provisioned"`
       // Add other fields as needed
   }

   type Link struct {
       ID              string  `db:"id"`
       AInterfaceID    string  `db:"a_interface_id"`
       BInterfaceID    string  `db:"b_interface_id"`
       Kind            string  `db:"kind"`
       Status          string  `db:"status"`
       EffectiveStatus *string `db:"effective_status"`
       // Add capacity fields
   }

   type Interface struct {
       ID       string `db:"id"`
       DeviceID string `db:"device_id"`
       Name     string `db:"name"`
       // Add port profile fields if needed
   }

   type Tariff struct {
       ID          int     `db:"id"`
       Name        string  `db:"name"`
       MaxDownMbps float64 `db:"max_down_mbps"`
       MaxUpMbps   float64 `db:"max_up_mbps"`
   }
   ```

2. [ ] Repository functions (read from DB)

   ```go
   func FetchAllDevices(db *sqlx.DB) ([]Device, error)
   func FetchAllLinks(db *sqlx.DB) ([]Link, error)
   func FetchAllInterfaces(db *sqlx.DB) ([]Interface, error)
   func FetchAllTariffs(db *sqlx.DB) ([]Tariff, error)
   ```

3. [ ] Index maps for fast lookups

   ```go
   type TopologyCache struct {
       Devices    map[string]*Device
       Links      map[string]*Link
       Interfaces map[string]*Interface
       Tariffs    map[int]*Tariff

       // Derived indices
       DeviceInterfaces map[string][]*Interface // device_id -> interfaces
       InterfaceLinks   map[string][]*Link      // interface_id -> links
   }

   func BuildTopologyCache(db *sqlx.DB) (*TopologyCache, error)
   ```

**Success Criteria:**

- Fetch all devices from PostgreSQL (match Python count)
- Fetch all links, interfaces, tariffs
- Build index maps in <100ms for 200 devices
- No memory leaks (run with `-race` flag)

**Files:**

- `engine-go/internal/models/device.go`
- `engine-go/internal/models/link.go`
- `engine-go/internal/models/topology_cache.go`
- `engine-go/internal/db/repository.go`

**Testing:**

- Unit tests: `models_test.go`
- Integration test: fetch from test DB, verify counts

---

#### **HGO-003: Build Adjacency Algorithm**

**Priority:** 🔥 CRITICAL  
**Effort:** 3-4 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
Port Python `build_adjacency()` to Go with same logic.

**Reference:** `backend/services/traffic/v2_graph.py`

**Subtasks:**

1. [ ] Define adjacency graph structure

   ```go
   type AdjacencyGraph struct {
       // Map: device_id -> list of (neighbor_device_id, link_id, bandwidth_mbps)
       Neighbors map[string][]Neighbor
   }

   type Neighbor struct {
       DeviceID    string
       LinkID      string
       Capacity    float64 // min(link capacity, port profile capacity)
       IsPassable  bool    // link effective_status == UP
   }
   ```

2. [ ] Implement `buildAdjacency(cache *TopologyCache) *AdjacencyGraph`
   - Iterate all links where `effective_status = 'UP'`
   - For each link, resolve A/B interfaces → devices
   - Add bidirectional edges (A→B, B→A)
   - Compute capacity: min(link capacity, port profile)
3. [ ] Cache adjacency graph
   - Store in memory (invalidate on topology change)
   - Add TTL or version tracking
   - Expose metrics: graph build time, node/edge counts

**Success Criteria:**

- Adjacency graph matches Python output (same edges, capacity)
- Build time <50ms for 200 devices
- No panics or race conditions (`go test -race`)

**Files:**

- `engine-go/internal/graph/adjacency.go`
- `engine-go/internal/graph/adjacency_test.go`

**Testing:**

- Unit test: build graph from fixture data
- Compare with Python output (export JSON, diff)

---

#### **HGO-004: Traffic Generation (Tariff-Based)**

**Priority:** 🔥 CRITICAL  
**Effort:** 4-5 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
Port Python `generate_flows_for_leaves()` to Go.

**Reference:** `backend/services/traffic/v2_tick.py`

**Subtasks:**

1. [ ] Identify leaf devices (ONT, BUSINESS_ONT, AON_CPE)

   - Filter devices by type
   - Check `provisioned = true` and `effective_status = 'UP'`
   - Check `tariff_id IS NOT NULL`

2. [ ] Generate flows per leaf

   ```go
   type Flow struct {
       SourceDeviceID string
       DownstreamBps  float64 // Mbps * 1e6
       UpstreamBps    float64
   }

   func generateFlows(cache *TopologyCache) []Flow {
       var flows []Flow
       for _, device := range cache.Devices {
           if !isLeafType(device.Type) { continue }
           if !device.Provisioned { continue }
           if device.EffectiveStatus == nil || *device.EffectiveStatus != "UP" { continue }
           if device.TariffID == nil { continue }

           tariff := cache.Tariffs[*device.TariffID]
           // Apply randomization (80-100% of tariff)
           downBps := tariff.MaxDownMbps * 1e6 * randomFactor()
           upBps := tariff.MaxUpMbps * 1e6 * randomFactor()

           flows = append(flows, Flow{
               SourceDeviceID: device.ID,
               DownstreamBps:  downBps,
               UpstreamBps:    upBps,
           })
       }
       return flows
   }
   ```

3. [ ] Deterministic randomization
   - Use seeded RNG (match Python behavior for tests)
   - Range: 80-100% of tariff bandwidth
   - ENV var: `TRAFFIC_RANDOM_SEED` (default: time-based)

**Success Criteria:**

- Flow generation matches Python (same devices, bandwidth ranges)
- Generation time <10ms for 200 devices
- Deterministic output when seeded

**Files:**

- `engine-go/internal/traffic/generation.go`
- `engine-go/internal/traffic/generation_test.go`

**Testing:**

- Unit test: generate flows from fixture devices + tariffs
- Compare counts and bandwidth sums with Python

---

#### **HGO-005: Path Aggregation (BFS from Leaves)**

**Priority:** 🔥 CRITICAL  
**Effort:** 5-6 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
Port Python path aggregation (BFS from leaves) to Go.

**Reference:** `backend/services/traffic/v2_aggregation.py`

**Subtasks:**

1. [ ] BFS traversal from each leaf

   ```go
   func aggregatePaths(graph *AdjacencyGraph, flows []Flow) (
       deviceMetrics map[string]*DeviceMetric,
       linkMetrics map[string]*LinkMetric,
   ) {
       deviceMetrics = make(map[string]*DeviceMetric)
       linkMetrics = make(map[string]*LinkMetric)

       for _, flow := range flows {
           visited := make(map[string]bool)
           queue := []string{flow.SourceDeviceID}

           for len(queue) > 0 {
               devID := queue[0]
               queue = queue[1:]
               if visited[devID] { continue }
               visited[devID] = true

               // Aggregate to device
               if deviceMetrics[devID] == nil {
                   deviceMetrics[devID] = &DeviceMetric{}
               }
               deviceMetrics[devID].TotalDown += flow.DownstreamBps
               deviceMetrics[devID].TotalUp += flow.UpstreamBps

               // Traverse neighbors
               for _, neighbor := range graph.Neighbors[devID] {
                   if !neighbor.IsPassable { continue }

                   // Aggregate to link
                   if linkMetrics[neighbor.LinkID] == nil {
                       linkMetrics[neighbor.LinkID] = &LinkMetric{}
                   }
                   linkMetrics[neighbor.LinkID].TotalDown += flow.DownstreamBps
                   linkMetrics[neighbor.LinkID].TotalUp += flow.UpstreamBps

                   queue = append(queue, neighbor.DeviceID)
               }
           }
       }
       return
   }
   ```

2. [ ] Device metrics structure

   ```go
   type DeviceMetric struct {
       DeviceID    string
       TotalDown   float64 // bps
       TotalUp     float64
       Utilization float64 // 0.0-1.0 (if capacity known)
   }
   ```

3. [ ] Link metrics structure
   ```go
   type LinkMetric struct {
       LinkID      string
       TotalDown   float64
       TotalUp     float64
       Utilization float64 // traffic / capacity
       Capacity    float64 // from graph
   }
   ```

**Success Criteria:**

- Aggregation matches Python (same device/link traffic sums)
- Aggregation time <100ms for 200 devices
- Correct handling of link directionality

**Files:**

- `engine-go/internal/traffic/aggregation.go`
- `engine-go/internal/traffic/aggregation_test.go`

**Testing:**

- Unit test: BFS from fixtures, verify sums
- Integration test: compare with Python snapshot

---

#### **HGO-006: Congestion Detection**

**Priority:** 🟡 HIGH  
**Effort:** 2-3 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
Port Python congestion detection logic to Go.

**Reference:** `backend/services/traffic/v2_congestion.py`

**Subtasks:**

1. [ ] Device congestion check

   ```go
   func detectDeviceCongestion(metrics map[string]*DeviceMetric, threshold float64) []CongestionEvent {
       var events []CongestionEvent
       for devID, metric := range metrics {
           if metric.Utilization > threshold {
               events = append(events, CongestionEvent{
                   Type:        "device",
                   EntityID:    devID,
                   Utilization: metric.Utilization,
                   Threshold:   threshold,
               })
           }
       }
       return events
   }
   ```

2. [ ] Link congestion check

   - Similar logic for links
   - Hysteresis handling (congestion ON at 90%, OFF at 85%)

3. [ ] Emit events to Python
   - Store events in PostgreSQL (`traffic_events` table?)
   - OR send via WebSocket to Python
   - OR expose via HTTP GET `/events`

**Success Criteria:**

- Congestion detection matches Python
- Events stored/sent correctly
- Hysteresis prevents flapping

**Files:**

- `engine-go/internal/traffic/congestion.go`
- `engine-go/internal/traffic/congestion_test.go`

**Testing:**

- Unit test: threshold crossings, hysteresis
- Integration test: verify event emission

---

#### **HGO-007: HTTP API + Python Client**

**Priority:** 🔥 CRITICAL  
**Effort:** 3-4 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
Expose HTTP API for Python to trigger ticks and fetch results.

**Subtasks:**

1. [ ] HTTP server setup

   ```go
   // cmd/traffic-engine/main.go
   func main() {
       router := gin.Default()

       router.POST("/api/v1/tick", handleTick)
       router.GET("/api/v1/snapshot", handleSnapshot)
       router.GET("/api/v1/health", handleHealth)

       router.Run(":8080")
   }
   ```

2. [ ] `/tick` endpoint

   - Trigger full traffic generation cycle
   - Return: tick ID, duration, device/link counts

   ```json
   POST /api/v1/tick
   Response:
   {
     "tick_id": "abc123",
     "duration_ms": 45,
     "devices": 198,
     "links": 240,
     "flows": 192
   }
   ```

3. [ ] `/snapshot` endpoint

   - Return current traffic metrics

   ```json
   GET /api/v1/snapshot
   Response:
   {
     "timestamp": "2025-10-03T12:00:00Z",
     "devices": {
       "ont1": {"total_down": 100000000, "total_up": 20000000, "utilization": 0.5}
     },
     "links": {
       "link1": {"total_down": 200000000, "total_up": 40000000, "utilization": 0.7}
     }
   }
   ```

4. [ ] Python client

   ```python
   # backend/clients/traffic_go_client.py
   import httpx

   class TrafficGoClient:
       def __init__(self, base_url: str = "http://localhost:8080"):
           self.base_url = base_url
           self.client = httpx.Client(timeout=30.0)

       def trigger_tick(self) -> dict:
           resp = self.client.post(f"{self.base_url}/api/v1/tick")
           resp.raise_for_status()
           return resp.json()

       def get_snapshot(self) -> dict:
           resp = self.client.get(f"{self.base_url}/api/v1/snapshot")
           resp.raise_for_status()
           return resp.json()
   ```

5. [ ] Integration with Python traffic loop
   - Replace `TrafficEngine().run_tick()` with `TrafficGoClient().trigger_tick()`
   - Fallback: if Go service down, use Python engine (graceful degradation)

**Success Criteria:**

- Python can trigger tick via HTTP
- Snapshot matches Python output
- Client handles errors gracefully

**Files:**

- `engine-go/internal/api/handlers.go`
- `backend/clients/traffic_go_client.py`
- `backend/tests/test_traffic_go_integration.py`

**Testing:**

- Start Go service, call from Python
- Compare results with pure Python engine

---

#### **HGO-008: Unit Tests (Go Side)**

**Priority:** 🟡 HIGH  
**Effort:** 3-4 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
Comprehensive unit tests for all Go components.

**Subtasks:**

1. [ ] Test fixtures (shared with Python)

   - JSON files with device/link/interface data
   - Same fixtures used by Python tests
   - Load via `testdata/` directory

2. [ ] Unit tests per module

   - `adjacency_test.go`: graph building
   - `generation_test.go`: flow generation
   - `aggregation_test.go`: path aggregation
   - `congestion_test.go`: threshold detection

3. [ ] Table-driven tests

   ```go
   func TestAdjacencyBuild(t *testing.T) {
       tests := []struct {
           name     string
           devices  []Device
           links    []Link
           expected int // edge count
       }{
           {"empty", []Device{}, []Link{}, 0},
           {"single link", /* ... */, 2}, // bidirectional
       }

       for _, tt := range tests {
           t.Run(tt.name, func(t *testing.T) {
               cache := &TopologyCache{Devices: tt.devices, Links: tt.links}
               graph := buildAdjacency(cache)
               assert.Equal(t, tt.expected, countEdges(graph))
           })
       }
   }
   ```

4. [ ] Benchmarks
   ```go
   func BenchmarkBuildAdjacency200(b *testing.B) {
       cache := loadFixture("200_devices.json")
       b.ResetTimer()
       for i := 0; i < b.N; i++ {
           buildAdjacency(cache)
       }
   }
   ```

**Success Criteria:**

- > 80% code coverage
- All tests pass with `-race` flag
- Benchmarks show <50ms adjacency build

**Files:**

- `engine-go/internal/*_test.go`
- `engine-go/testdata/*.json`

**Testing:**

- `go test -v -cover -race ./...`

---

#### **HGO-009: Integration Tests (Python ↔ Go)**

**Priority:** 🟡 HIGH  
**Effort:** 2-3 days  
**Owner:** @agent + @duly3  
**Status:** ⬜ not started

**Description:**
End-to-end tests verifying Python ↔ Go integration.

**Subtasks:**

1. [ ] Test setup: start Go service in background

   ```python
   # backend/tests/test_traffic_go_integration.py
   import subprocess
   import pytest

   @pytest.fixture(scope="module")
   def go_service():
       proc = subprocess.Popen(
           ["./engine-go/cmd/traffic-engine/traffic-engine"],
           env={"DB_URL": "..."}
       )
       time.sleep(2)  # wait for startup
       yield
       proc.terminate()
       proc.wait()
   ```

2. [ ] Test: trigger tick from Python

   ```python
   def test_trigger_tick_from_python(go_service):
       client = TrafficGoClient()
       result = client.trigger_tick()
       assert result["devices"] > 0
       assert result["flows"] > 0
   ```

3. [ ] Test: compare Go vs Python output

   ```python
   def test_go_matches_python_output():
       # Build same topology
       # Run Python engine → snapshot1
       # Run Go engine → snapshot2
       # Assert snapshots match (tolerance 1%)
       assert_snapshots_equal(snapshot1, snapshot2, tolerance=0.01)
   ```

4. [ ] Test: performance regression
   ```python
   def test_go_performance_200_devices():
       start = time.perf_counter()
       client.trigger_tick()
       duration = time.perf_counter() - start
       assert duration < 0.5  # 500ms target
   ```

**Success Criteria:**

- Python can communicate with Go service
- Results match within 1% tolerance
- Performance <500ms for 200 devices

**Files:**

- `backend/tests/test_traffic_go_integration.py`

**Testing:**

- `pytest backend/tests/test_traffic_go_integration.py -v`

---

#### **HGO-010: Load Test @ 200 Devices (Validation)**

**Priority:** 🔥 CRITICAL  
**Effort:** 1-2 days  
**Owner:** @agent + @duly3  
**Status:** ⚠️ **BLOCKER FOUND - BFS Performance Issue** (2025-10-04)

**Description:**
Run same load test as Python (test_realistic_200.py) but with Go engine.

**Current Progress:**

- ✅ Test file created (backend/tests/perf/test_go_200_clean.py, 456 lines)
- ✅ Go binary built and running
- ✅ Fixed 6 issues: unicode encoding, backend check, timestamp field, response structure, timeout, provisioning
- ✅ **BREAKTHROUGH:** Topology populates correctly in PostgreSQL!
  - Fixed root conftest.py conflict (was forcing inmemory)
  - Re-initialized backend.db engine to use PostgreSQL
  - Fixed session commit issue (final commit before session close)
  - Created backend/tests/perf/conftest.py with pytest_configure hook
- ✅ Go engine reads 198 devices + 197 links from DB
- ✅ BFS pathfinding finds ONTs and generates traffic
- ❌ **NEW BLOCKER:** BFS is O(N²) and TIMEOUTS after 2 minutes!
  - Go engine processes 10 ONTs, then hangs
  - Each ONT does full BFS through entire network
  - 192 ONTs × BFS = 💀 (timeout after 120s)

**Root Cause Analysis:**

```
2:48PM DBG Fetched devices from database count=198
2:48PM DBG Fetched links from database count=197
2:48PM INF Built topology cache devices=198 interfaces=587 links=197 tariffs=1
2:48PM INF Built adjacency graph devices_in_graph=198 passable_links=394
2:48PM DBG Processing devices for traffic generation total_devices=198
2:48PM DBG Found leaf device device_id=ont2_5 provisioned=true tariff_valid=true
2:48PM INF Processing leaf device for traffic generation device_id=ont2_5 max_up_mbps=20
... (9 more ONTs processed)
[TIMEOUT AFTER 2 MINUTES - only 10/192 ONTs completed]
```

**Performance Bottleneck:**

- **BFS pathfinding** is called **per-ONT** (not cached!)
- At 200 devices: **192 BFS calls** × **~198 node graph** = O(N²) complexity
- Current implementation: **~1.2s per ONT** (120s / 10 ONTs = 12s per ONT!)
- Extrapolated to 1000 devices: **~60 minutes per tick** 💀

**Optimization Required:**

1. **Cache BFS results** (paths don't change between ONTs)
2. **Batch pathfinding** (find all paths in one graph traversal)
3. **Precompute routing tables** (startup cost, O(1) lookup during tick)
4. **Use Dijkstra with heap** (current BFS may be naive implementation)

**Next Steps:**

1. ✅ Create test with 64 ONTs (faster iteration)
2. ✅ Profile Go BFS code (identify exact bottleneck)
3. ✅ Implement path caching or batch pathfinding
4. ✅ Re-run load test with optimization

**Subtasks:**

1. [x] Create `test_go_200_clean.py` with correct PON hierarchy
2. [x] Debug topology/provisioning issue (RESOLVED - PostgreSQL engine)
3. [ ] **Optimize BFS performance** (IN PROGRESS)
   - Profile `internal/traffic/generation.go` BFS implementation
   - Implement path caching or precomputed routing tables
   - Target: <1s total for all 192 ONTs
4. [ ] Analyze results (BLOCKED by BFS optimization)
5. [ ] Extrapolate to 1000 devices (BLOCKED)

**Success Criteria:**

- ✅ Traffic tick <500ms @ 200 devices (4-5× faster than Python)
- ✅ Extrapolated 1000-device traffic <3s (within target)
- ✅ No crashes or data corruption

**Files:**

- `backend/tests/perf/test_realistic_200_go.py`

**Testing:**

- Manual run + profiling analysis

---

### 🚀 **Phase 2: Production Integration**

#### **HGO-011: Docker Containerization**

**Priority:** 🟡 HIGH  
**Effort:** 2-3 days  
**Status:** ⬜ not started

**Description:**
Package Go service as Docker container.

**Subtasks:**

1. [ ] Multi-stage Dockerfile

   ```dockerfile
   # Stage 1: Build
   FROM golang:1.21-alpine AS builder
   WORKDIR /app
   COPY go.mod go.sum ./
   RUN go mod download
   COPY . .
   RUN go build -o /traffic-engine ./cmd/traffic-engine

   # Stage 2: Runtime
   FROM alpine:latest
   RUN apk --no-cache add ca-certificates
   COPY --from=builder /traffic-engine /traffic-engine
   EXPOSE 8080
   CMD ["/traffic-engine"]
   ```

2. [ ] Update `docker-compose.yml`

   ```yaml
   services:
     traffic-engine:
       build: ./engine-go
       ports:
         - '8080:8080'
       environment:
         DB_URL: postgresql://unoc:unocpw@db:5432/unocdb
       depends_on:
         - db

     backend:
       # existing Python service
       environment:
         TRAFFIC_GO_URL: http://traffic-engine:8080
   ```

3. [ ] Health checks
   - Docker health check: GET `/api/v1/health`
   - Restart policy: `unless-stopped`

**Success Criteria:**

- Docker build succeeds
- Service starts in container
- Python can reach Go service via `traffic-engine:8080`

**Files:**

- `engine-go/Dockerfile`
- `docker-compose.yml`

---

#### **HGO-012: Prometheus Metrics**

**Priority:** 🟡 HIGH  
**Effort:** 2-3 days  
**Status:** ⬜ not started

**Description:**
Export metrics for monitoring.

**Subtasks:**

1. [ ] Prometheus endpoint

   ```go
   import "github.com/prometheus/client_golang/prometheus"

   var (
       tickDuration = prometheus.NewHistogram(...)
       deviceCount  = prometheus.NewGauge(...)
       flowCount    = prometheus.NewGauge(...)
   )

   router.GET("/metrics", gin.WrapH(promhttp.Handler()))
   ```

2. [ ] Key metrics

   - `traffic_tick_duration_seconds` (histogram)
   - `traffic_devices_total` (gauge)
   - `traffic_flows_total` (gauge)
   - `traffic_adjacency_build_duration_seconds`
   - `traffic_aggregation_duration_seconds`

3. [ ] Grafana dashboard
   - Traffic tick latency over time
   - Device/flow counts
   - Congestion events per minute

**Success Criteria:**

- Metrics exposed at `/metrics`
- Grafana dashboard shows live data

**Files:**

- `engine-go/internal/metrics/prometheus.go`
- `ops/grafana/traffic-dashboard.json`

---

#### **HGO-013: Load Test @ 1000 Devices (GO/NO-GO)**

**Priority:** 🔥 CRITICAL  
**Effort:** 1-2 days  
**Status:** ⬜ not started

**Description:**
Final validation at 1000-device scale.

**Subtasks:**

1. [ ] Create `test_realistic_1000_go.py`

   - 1000 devices: 10 cores, 50 OLTs, 940 ONTs
   - Measure: Status recompute + Traffic tick

2. [ ] Run test

   ```bash
   UNOC_PERF_PROFILE=1 pytest backend/tests/perf/test_realistic_1000_go.py -s
   ```

3. [ ] Validate targets

   - ✅ Traffic tick <2s @ 1000 devices (GO/NO-GO criterion)
   - ⚠️ Status recompute <5s (acceptable if <50s)

4. [ ] Decision point
   - ✅ Both pass → Ship to production
   - ❌ Traffic fails → Optimize Go engine (goroutines, caching)
   - ❌ Status fails → Optimize Python status (lower priority)

**Success Criteria:**

- ✅ Traffic tick <2s @ 1000 devices
- ✅ No errors or crashes during 100+ ticks

**Files:**

- `backend/tests/perf/test_realistic_1000_go.py`

**Testing:**

- Extended run: 1000 ticks (16 minutes) to check stability

---

### 🔧 **Phase 3: Optimization & Monitoring**

#### **HGO-014: Profiling + Optimization**

**Priority:** 🟢 MEDIUM  
**Effort:** 2-3 days  
**Status:** ⬜ not started

**Description:**
Profile Go engine and optimize hot paths.

**Subtasks:**

1. [ ] CPU profiling

   ```bash
   go test -cpuprofile=cpu.prof -bench=.
   go tool pprof cpu.prof
   ```

2. [ ] Memory profiling

   ```bash
   go test -memprofile=mem.prof -bench=.
   go tool pprof mem.prof
   ```

3. [ ] Optimization targets
   - Goroutines for parallel flow generation?
   - Faster map implementations (sync.Map?)
   - Reduce allocations in hot loops

**Success Criteria:**

- Identify top 3 bottlenecks
- Optimize to <1s @ 1000 devices (stretch goal)

---

#### **HGO-015: Production Runbook**

**Priority:** 🟢 MEDIUM  
**Effort:** 1-2 days  
**Status:** ⬜ not started

**Description:**
Document operations procedures.

**Subtasks:**

1. [ ] Deployment guide

   - How to build/push Docker image
   - Environment variables
   - Rollback procedure

2. [ ] Troubleshooting

   - Go service not starting → check DB connection
   - Python can't reach Go → check network/firewall
   - High latency → check profiling data

3. [ ] Monitoring alerts
   - Traffic tick >5s → investigate
   - Error rate >1% → rollback

**Files:**

- `docs/operations/TRAFFIC_GO_RUNBOOK.md`

---

## 📊 Success Metrics

### **Phase 1 (Go Engine) – Week 3**

- [ ] Traffic tick <500ms @ 200 devices
- [ ] Unit test coverage >80%
- [ ] Integration tests pass (Python ↔ Go)
- [ ] Load test extrapolation: <3s @ 1000 devices

### **Phase 2 (Production) – Week 5**

- [ ] Docker deployment successful
- [ ] Prometheus metrics live
- [ ] Load test @ 1000 devices: <2s traffic tick ✅
- [ ] Zero production incidents during rollout

### **Phase 3 (Optimization) – Week 6**

- [ ] Traffic tick <1s @ 1000 devices (stretch goal)
- [ ] Runbook complete
- [ ] Team trained on Go service operations

---

## 🚨 Risks & Mitigation

### **Risk 1: Go Engine Doesn't Match Python Logic**

**Impact:** HIGH (data corruption, incorrect traffic)  
**Likelihood:** MEDIUM  
**Mitigation:**

- Comprehensive unit tests with shared fixtures
- Side-by-side comparison tests (Python vs Go output)
- Gradual rollout: dev → staging → canary → prod

### **Risk 2: Go Performance Insufficient**

**Impact:** HIGH (project fails, need Option B)  
**Likelihood:** LOW (Go typically 10-50× faster than Python)  
**Mitigation:**

- Early profiling at 200-device scale
- Fallback: optimize hot paths (goroutines, better algorithms)
- Worst case: consider C++ for critical sections (unlikely)

### **Risk 3: Operational Complexity**

**Impact:** MEDIUM (two services instead of one)  
**Likelihood:** MEDIUM  
**Mitigation:**

- Docker Compose simplifies deployment
- Shared PostgreSQL (no data sync issues)
- Health checks + auto-restart

### **Risk 4: Python-Go Communication Overhead**

**Impact:** LOW (HTTP adds ~5-10ms)  
**Likelihood:** LOW  
**Mitigation:**

- Use gRPC instead of HTTP if needed (faster serialization)
- Keep Python-Go calls infrequent (1 call per tick)

---

## 📝 Update Log

| Date       | Task            | Status | Notes                                                                                                                                                                                                                                                                                                                                          |
| ---------- | --------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2025-10-03 | Roadmap created | ✅     | Initial version based on Option A load test results (Traffic 11.6s, Status 50s @ 1000 devices → PIVOT TO HYBRID GO)                                                                                                                                                                                                                            |
| 2025-10-03 | HGO-001         | ✅     | **COMPLETED** - Go project setup: Binary (22 MB), PostgreSQL pool (10 conns), HTTP server (:8080), Health check endpoint (0.8ms response). Files: cmd/traffic-engine/main.go, internal/config/config.go, internal/db/postgres.go, internal/api/server.go. Dependencies: pgx v5.7.6, zerolog v1.34.0, gin v1.11.0. Build time: 5s. Startup: 1s. |

---

**Last Updated:** 2025-10-03  
**Status:** � PHASE 1 IN PROGRESS – HGO-001 COMPLETED → HGO-002 NEXT  
**Next Milestone:** HGO-002 (Data Models: Device, Link, Interface, Tariff)

---

## 📚 References

- **Option A Results:** `docs/performance/OPTIMIZATION_ROADMAP.md`
- **Load Test:** `backend/tests/perf/test_realistic_200.py`
- **Architecture Decision:** `docs/architecture/ARCHITECTURE.md`
- **Python Traffic Engine:** `backend/services/traffic/v2_engine.py`
- **Go Project:** `engine-go/` (to be created)
