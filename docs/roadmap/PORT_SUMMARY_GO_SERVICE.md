# 🚀 Port Summary Go Service - Roadmap & Implementation Plan

**Version:** 1.0  
**Status:** PLANNING  
**Estimated Duration:** 2-3 Days (Week 3, Days 18-20)  
**Target Completion:** Wednesday, October 10, 2025

---

## 📊 Performance Goals

| Metric       | Current (Python) | Target (Go)          | Speedup     | Priority    |
| ------------ | ---------------- | -------------------- | ----------- | ----------- |
| 70 Devices   | 250-700ms        | 5-10ms               | **50-100×** | 🔴 CRITICAL |
| 200 Devices  | 2-5s (stuck)     | 10-20ms              | **200×**    | 🔴 CRITICAL |
| 1000 Devices | 10-30s (timeout) | 20-50ms              | **500×**    | 🟡 HIGH     |
| Memory Usage | N/A              | ~100MB @ 10k devices | -           | 🟢 LOW      |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│      PORT SUMMARY SERVICE (Go, port 50054)              │
├─────────────────────────────────────────────────────────┤
│  IN-MEMORY STATE:                                       │
│  ├─ devices: map[string]Device                         │
│  ├─ interfaces: map[string]Interface                   │
│  ├─ links: map[string]Link                             │
│  ├─ ponOccupancy: map[string]map[string]int            │
│  │   └─ oltID -> ponInterfaceID -> ontCount            │
│  └─ opticalPaths: map[string]string                    │
│      └─ ontID -> ponInterfaceID (precomputed!)         │
│                                                          │
│  gRPC METHODS:                                          │
│  ├─ GetPortSummary(deviceID) -> InterfaceSummary[]     │
│  ├─ GetBulkPortSummary(deviceIDs[]) -> map[id]summary  │
│  └─ InvalidateCache(deviceID) // Event-triggered       │
│                                                          │
│  EVENT LISTENERS (PostgreSQL NOTIFY):                  │
│  ├─ link_created/deleted -> recompute affected OLT     │
│  ├─ device_provisioned -> update optical path          │
│  └─ topology_version_change -> full reload             │
└─────────────────────────────────────────────────────────┘
         ▲                                    │
         │ gRPC                               │ PostgreSQL
         │                                    ▼
┌────────┴──────────┐              ┌──────────────────┐
│  FastAPI Backend  │              │    Database      │
│  (Python)         │              │   (Postgres)     │
│                   │              │                  │
│  /api/ports/      │              │  LISTEN events   │
│  summary          │              │  NOTIFY triggers │
└───────────────────┘              └──────────────────┘
```

---

## 📋 PHASE 1: Core Go Service (Day 18 - 8h)

### Task 1.1: Proto Definition & Code Generation

**Files:** `proto/port_summary.proto`, `engine-go/gen/port_summary/`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 1h

**Implementation:**

```protobuf
syntax = "proto3";
package port_summary;

service PortSummaryService {
  rpc GetPortSummary(DeviceRequest) returns (PortSummaryResponse);
  rpc GetBulkPortSummary(BulkDeviceRequest) returns (BulkPortSummaryResponse);
  rpc InvalidateCache(InvalidateCacheRequest) returns (google.protobuf.Empty);
}

message DeviceRequest {
  string device_id = 1;
}

message BulkDeviceRequest {
  repeated string device_ids = 1;
}

message InterfaceSummary {
  string id = 1;
  string name = 2;
  string port_role = 3;
  string effective_status = 4;
  int32 occupancy = 5;
  optional int32 capacity = 6;
}

message PortSummaryResponse {
  repeated InterfaceSummary interfaces = 1;
}

message BulkPortSummaryResponse {
  map<string, PortSummaryResponse> summaries = 1;
}

