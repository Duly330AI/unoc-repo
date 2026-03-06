# Go Service Contracts (Protobuf/gRPC Examples)

**Purpose:** Define clear interfaces between Python (FastAPI) and Go services.  
**Status:** Planning (Week 1 implementation)  
**Last Updated:** 2025-10-04

---

## 🏗️ **Service Architecture**

```
Python FastAPI (Port 5001)
    ├─ gRPC Client → Go Optical Service (Port 50051)
    ├─ gRPC Client → Go Batch Service (Port 50052)
    └─ gRPC Client → Go Status Service (Port 50053)

Go Traffic Engine (Port 8080)  ✅ Already running!
```

---

## 📦 **optical.proto** — Optical Path Resolution

```protobuf
syntax = "proto3";

package optical;

// Service for optical path computation
service OpticalService {
  // Recompute optical paths for affected ONTs
  rpc RecomputePaths(RecomputeRequest) returns (RecomputeResponse);

  // Get optical path details for a single ONT
  rpc GetPath(GetPathRequest) returns (OpticalPath);

  // Health check
  rpc Health(Empty) returns (HealthResponse);
}

message RecomputeRequest {
  repeated string link_ids = 1;        // Links that changed
  repeated string device_ids = 2;      // Devices that changed
  bool force_full_recompute = 3;       // Skip smart detection, recompute all
}

message RecomputeResponse {
  int32 affected_onts = 1;             // Number of ONTs recomputed
  repeated string ont_ids = 2;         // List of affected ONT IDs
  int64 duration_ms = 3;               // How long it took
  string status = 4;                   // "success" | "partial" | "error"
  repeated string errors = 5;          // Error messages if any
}

message GetPathRequest {
  string ont_id = 1;                   // ONT device ID
}

message OpticalPath {
  string ont_id = 1;                   // ONT device ID
  repeated PathSegment segments = 2;   // Splitter → OLT path
  double total_attenuation_db = 3;     // Total loss
  double rx_power_dbm = 4;             // Received power
  double margin_db = 5;                // Signal margin
  string status = 6;                   // "ok" | "degraded" | "loss"
}

message PathSegment {
  string link_id = 1;                  // Link ID
  string from_device_id = 2;           // Source device
  string to_device_id = 3;             // Target device
  double attenuation_db = 4;           // Loss for this segment
}

message Empty {}

message HealthResponse {
  string status = 1;                   // "ok" | "degraded" | "down"
  string version = 2;                  // Service version
  int64 uptime_seconds = 3;            // How long running
}
```

**Python Client Example:**

```python
# backend/clients/go_services/optical_client.py
import grpc
from proto import optical_pb2, optical_pb2_grpc

class OpticalClient:
    def __init__(self, address="localhost:50051"):
        self.channel = grpc.insecure_channel(address)
        self.stub = optical_pb2_grpc.OpticalServiceStub(self.channel)

    def recompute_paths(self, link_ids: list[str]) -> dict:
        """Recompute optical paths for affected ONTs"""
        request = optical_pb2.RecomputeRequest(link_ids=link_ids)

        try:
            response = self.stub.RecomputePaths(request, timeout=30)
            return {
                "affected_onts": response.affected_onts,
                "ont_ids": list(response.ont_ids),
                "duration_ms": response.duration_ms,
                "status": response.status,
            }
        except grpc.RpcError as e:
            # Fallback to Python implementation
            from backend.services.optical_service import recompute_optical_paths
            return recompute_optical_paths(link_ids=link_ids)

    def get_path(self, ont_id: str) -> dict:
        """Get optical path details for a single ONT"""
        request = optical_pb2.GetPathRequest(ont_id=ont_id)
        response = self.stub.GetPath(request, timeout=5)

        return {
            "ont_id": response.ont_id,
            "total_attenuation_db": response.total_attenuation_db,
            "rx_power_dbm": response.rx_power_dbm,
            "margin_db": response.margin_db,
            "status": response.status,
            "segments": [
                {
                    "link_id": seg.link_id,
                    "from_device_id": seg.from_device_id,
                    "to_device_id": seg.to_device_id,
                    "attenuation_db": seg.attenuation_db,
                }
                for seg in response.segments
            ],
        }
```

**FastAPI Integration:**

```python
# backend/services/optical_service.py (updated)
from backend.clients.go_services.optical_client import OpticalClient

# Try Go service, fallback to Python
optical_client = OpticalClient()

def recompute_optical_paths_for_affected_onts(link_ids: set[str]):
    """
    Recompute optical paths. Uses Go service if available, else Python.
    """
    try:
        result = optical_client.recompute_paths(list(link_ids))
        logger.info(f"Go optical recompute: {result['affected_onts']} ONTs in {result['duration_ms']}ms")
        return result
    except Exception as e:
        logger.warning(f"Go service unavailable, using Python fallback: {e}")
        # Original Python implementation (slow but reliable)
        return _recompute_optical_paths_python(link_ids)
```

---

## 📦 **batch.proto** — Batch Operations

