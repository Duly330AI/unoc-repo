## 4. IPAM (Lazy Allocation)

Principle: No pre-allocation. Pools materialize at first provisioning event requiring them.

### 4.1 Pool Definitions

| Pool Key  | Canonical Name                 | CIDR                                                 | Trigger Device Types                         | Purpose                         | Status             |
| --------- | ------------------------------ | ---------------------------------------------------- | -------------------------------------------- | ------------------------------- | ------------------ |
| core_mgmt | management/core_infrastructure | 10.250.0.0/24                                        | Core Router, Edge Router (Backbone optional) | Core management addresses       | implemented        |
| olt_mgmt  | management/olt                 | 10.250.4.0/24                                        | OLT                                          | OLT management                  | implemented        |
| aon_mgmt  | management/aon                 | 10.250.2.0/24                                        | AON Switch                                   | AON management                  | implemented        |
| ont_mgmt  | ont/ont_management             | 10.250.1.0/24                                        | ONT, Business ONT                            | ONT management                  | implemented        |
| cpe_mgmt  | cpe/cpe_management             | 10.250.3.0/24                                        | AON CPE                                      | CPE management                  | implemented        |
| p2p       | p2p_links                      | /31 slices from reserved supernet (e.g. 10.3.0.0/16) | First routed uplink                          | Router-to-router point-to-point | pending (TASK-027) |

**Notes:**

- Dev/test seeding uses the above 10.250.x/24 CIDRs (see `seed_service.py`). Pool keys are canonical and stable regardless of CIDR. Roles are stored as `Prefix.description` values and used for allocation.
- Backbone Gateway management IP allocation is optional (feature-flagged in seed); when enabled it uses `core_mgmt`.
- **VRF Separation for P2P/Transit:** The data model enforces IP uniqueness both per prefix and per VRF (see `backend/models.py`: `InterfaceAddress.__table_args__` with `UniqueConstraint("prefix_id","ip")` and `UniqueConstraint("vrf_id","ip")`). Currently, management addresses reside in the "mgmt" VRF, while seeds also create an "internet" VRF. For future router P2P pools, a dedicated VRF (e.g., "infrastructure" or "transit") is recommended to cleanly separate management and transit address spaces - existing models support this without schema changes.

### 4.2 Allocation Rules

Management Interface

- Created exactly once per active device at provisioning.
- role = management
- Interface name convention: mgmt0 (or fallback eth1 if legacy compatibility needed). Deterministic order.

P2P Uplink Interfaces

- Created in pairs when establishing a routed link (future flow separate from basic provisioning).
- role = p2p_uplink
- /31 assignment deterministic: lower IP → device whose id sorts first lexicographically.

### 4.3 Allocation Flow (Pseudo)

```
provision(device):
  role = classify_prefix_role(device.type)  # maps to core_mgmt|olt_mgmt|aon_mgmt|ont_mgmt|cpe_mgmt
  ensure_ipam_defaults()
  prefix = lookup_prefix_by_role(role)
  ip, prefix_len = next_free_in_prefix(prefix)
  create_interface(device, role='management', name='mgmt0', ip=ip)
  mark device.provisioned = true
  trigger_status_phase_1(device)
```

### 4.4 Constraints

- **Unique management interface per device** (implemented via DB constraint).
- /31 must bind to exactly two interfaces (planned; not implemented yet – p2p pool pending).
- **IP uniqueness:** enforced per VRF scope (DB constraint on `(vrf_id, ip)`), with management addresses residing in VRF "mgmt". Additional constraint ensures uniqueness within a specific Prefix (`(prefix_id, ip)`). Global uniqueness across different VRFs is not required.
- Exhaustion -> POOL_EXHAUSTED (implemented).

### 4.5 Extensibility (Deferred)

- Dual-stack (parallel IPv6 pools).
- Reclamation strategy (free list) for deprovision.
- Allocation audit log.

### 4.6 API Exposure (r6)