message InvalidateCacheRequest {
  string device_id = 1;
}
```

**Commands:**

```bash
protoc --go_out=engine-go/gen --go-grpc_out=engine-go/gen proto/port_summary.proto
```

**Acceptance Criteria:**

- [ ] Proto file compiled without errors
- [ ] Generated Go code in `engine-go/gen/port_summary/`
- [ ] gRPC service interface available

---

### Task 1.2: Database Loader (Initial State)

**Files:** `engine-go/cmd/port-summary-service/loader.go`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 2h

**Implementation:**

```go
type PortSummaryService struct {
    devices    map[string]*Device
    interfaces map[string]*Interface
    links      map[string]*Link

    // PRECOMPUTED für Performance:
    ponOccupancy  map[string]map[string]int // oltID -> ponIfID -> count
    opticalPaths  map[string]string         // ontID -> ponIfID

    mu sync.RWMutex // Thread-safe
    db *sql.DB
}

func (s *PortSummaryService) LoadInitialState() error {
    s.mu.Lock()
    defer s.mu.Unlock()

    // BATCH LOAD 1: All devices
    rows, err := s.db.Query("SELECT id, type, status FROM device")
    // ... load into s.devices

    // BATCH LOAD 2: All interfaces
    rows, err = s.db.Query("SELECT id, device_id, name, port_role FROM interface")
    // ... load into s.interfaces

    // BATCH LOAD 3: All links
    rows, err = s.db.Query("SELECT id, a_interface_id, b_interface_id FROM link")
    // ... load into s.links

    // PRECOMPUTE: PON Occupancy + Optical Paths
    s.computePONOccupancy()
    s.computeOpticalPaths()

    return nil
}
```

**Acceptance Criteria:**

- [ ] Load all devices, interfaces, links in 3 batch queries
- [ ] Build in-memory maps (thread-safe with RWMutex)
- [ ] Precompute PON occupancy + optical paths
- [ ] Handle database connection errors gracefully

---

### Task 1.3: Simple Counting Logic

**Files:** `engine-go/cmd/port-summary-service/counting.go`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 2h

**Implementation:**

```go
func (s *PortSummaryService) computePONOccupancy() {
    s.ponOccupancy = make(map[string]map[string]int)

    // For each OLT:
    for _, dev := range s.devices {
        if dev.Type != "OLT" {
            continue
        }

        oltID := dev.ID
        s.ponOccupancy[oltID] = make(map[string]int)

        // Get PON interfaces for this OLT
        ponInterfaces := s.getPONInterfaces(oltID)

        // For each PON interface:
        for _, ponIf := range ponInterfaces {
            count := 0

            // Count connected ONTs via optical paths
            for ontID, ponIfID := range s.opticalPaths {
                if ponIfID == ponIf.ID {
                    count++
                }
            }

            s.ponOccupancy[oltID][ponIf.ID] = count
        }
    }
}

func (s *PortSummaryService) computeOccupancy(iface *Interface) int {
    switch iface.PortRole {
    case "PON":
        // OLT PON port: precomputed occupancy
        oltID := iface.DeviceID
        return s.ponOccupancy[oltID][iface.ID]

    case "ACCESS":
        // AON Switch ACCESS port: count connected links
        return len(s.getLinksForInterface(iface.ID))

    case "UPLINK":
        // Binary: 0 or 1
        links := s.getLinksForInterface(iface.ID)
        if len(links) > 0 {
            return 1
        }
        return 0

    default:
        return 0
    }
}
```

**Acceptance Criteria:**

- [ ] PON occupancy: Count ONTs per PON port
- [ ] ACCESS occupancy: Count connected devices (CPEs)
- [ ] UPLINK occupancy: Binary (0 or 1)
- [ ] Match Python logic exactly (for regression testing)

---

### Task 1.4: gRPC Server Implementation

**Files:** `engine-go/cmd/port-summary-service/server.go`, `main.go`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 2h

**Implementation:**

```go
func (s *PortSummaryService) GetPortSummary(ctx context.Context, req *pb.DeviceRequest) (*pb.PortSummaryResponse, error) {
    s.mu.RLock()
    defer s.mu.RUnlock()

    deviceID := req.DeviceId
    interfaces := s.getInterfacesForDevice(deviceID)

    var summaries []*pb.InterfaceSummary
    for _, iface := range interfaces {
        occupancy := s.computeOccupancy(iface)
        capacity := s.getCapacity(iface)

        summaries = append(summaries, &pb.InterfaceSummary{
            Id:              iface.ID,
            Name:            iface.Name,
            PortRole:        iface.PortRole,
            EffectiveStatus: s.computeEffectiveStatus(iface),
            Occupancy:       int32(occupancy),
            Capacity:        capacity,
        })
    }

    return &pb.PortSummaryResponse{Interfaces: summaries}, nil
}