```protobuf
syntax = "proto3";

package batch;

// Service for bulk CRUD operations
service BatchService {
  // Create multiple links in a single transaction
  rpc CreateLinks(CreateLinksRequest) returns (CreateLinksResponse);

  // Provision multiple ONTs in a single transaction
  rpc ProvisionDevices(ProvisionDevicesRequest) returns (ProvisionDevicesResponse);

  // Health check
  rpc Health(Empty) returns (HealthResponse);
}

message CreateLinksRequest {
  repeated LinkCreate links = 1;       // Links to create
  bool skip_validation = 2;            // Skip validation (unsafe!)
}

message LinkCreate {
  string a_interface_id = 1;           // Interface A
  string b_interface_id = 2;           // Interface B
  string classification = 3;           // "gpon_olt_to_splitter", etc.
  double attenuation_db = 4;           // Signal loss
  optional string label = 5;           // Optional label
}

message CreateLinksResponse {
  int32 created = 1;                   // Number of links created
  repeated string link_ids = 2;        // Created link IDs
  repeated string failed = 3;          // Failed link IDs
  int64 duration_ms = 4;               // Total time
  string recompute_status = 5;         // "pending" | "complete" | "error"
}

message ProvisionDevicesRequest {
  repeated DeviceProvision devices = 1;  // Devices to provision
}

message DeviceProvision {
  string device_id = 1;                // Device to provision
  string parent_id = 2;                // Parent device (OLT/splitter)
  int32 pon_port = 3;                  // PON port number
  int32 ont_id = 4;                    // ONT ID on PON
  string tariff_id = 5;                // Tariff for traffic generation
}

message ProvisionDevicesResponse {
  int32 provisioned = 1;               // Number provisioned
  repeated string device_ids = 2;      // Provisioned device IDs
  repeated string failed = 3;          // Failed device IDs
  int64 duration_ms = 4;               // Total time
}

message Empty {}

message HealthResponse {
  string status = 1;
  string version = 2;
  int64 uptime_seconds = 3;
}
```

---

## 📦 **status.proto** — Status Propagation

```protobuf
syntax = "proto3";

package status;

// Service for status dependency resolution
service StatusService {
  // Propagate status changes through dependency tree
  rpc PropagateStatus(PropagateRequest) returns (PropagateResponse);

  // Get dependency tree for a device
  rpc GetDependencies(GetDepsRequest) returns (DependencyTree);

  // Health check
  rpc Health(Empty) returns (HealthResponse);
}

message PropagateRequest {
  repeated string changed_device_ids = 1;  // Devices that changed
  repeated string changed_link_ids = 2;    // Links that changed
}

message PropagateResponse {
  int32 affected_devices = 1;              // Number of devices updated
  repeated string device_ids = 2;          // Updated device IDs
  int64 duration_ms = 3;                   // Time taken
  string status = 4;                       // "success" | "partial" | "error"
}

message GetDepsRequest {
  string device_id = 1;                    // Device to analyze
}

message DependencyTree {
  string device_id = 1;                    // Root device
  repeated Dependency dependencies = 2;    // Upstream dependencies
}

message Dependency {
  string device_id = 1;                    // Dependent device
  string link_id = 2;                      // Link connecting them
  int32 depth = 3;                         // Distance from root
}

message Empty {}

message HealthResponse {
  string status = 1;
  string version = 2;
  int64 uptime_seconds = 3;
}
```

---

## 🚀 **Implementation Timeline**

### **Week 1 (Oct 7-11):**

- [ ] Create `.proto` files in `engine-go/proto/`
- [ ] Generate Go code: `protoc --go_out=. --go-grpc_out=. *.proto`
- [ ] Generate Python code: `python -m grpc_tools.protoc --python_out=. --grpc_python_out=. *.proto`
- [ ] Implement service scaffolding (health checks only)
- [ ] Create Python client wrappers with fallback logic

### **Week 2 (Oct 14-18):**

- [ ] Implement `OpticalService` in Go
- [ ] Implement `StatusService` in Go
- [ ] Test gRPC communication (Python → Go)
- [ ] Benchmark performance (before/after)

### **Week 3 (Oct 21-25):**

- [ ] Implement `BatchService` in Go
- [ ] Update FastAPI endpoints to use Go services
- [ ] Update frontend to use batch endpoints
- [ ] End-to-end testing (create 64 ONTs, measure time)

---

## 🔗 **Related Documentation**

- **[../OPERATION-STABLE-FOUNDATION.md](OPERATION-STABLE-FOUNDATION.md)** — 3-week plan
- **[../architecture/HYBRID-ARCHITECTURE.md](../architecture/HYBRID-ARCHITECTURE.md)** _(TODO: Week 1)_ — Detailed design
- **[../operations/GO-SERVICES-DEPLOYMENT.md](../operations/GO-SERVICES-DEPLOYMENT.md)** _(TODO: Week 3)_ — Ops guide

---

**Note:** All Go services must have graceful degradation (Python fallback) to ensure system reliability during rollout.