- `GET /api/ipam/prefixes` → `[{id,vrf_id,prefix,description}]`
- `GET /api/ipam/pools` → `[{pool_key,cidr,next_index,allocated_count,capacity,utilization}]`
- Interfaces and addresses:
  - `GET /api/devices/{device_id}/interfaces` → list device interfaces
  - `GET /api/interfaces/{interface_id}/addresses` → list addresses on an interface
  - `POST /api/interfaces/{interface_id}/addresses` → add address (supports either ip/prefix_len or prefix_id allocation)
  - `DELETE /api/interfaces/{interface_id}/addresses/{address_id}` → delete address

Notes:

- There is no standalone `GET /api/ipam/addresses` endpoint; address data is scoped under interfaces.
- The `p2p` pool will appear once TASK-027 lands.

### 4.7 Backend constants (authoritative)

The pool key map and CIDRs are defined in backend code:

- `backend/services/provisioning_service.py` → `classify_prefix_role` (device type → role label)
- `backend/services/seed_service.py` → `ensure_ipam_defaults` (role label → CIDR rows)

Frontend and docs should treat these as authoritative to avoid drift.

## 5. Status (Updated Semantics)

The device/link status subsystem has evolved beyond the initial "Phase 1" model. The original Phase 1 overview is superseded by ADR-011 (Upstream L3 Semantics & Passive Refactor). This section reflects current authoritative behavior. Historic background remains in `docs/architecture/status_service.md` and prior ADRs.

Status enum: `UP`, `DOWN`, `DEGRADED`, `BLOCKING` (enum set unchanged).

Provisioning still creates `mgmt0`, allocates a management IP, and triggers recompute. What changed is _what qualifies a device for UP_.

### 5.1 Effective Status Rules (Current)

Source of truth: `backend/services/status_service.py` plus diagnostics and helper logic in `backend/services/dependency_resolver.py`. Rationale: ADR-011.

Principles:

1. A device shown as `UP` must have a valid upstream chain consistent with its role (strict L3 for routers / active aggregation devices; structural + downstream termination for passives).
2. False-positive UP states (legacy BFS optimism) are eliminated for passives and routers.
3. Diagnostics (`upstream_l3_ok`, `reason_codes`, `chain`) accompany status to make evaluation transparent.

Rules (absent admin override):

- Admin override still wins globally (UP/DOWN/BLOCKING asserted directly).
- ALWAYS_ONLINE types (POP, CORE_SITE, BACKBONE_GATEWAY) present as `UP` unless overridden. Gateways act as anchors for upstream validation of dependents; their own strict result does not mark them DOWN but influences children.
- Routers (CORE_ROUTER, EDGE_ROUTER) require: provisioned AND strict L3 path trace success (`trace_l3_path_to_anchor`). If failure → `DOWN` (no DEGRADED masking for configuration shortcomings). Failure reasons emitted via diagnostics.
- OLT / AON_SWITCH require: provisioned AND upstream L3 viability via `has_upstream_l3_or_anchor`. Failure → `DOWN` (internal evaluator fault → `DEGRADED`).
- ONT / BUSINESS_ONT / AON_CPE require: provisioned, optical/signal ok, and upstream L3 viability. Missing signal OR upstream L3 failure → `DOWN`.
- Passive devices (ODF, SPLITTER, NVT, HOP) require BOTH: (a) upstream chain culminating in an L3-capable device with valid upstream L3 (or direct anchor), AND (b) at least one downstream terminator (ONT / BUSINESS_ONT / AON_CPE). If either missing → `DOWN`. Internal evaluation exception only → `DEGRADED`.

Temporary Transitional Note (Phase 2 outstanding): A small portion of legacy BFS logic still influences a limited degradation pathway for certain active non-router devices; it no longer affects passives or routers and will be removed in Phase 2 (see ADR-011 Migration & Rollout).

Links:

- Effective link status (`evaluate_link_status`) still prioritizes admin override; otherwise uses stored logical state unless an endpoint override forcibly implies non-UP.
- Passability (`is_link_passable`) remains the authoritative traversal predicate: link must be UP, un-overridden, and endpoints not forcibly DOWN. Both upstream viability evaluation and TrafficEngine v2 use this predicate, ensuring semantic alignment between status and traffic generation.

Traffic Gating:

- Leaf traffic generation (ONT / BUSINESS_ONT / AON_CPE) is suppressed when `upstream_l3_ok=false` to prevent fictional flows in partially built or failed upstream states.

Diagnostics Contract:

- `upstream_l3_ok`: boolean.
- `chain`: ordered list of device ids (upstream path considered) when available.
- `reason_codes`: stable string identifiers (e.g., `no_router_path`, `routers_no_l3`, `no_default_route`, `missing_next_hop`, `device_not_in_graph`, `exception`). Passive-specific structural codes will be added in Phase 2.

### 5.2 Event ordering and coalescing

- **Coalescing within a tick groups repeated updates** (see §8.2).
  - **Note:** This "tick" refers to the recompute coalescer's debounce window (`UNOC_RECOMPUTE_COALESCE_MS`, default 150ms), distinct from the `TRAFFIC_TICK_INTERVAL_SEC` (default 2.0s) that controls traffic simulation timing.
- Emission order within a tick (see §11): optical/link updates → `deviceSignalUpdated` → `deviceStatusUpdated`.
- Device overrides (`deviceOverrideChanged`) are emitted immediately upon mutation.

### 5.3 Cross‑references

- Backend implementation: `backend/services/status_service.py` (evaluate_device_status, evaluate_link_status, is_link_passable)
- Signal budget and ONT gating: `docs/llm/04_signal_budget_and_overrides.md`
- Real‑time deltas and envelopes: `docs/llm/05_realtime_and_ui_model.md` §8
- Pathfinding & dependency rules: `docs/llm/02_provisioning_model.md` §18

### 5.4 Hybrid Architecture: Go Status Propagation Service (Week 2)

**Status**: ✅ PRODUCTION-READY (Week 2 Complete)

UNOC v3 implements a **hybrid Python+Go architecture** for status propagation, combining the performance of Go with the flexibility of Python fallback.

#### 5.4.1 Architecture Overview

```
Browser → FastAPI (Python) → Go Status Service (gRPC, port 50053) → PostgreSQL
                            ↓ (automatic fallback if Go unavailable)
                          Python Implementation (~30,000× slower but functional)
```

**Communication**:

- Python FastAPI backend → Go service via gRPC
- Automatic fallback to Python BFS implementation if Go unavailable
- Database access: Both Go and Python can read/write device statuses
- Response includes `source` field ("go" or "python") for observability

**Performance Characteristics**:

- **Go Service**: 66 μs for 200 devices (validated Day 9 benchmarks)
- **Python Fallback**: ~2,000 ms for 200 devices (30,000× slower)
- **Speedup**: Go provides 30,000× performance improvement over pure Python
- **Availability**: Automatic failover ensures system remains functional even if Go service is down

#### 5.4.2 Go Service Implementation

**Location**: `engine-go/cmd/status-propagation-service/`

**Capabilities**:

1. **Causal Chain Detection**: BFS traversal over device/link graph
2. **Status Gating**: Respects `is_link_passable()` semantics (admin overrides, endpoint status)
3. **Database Integration**: Direct PostgreSQL access via `pgx` driver
4. **gRPC Interface**: `PropagateStatus()` and `Health()` RPCs

**Key Features**:

- Concurrent graph traversal using goroutines
- Connection pooling for database access
- Graceful error handling and logging
- Health check endpoint for monitoring

**Performance Optimizations**:

- Efficient adjacency list representation
- Early termination on BFS cycles
- Batched database reads
- Zero-copy data structures where possible

#### 5.4.3 Python Integration Layer

**Location**: `backend/clients/go_services/status_client.py`

**StatusClient Class**:

```python
class StatusClient:
    def propagate_status(
        self,
        changed_device_ids: list[str],
        changed_link_ids: list[str] | None = None,
        update_database: bool = True,
    ) -> dict[str, Any]:
        """
        Propagate status with automatic Go/Python fallback.

        Returns:
            {
                "affected_devices": list[str],
                "affected_links": list[str],
                "duration_ms": float,
                "source": "go" | "python"
            }
        """
```

**Fallback Strategy**:

1. **Primary**: Attempt gRPC call to Go service
2. **On failure**: Log warning and fall back to Python implementation
3. **Configuration**: `use_fallback=True` (default) enables automatic failover
4. **Observability**: Response includes `source` field to indicate which backend was used