func (s *PortSummaryService) GetBulkPortSummary(ctx context.Context, req *pb.BulkDeviceRequest) (*pb.BulkPortSummaryResponse, error) {
    s.mu.RLock()
    defer s.mu.RUnlock()

    result := make(map[string]*pb.PortSummaryResponse)

    for _, deviceID := range req.DeviceIds {
        summary, err := s.GetPortSummary(ctx, &pb.DeviceRequest{DeviceId: deviceID})
        if err == nil {
            result[deviceID] = summary
        }
    }

    return &pb.BulkPortSummaryResponse{Summaries: result}, nil
}

func main() {
    // Database connection
    db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
    // ...

    // Service initialization
    service := &PortSummaryService{db: db}
    service.LoadInitialState()

    // gRPC server
    lis, err := net.Listen("tcp", ":50054")
    grpcServer := grpc.NewServer()
    pb.RegisterPortSummaryServiceServer(grpcServer, service)

    log.Println("Port Summary Service listening on :50054")
    grpcServer.Serve(lis)
}
```

**Acceptance Criteria:**

- [ ] gRPC server listens on port 50054
- [ ] GetPortSummary returns correct interface summaries
- [ ] GetBulkPortSummary handles multiple device IDs efficiently
- [ ] Thread-safe read operations (RWMutex)
- [ ] Graceful error handling

---

### Task 1.5: Unit Tests (Go)

**Files:** `engine-go/cmd/port-summary-service/server_test.go`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 1h

**Tests:**

- [ ] Test PON occupancy counting (mock data)
- [ ] Test ACCESS occupancy counting (mock links)
- [ ] Test UPLINK occupancy (binary logic)
- [ ] Test GetPortSummary (single device)
- [ ] Test GetBulkPortSummary (multiple devices)

---

## 📋 PHASE 2: Event-Driven Updates (Day 19 - 6h)

### Task 2.1: PostgreSQL NOTIFY Listener

**Files:** `engine-go/cmd/port-summary-service/events.go`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 2h

**Implementation:**

```go
func (s *PortSummaryService) StartEventListener() {
    // PostgreSQL LISTEN
    conn, err := pq.NewListener(s.dbURL, 10*time.Second, time.Minute, nil)
    conn.Listen("link_events")
    conn.Listen("device_events")
    conn.Listen("topology_events")

    for {
        select {
        case notification := <-conn.Notify:
            s.handleEvent(notification)
        case <-time.After(90 * time.Second):
            conn.Ping()
        }
    }
}

func (s *PortSummaryService) handleEvent(n *pq.Notification) {
    var event Event
    json.Unmarshal([]byte(n.Extra), &event)

    switch event.Type {
    case "link_created", "link_deleted":
        s.onLinkChanged(event.LinkID)
    case "device_provisioned":
        s.onDeviceProvisioned(event.DeviceID)
    case "topology_version_change":
        s.reloadAll()
    }
}
```

**Acceptance Criteria:**

- [ ] Listen to PostgreSQL NOTIFY channels
- [ ] Parse event payloads (JSON)
- [ ] Dispatch events to correct handlers
- [ ] Reconnect on connection loss

---

### Task 2.2: Cache Invalidation Logic

**Files:** `engine-go/cmd/port-summary-service/cache.go`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 2h

**Implementation:**

```go
func (s *PortSummaryService) onLinkChanged(linkID string) {
    s.mu.Lock()
    defer s.mu.Unlock()

    // Reload affected link
    link := s.loadLink(linkID)
    s.links[linkID] = link

    // Find affected OLTs (interfaces connected to this link)
    affectedOLTs := s.findAffectedOLTs(link)

    // Recompute PON occupancy for affected OLTs
    for _, oltID := range affectedOLTs {
        s.recomputeOLTOccupancy(oltID)
    }
}

func (s *PortSummaryService) onDeviceProvisioned(deviceID string) {
    s.mu.Lock()
    defer s.mu.Unlock()

    // Reload device
    device := s.loadDevice(deviceID)
    s.devices[deviceID] = device

    // If ONT: update optical path
    if device.Type == "ONT" || device.Type == "BUSINESS_ONT" {
        ponIfID := s.findPONInterface(deviceID)
        s.opticalPaths[deviceID] = ponIfID

        // Recompute parent OLT occupancy
        oltID := s.findParentOLT(deviceID)
        s.recomputeOLTOccupancy(oltID)
    }
}

func (s *PortSummaryService) InvalidateCache(ctx context.Context, req *pb.InvalidateCacheRequest) (*emptypb.Empty, error) {
    // Triggered by Python backend after mutations
    deviceID := req.DeviceId
    s.recomputeDevice(deviceID)
    return &emptypb.Empty{}, nil
}
```

**Acceptance Criteria:**

- [ ] Link events trigger OLT recomputation
- [ ] Device provisioning updates optical paths
- [ ] Manual InvalidateCache method for Python backend
- [ ] Minimal recomputation (only affected devices)

---

### Task 2.3: Optical Path Precomputation

**Files:** `engine-go/cmd/port-summary-service/optical.go`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 1h

**Implementation:**

```go
func (s *PortSummaryService) computeOpticalPaths() {
    s.opticalPaths = make(map[string]string)

    // For each provisioned ONT:
    for _, dev := range s.devices {
        if (dev.Type != "ONT" && dev.Type != "BUSINESS_ONT") || !dev.Provisioned {
            continue
        }

        // Find ONT interface (ont1)
        ontIf := s.findInterface(dev.ID, "ont1")
        if ontIf == nil {
            continue
        }

        // Find PON interface via link traversal (BFS)
        ponIfID := s.traceToPON(ontIf.ID)
        if ponIfID != "" {
            s.opticalPaths[dev.ID] = ponIfID
        }
    }
}

func (s *PortSummaryService) traceToPON(startIfID string) string {
    // BFS: Follow links until we reach a PON port
    visited := make(map[string]bool)
    queue := []string{startIfID}

    for len(queue) > 0 {
        ifID := queue[0]
        queue = queue[1:]

        if visited[ifID] {
            continue
        }
        visited[ifID] = true

        iface := s.interfaces[ifID]
        if iface.PortRole == "PON" {
            return ifID
        }

        // Add connected interfaces to queue
        for _, link := range s.getLinksForInterface(ifID) {
            peerIfID := s.getPeerInterface(link, ifID)
            queue = append(queue, peerIfID)
        }
    }

    return ""
}
```

**Acceptance Criteria:**

- [ ] Precompute optical paths for all ONTs on startup
- [ ] Update paths on device provisioning events
- [ ] BFS path finding (like Python implementation)
- [ ] Handle missing paths gracefully

---

### Task 2.4: Integration Tests (gRPC Client)

**Files:** `engine-go/cmd/port-summary-service/integration_test.go`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 1h

**Tests:**

- [ ] Test event listener (mock PostgreSQL NOTIFY)
- [ ] Test cache invalidation (link created/deleted)
- [ ] Test device provisioning event handling
- [ ] Test topology version change (full reload)

---

## 📋 PHASE 3: Python Integration (Day 20 - 4h)

### Task 3.1: Python gRPC Client

**Files:** `backend/clients/port_summary_client.py`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 1h

**Implementation:**

```python
import grpc
from backend.proto import port_summary_pb2, port_summary_pb2_grpc