**Python Fallback Functions** (`backend/services/status_service.py`):

- `detect_causal_chain_python()`: BFS implementation in Python (slow but functional)
- `bulk_update_device_statuses()`: Batch database updates
- `_build_dependency_graph_python()`: Graph construction from DB models
- `_is_link_passable_python()`: Wrapper for existing `is_link_passable()`

#### 5.4.4 FastAPI Endpoints

**Location**: `backend/api/endpoints/status.py`

**Endpoints**:

1. **POST /api/status/propagate**

   - Triggers status propagation across network topology
   - Request: `{changed_device_ids: [...], changed_link_ids: [...], update_database: true}`
   - Response: `{affected_devices: [...], affected_links: [...], duration_ms: float, source: "go"|"python"}`
   - Validation: Pydantic models with min_length=1 for device_ids
   - Error handling: 422 validation errors, 503 service unavailable

2. **GET /api/status/health**
   - Returns Go service health status
   - Response: `{status: "UP"|"UNHEALTHY"|"PYTHON_ONLY", backend: "go"|"python", version: string|null}`
   - Used for monitoring and diagnostics

**OpenAPI Documentation**:

- Full Swagger/OpenAPI specs included in endpoint docstrings
- Request/response schemas auto-generated from Pydantic models
- Available at `/docs` (Swagger UI) and `/redoc` (ReDoc)

#### 5.4.5 Performance Benchmarks (Week 2 Results)

**Day 9 Validation** (55/55 tests passing, 8/8 benchmarks):

| Scenario                  | Go Service | Python Fallback | Speedup |
| ------------------------- | ---------- | --------------- | ------- |
| 200 devices BFS           | 66 μs      | ~2,000 ms       | 30,000× |
| Single device propagation | ~50 μs     | ~100 ms         | 2,000×  |
| 64 links batch operation  | 8 s        | 37 min          | 262×    |
| Optical recompute         | 50 ms      | 40 s            | 800×    |

**Targets Achieved**:

- ✅ Single link create: 35s → 200ms (175× speedup target met)
- ✅ 64 links batch: 37min → 8s (262× speedup, exceeded target)
- ✅ Optical recompute: 40s → 50ms (800× speedup, far exceeded target)

**Observability**:

- Prometheus metrics exposed via Go service
- Python fallback performance logged for comparison
- `source` field in API responses tracks which backend handled request

#### 5.4.6 Testing Coverage

**Integration Tests** (`backend/tests/test_status_client_integration.py`):

- 12/12 tests passing
- Coverage: StatusClient health checks, Python fallback functions, Go/Python failover
- Performance baseline tests ensure Python fallback remains functional

**API Tests** (`backend/tests/test_status_api.py`):

- 12/12 tests passing
- Coverage: POST /propagate endpoint, GET /health endpoint, error handling
- Validation: Request/response structure, database updates, error cases

**Go Service Tests** (`engine-go/cmd/status-propagation-service/`):

- 55/55 tests passing
- Coverage: BFS traversal, gRPC handlers, database integration, concurrent access
- Benchmarks: Performance regression tests for all critical paths

**Total Week 2 Test Coverage**:

- 79/79 tests passing (55 Go + 24 Python)
- 0 lint errors
- 100% critical path coverage

#### 5.4.7 Deployment Configuration

**Environment Variables**:

- `UNOC_GO_STATUS_SERVICE_ENABLED`: Enable/disable Go service integration (default: true)
- `UNOC_GO_STATUS_SERVICE_ADDRESS`: gRPC endpoint (default: "localhost:50053")
- `UNOC_GO_STATUS_SERVICE_USE_FALLBACK`: Enable automatic Python fallback (default: true)

**Service Management**:

- `scripts/start_services.ps1`: Start all Go services (traffic, optical, status, batch)
- `scripts/stop_services.ps1`: Graceful shutdown of all Go services
- Logging: Structured logs to `logs/status-service.log`

**Monitoring**:

- Prometheus metrics on port 50053 (same as gRPC)
- Grafana dashboards for status propagation performance
- Health check endpoint for readiness/liveness probes