class PortSummaryClient:
    """gRPC client for Port Summary Go Service."""

    def __init__(self, host: str = "localhost:50054"):
        self.channel = grpc.insecure_channel(host)
        self.stub = port_summary_pb2_grpc.PortSummaryServiceStub(self.channel)

    def get_port_summary(self, device_id: str) -> list[dict]:
        """Get port summary for single device."""
        try:
            request = port_summary_pb2.DeviceRequest(device_id=device_id)
            response = self.stub.GetPortSummary(request, timeout=5.0)
            return [self._to_dict(iface) for iface in response.interfaces]
        except grpc.RpcError as e:
            raise Exception(f"gRPC error: {e.code()}")

    def get_bulk_port_summary(self, device_ids: list[str]) -> dict[str, list[dict]]:
        """Get port summaries for multiple devices (bulk)."""
        try:
            request = port_summary_pb2.BulkDeviceRequest(device_ids=device_ids)
            response = self.stub.GetBulkPortSummary(request, timeout=10.0)
            return {
                dev_id: [self._to_dict(iface) for iface in summary.interfaces]
                for dev_id, summary in response.summaries.items()
            }
        except grpc.RpcError as e:
            raise Exception(f"gRPC error: {e.code()}")

    def invalidate_cache(self, device_id: str):
        """Trigger cache invalidation for device."""
        request = port_summary_pb2.InvalidateCacheRequest(device_id=device_id)
        self.stub.InvalidateCache(request, timeout=2.0)

    @staticmethod
    def _to_dict(iface) -> dict:
        return {
            "id": iface.id,
            "name": iface.name,
            "port_role": iface.port_role,
            "effective_status": iface.effective_status,
            "occupancy": iface.occupancy,
            "capacity": iface.capacity if iface.HasField("capacity") else None,
        }
```

**Acceptance Criteria:**

- [ ] Connect to Go service via gRPC (port 50054)
- [ ] GetPortSummary method (single device)
- [ ] GetBulkPortSummary method (multiple devices)
- [ ] InvalidateCache method (event-triggered)
- [ ] Timeout handling (5-10s)
- [ ] Error handling (gRPC exceptions)

---

### Task 3.2: Backend API Migration

**Files:** `backend/api/endpoints/ports.py`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 1.5h

**Implementation:**

```python
from backend.clients.port_summary_client import PortSummaryClient

# Global client instance
_port_summary_client = PortSummaryClient()