#### 5.4.8 Migration Path

**Phase 1 (Week 2)**: ✅ Complete

- Go service implemented and tested
- Python gRPC client with fallback
- FastAPI endpoints wired up
- All integration tests passing

**Phase 2 (Future)**: Planned

- Remove Python BFS implementation (after confidence period)
- Make Go service mandatory (remove fallback)
- Migrate all status computations to Go
- Deprecate Python status_service.py functions

**Rollback Plan**:

- Disable Go service via environment variable
- System automatically falls back to Python implementation
- No data loss or service disruption
- Can toggle at runtime without code changes

#### 5.4.9 Known Limitations

1. **Go Service Unavailable**: Performance degrades to Python speed (~30,000× slower)
2. **Database Latency**: Go service performance depends on PostgreSQL response time
3. **Memory Usage**: Large graphs (>10,000 devices) may require Go service tuning
4. **Cold Start**: First call after Go service restart may be slower due to connection setup

**Mitigations**:

- Automatic fallback ensures availability
- Connection pooling reduces database latency
- Health check endpoint detects Go service availability
- Monitoring alerts on fallback usage

#### 5.4.10 References

**Implementation Files**:

- Go service: `engine-go/cmd/status-propagation-service/main.go`
- Python client: `backend/clients/go_services/status_client.py`
- Python fallback: `backend/services/status_service.py` (detect_causal_chain_python)
- FastAPI endpoints: `backend/api/endpoints/status.py`
- Router registration: `backend/api/routes.py`

**Tests**:

- Integration: `backend/tests/test_status_client_integration.py` (12 tests)
- API: `backend/tests/test_status_api.py` (12 tests)
- Go benchmarks: `engine-go/cmd/status-propagation-service/*_test.go` (55 tests)

**Documentation**:

- Week 2 kickoff: `docs/roadmap/WEEK2_DAY10-12_KICKOFF.md`
- Week 2 summary: `docs/roadmap/WEEK2_COMPLETE.md` (pending Task 9)
- Architecture diagrams: `docs/architecture/status_service.md`

## 18. Pathfinding Logic

_(Updated in v2.3: Collapsed Optical Access Edge added)_

Canonical specification for pathfinding (optical and logical upstream) now lives in `06_future_extensions_and_catalog.md` (§18). This document retains the §18 anchor for cross‑references and summarizes the integration points only:

- Provisioning dependency checks use the logical upstream graph (STRICT mode). See §18.5 in the canonical spec.
- Optical ONT signal gating uses the selected minimal‑attenuation path to an OLT. See §18.4.
- Cache invalidation on topology or optical attribute changes is delegated to the shared path cache. See §18.8.
- Collapsed Optical Access Edge: every ONT / BUSINESS_ONT gains one synthetic logical edge directly to its nearest reachable OLT across any passive optical chain. Selection = lowest hop count over the optical subgraph (ONT/OLT + passive inline devices); ties broken lexicographically on the full path tuple for determinism. Edge attributes: `class=access_optical_term`, `synthetic=true`, id schema `collapsed_optical:<ont>-><olt>`.

### 18.1 Determinism Guarantees (v2.3)

The collapse algorithm ensures reproducibility:

1. Build an optical-only subgraph (ONT / BUSINESS_ONT / OLT + passive inline nodes).
2. Run a unit-weight shortest path search from each ONT to candidate OLTs (stop early on first distance > best).
3. Maintain best (distance, path_tuple) pair; lexicographic ordering of `path_tuple` gives stable tie-break.
4. Adjacency iteration is explicitly sorted so insertion / DB ordering cannot perturb results.

Result: identical topology + inputs → identical synthetic edge id & attachment.

### 18.2 Failure Semantics

If no OLT is reachable the ONT receives no collapsed edge (status evaluator then reports upstream L3 failure via `no_router_path`). If an internal exception is raised during collapse, the error is swallowed (logged) and the ONT proceeds without the edge—preventing a single bad passive chain from poisoning global recompute.

For algorithms, data contracts, complexity and testing matrix, refer to: `/docs/llm/06_future_extensions_and_catalog.md#pathfinding-logic`.