@router.get("/summary", response_model=dict[str, list[InterfaceSummaryOut]])
async def get_bulk_port_summary(
    request: Request,
    ids: Annotated[list[str], Query(..., description="Device IDs to summarize")],
    s: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Bulk variant: returns mapping device_id -> list[InterfaceSummaryOut].

    PERFORMANCE: Uses Go service if available, falls back to Python.
    """

    # Validate & deduplicate IDs
    if len(ids) > MAX_BULK_IDS:
        raise HTTPException(status_code=400, detail=f"Too many IDs (>{MAX_BULK_IDS})")

    ordered_ids = list(dict.fromkeys(ids))  # dedupe, preserve order

    # TRY GO SERVICE FIRST
    use_go = os.getenv("USE_GO_PORT_SUMMARY", "1") == "1"
    if use_go:
        try:
            go_result = _port_summary_client.get_bulk_port_summary(ordered_ids)
            return go_result
        except Exception as e:
            logger.warning(f"Go service failed, falling back to Python: {e}")

    # FALLBACK: Python implementation (existing code)
    return await _get_bulk_port_summary_python(s, ordered_ids)
```

**Acceptance Criteria:**

- [ ] Try Go service first (if USE_GO_PORT_SUMMARY=1)
- [ ] Fallback to Python on gRPC errors
- [ ] Log fallback events for monitoring
- [ ] Preserve API response format (backward compatible)

---

### Task 3.3: Event Triggers (Python → Go)

**Files:** `backend/api/endpoints/links.py`, `backend/services/provisioning_service.py`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 0.5h

**Implementation:**

```python
# After link creation/deletion:
async def create_link(...):
    # ... create link in DB

    # Trigger Go service cache invalidation
    if os.getenv("USE_GO_PORT_SUMMARY") == "1":
        try:
            # Invalidate affected devices (both endpoints)
            _port_summary_client.invalidate_cache(link.a_device_id)
            _port_summary_client.invalidate_cache(link.b_device_id)
        except Exception as e:
            logger.warning(f"Go cache invalidation failed: {e}")

    return link

# After device provisioning:
async def provision_device(...):
    # ... provision device

    # Trigger Go service cache invalidation
    if os.getenv("USE_GO_PORT_SUMMARY") == "1":
        try:
            _port_summary_client.invalidate_cache(device.id)
            if device.parent_container_id:
                _port_summary_client.invalidate_cache(device.parent_container_id)
        except Exception as e:
            logger.warning(f"Go cache invalidation failed: {e}")
```

**Acceptance Criteria:**

- [ ] Link create/delete triggers cache invalidation
- [ ] Device provisioning triggers cache invalidation
- [ ] Invalidate parent devices (OLTs) when ONTs provisioned
- [ ] Non-blocking (don't fail request if Go service down)

---

### Task 3.4: E2E Tests (Python → Go → DB)

**Files:** `backend/tests/test_port_summary_go_service.py`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 1h

**Tests:**

- [ ] Test bulk API with Go service (70 devices)
- [ ] Test fallback to Python when Go service unavailable
- [ ] Test cache invalidation after link creation
- [ ] Test cache invalidation after device provisioning
- [ ] Test correct occupancy values (compare Python vs Go)
- [ ] Test response time < 50ms for 200 devices

---

## 📋 PHASE 4: Testing & Benchmarks (Day 20 - 2h)

### Task 4.1: Performance Benchmarks

**Files:** `tools/benchmark_port_summary.py`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 1h

**Benchmarks:**

- [ ] 70 devices: Target < 10ms (vs 250-700ms Python)
- [ ] 200 devices: Target < 20ms (vs 2-5s Python)
- [ ] 1000 devices: Target < 50ms (vs 10-30s Python)
- [ ] Memory usage: < 200MB @ 10k devices

**Implementation:**

```python
import time
from backend.clients.port_summary_client import PortSummaryClient

def benchmark_port_summary(device_count: int):
    client = PortSummaryClient()
    device_ids = [f"device-{i}" for i in range(device_count)]

    start = time.perf_counter()
    result = client.get_bulk_port_summary(device_ids)
    elapsed = time.perf_counter() - start

    print(f"Devices: {device_count}, Time: {elapsed*1000:.2f}ms")
    return elapsed

# Run benchmarks
benchmark_port_summary(70)
benchmark_port_summary(200)
benchmark_port_summary(1000)
```

**Acceptance Criteria:**

- [ ] 70 devices: < 10ms ✅
- [ ] 200 devices: < 20ms ✅
- [ ] 1000 devices: < 50ms ✅
- [ ] Compare Python vs Go side-by-side

---

### Task 4.2: Load Testing

**Files:** `tools/load_test_port_summary.py`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 0.5h

**Tests:**

- [ ] 10 concurrent requests (70 devices each)
- [ ] 50 concurrent requests (200 devices each)
- [ ] Sustained load (1000 requests/minute for 5 minutes)
- [ ] Memory leak detection

---

### Task 4.3: Documentation

**Files:** `docs/roadmap/PORT_SUMMARY_GO_SERVICE.md`, `README.md`  
**Status:** 🔴 NOT STARTED  
**Estimated:** 0.5h

**Documentation:**

- [ ] Architecture diagram (updated README)
- [ ] API documentation (gRPC methods)
- [ ] Configuration guide (env vars)
- [ ] Monitoring guide (Prometheus metrics)
- [ ] Troubleshooting guide (fallback scenarios)

---

## 📊 Progress Tracking

### Phase 1: Core Go Service (Day 18)

- [ ] Task 1.1: Proto Definition (1h)
- [ ] Task 1.2: Database Loader (2h)
- [ ] Task 1.3: Counting Logic (2h)
- [ ] Task 1.4: gRPC Server (2h)
- [ ] Task 1.5: Unit Tests (1h)

**Total: 8h**

### Phase 2: Event-Driven Updates (Day 19)

- [ ] Task 2.1: PostgreSQL Listener (2h)
- [ ] Task 2.2: Cache Invalidation (2h)
- [ ] Task 2.3: Optical Path Precomputation (1h)
- [ ] Task 2.4: Integration Tests (1h)

**Total: 6h**

### Phase 3: Python Integration (Day 20)

- [ ] Task 3.1: Python gRPC Client (1h)
- [ ] Task 3.2: Backend API Migration (1.5h)
- [ ] Task 3.3: Event Triggers (0.5h)
- [ ] Task 3.4: E2E Tests (1h)

**Total: 4h**

### Phase 4: Testing & Benchmarks (Day 20)

- [ ] Task 4.1: Performance Benchmarks (1h)
- [ ] Task 4.2: Load Testing (0.5h)
- [ ] Task 4.3: Documentation (0.5h)

**Total: 2h**

---

## 🎯 Success Criteria

- [ ] Go service handles 1000 devices in < 50ms
- [ ] Python fallback works when Go service unavailable
- [ ] All tests pass (unit + integration + E2E)
- [ ] Memory usage < 200MB @ 10k devices
- [ ] Event-driven updates working (real-time)
- [ ] Documentation complete
- [ ] Production-ready deployment (Docker, systemd)

---

## 🚧 Known Risks & Mitigation

| Risk                        | Impact | Probability | Mitigation                                      |
| --------------------------- | ------ | ----------- | ----------------------------------------------- |
| **Optical Path Complexity** | Medium | Low         | Reuse PathFinder Service logic (proven)         |
| **Memory Usage**            | Low    | Low         | ~100MB @ 10k devices (tested in Status Service) |
| **Event Race Conditions**   | Medium | Low         | RWMutex + Event Queue (like Status Service)     |
| **Integration Issues**      | High   | Medium      | Copy Traffic Engine Client Pattern (proven)     |
| **PostgreSQL NOTIFY Lag**   | Low    | Low         | <100ms lag acceptable for PON occupancy         |

---

## 🔄 Context Estimation

**Token Usage Forecast:**

| Phase                               | Estimated Tokens | Cumulative |
| ----------------------------------- | ---------------- | ---------- |
| Phase 1: Core Go Service            | ~30k tokens      | 30k        |
| Phase 2: Event Updates              | ~25k tokens      | 55k        |
| Phase 3: Python Integration         | ~20k tokens      | 75k        |
| Phase 4: Testing & Docs             | ~15k tokens      | 90k        |
| **Buffer (Debugging, Refactoring)** | ~30k tokens      | **120k**   |

**Current Context Status:**

- Used: ~75k tokens
- Available: ~125k tokens
- **Verdict:** ✅ **COMFORTABLE** (120k needed, 125k available)

**Mitigation if context runs low:**

1. Summarize after each phase
2. Extract completed code to files
3. Focus on incremental testing (validate as we go)

---

## 📅 Timeline Summary

| Day        | Phase              | Hours | Deliverables                                                   |
| ---------- | ------------------ | ----- | -------------------------------------------------------------- |
| **Day 18** | Core Go Service    | 8h    | Proto, Loader, Counting, gRPC Server, Unit Tests               |
| **Day 19** | Event Updates      | 6h    | Listener, Cache Invalidation, Optical Paths, Integration Tests |
| **Day 20** | Python Integration | 4h    | gRPC Client, API Migration, Event Triggers, E2E Tests          |
| **Day 20** | Testing & Docs     | 2h    | Benchmarks, Load Tests, Documentation                          |

**Total: 20h over 3 days (Wed, Oct 10)**

---

## ✅ Ready to Start?

**Prerequisites:**

- [x] Roadmap created
- [x] LLM Keyfiles updated
- [x] Context estimate acceptable
- [ ] User approval to proceed

**Next Steps:**

1. User reviews roadmap
2. Start Phase 1: Proto Definition
3. Iterative development with continuous testing

---

**Version History:**

- v1.0 (2025-10-08): Initial roadmap created
