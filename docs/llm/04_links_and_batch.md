# 04. Links and Batch Operations

## 4.1 Link Model

Links connect two interfaces and represent physical or logical connections in the network.

**Key Fields:**

- `id`: Unique link identifier (auto-generated)
- `a_interface_id`: First interface ID
- `b_interface_id`: Second interface ID
- `length_km`: Cable length in kilometers
- `status`: Link operational status (`UP`, `DOWN`, `DEGRADED`)
- `effective_status`: Computed status considering endpoints and admin overrides
- `admin_override_status`: Admin-configured status override
- `link_type`: Physical link type (ETHERNET, FIBER, WIRELESS)
- `metadata`: JSON metadata (fiber type, cable ID, etc.)

## 4.2 Link Rules

Links must satisfy topology rules:

1. **No Self-Links**: Both interfaces must be on different devices
2. **Interface Uniqueness**: Each interface can be in at most one link
3. **Role Compatibility**: Interfaces must have compatible roles (e.g., UNI ↔ NNI)
4. **Device Type Compatibility**: Device types must form valid connections (e.g., OLT ↔ ODF ↔ ONT)

## 4.3 Link CRUD Operations

### Create Link

```http
POST /api/v1/links
Content-Type: application/json

{
  "a_interface_id": 1,
  "b_interface_id": 2,
  "length_km": 5.0,
  "status": "active",
  "metadata": {"fiber_type": "SM", "cable_id": "CAB-001"}
}
```

**Response (201):**

```json
{
  "id": 123,
  "a_interface_id": 1,
  "b_interface_id": 2,
  "length_km": 5.0,
  "status": "UP",
  "effective_status": "UP",
  "link_type": "FIBER",
  "metadata": { "fiber_type": "SM", "cable_id": "CAB-001" },
  "created_at": "2025-10-05T10:00:00Z"
}
```

### Delete Link

```http
DELETE /api/v1/links/{link_id}
```

**Response (202):**

```json
{
  "accepted": true,
  "job_id": "job_abc123"
}
```

Link deletion is **asynchronous** to avoid blocking the UI during optical recomputation.

### Update Link

```http
PUT /api/v1/links/{link_id}
Content-Type: application/json

{
  "length_km": 7.5,
  "metadata": {"fiber_type": "SM", "notes": "Replaced cable"}
}
```

### Set Admin Override

```http
PATCH /api/v1/links/{link_id}/override
Content-Type: application/json

{
  "admin_override_status": "DOWN"
}
```

**Response (202):**

```json
{
  "accepted": true,
  "job_id": "job_def456"
}
```

Admin overrides are **asynchronous** to trigger status propagation without blocking.

## 4.4 Link Status Computation

Links use **effective status** computed from:

1. **Endpoint Status**: Both interface devices must be `UP` or `DEGRADED`
2. **Admin Override**: If set, overrides computed status
3. **Optical Path**: For fiber links, optical power budget must be sufficient

**Status Precedence:**

1. Admin override (if set)
2. `DOWN` if either endpoint is `DOWN`
3. `DEGRADED` if either endpoint is `DEGRADED`
4. `UP` if both endpoints are `UP` and optical path is healthy

## 4.5 Batch Operations (Week 3 Day 14)

**Motivation**: Creating links one-by-one is slow (~35s per link). For large topologies (64+ links), this is impractical (37+ minutes). Batch operations enable bulk creation with parallel validation and transaction-based commits.

**Performance**:

- **Before**: 64 links in 37 minutes (sequential Python)
- **After**: 64 links in <10 seconds (Go service with parallel validation)
- **Speedup**: 262× faster

### Architecture

**Hybrid Python + Go**:

1. **Python FastAPI**: REST endpoint accepts batch requests
2. **Python gRPC Client**: Converts requests to protobuf, calls Go service
3. **Go Batch Service**: Parallel validation, bulk DB operations
4. **Python Fallback**: Stub implementation when Go service unavailable

```
Browser → FastAPI → Python gRPC Client → Go Batch Service → PostgreSQL
                         ↓ (on error)
                    Python Fallback Stub
```

### Batch Create Links

```http
POST /api/v1/links/batch
Content-Type: application/json

{
  "links": [
    {
      "a_interface_id": 1,
      "b_interface_id": 2,
      "length_km": 5.0,
      "status": "active",
      "metadata": {"fiber_type": "SM"}
    },
    {
      "a_interface_id": 3,
      "b_interface_id": 4,
      "length_km": 3.0,
      "status": "active",
      "metadata": {"fiber_type": "SM"}
    }
  ],
  "dry_run": false,
  "skip_optical_recompute": false,
  "request_id": "batch-001"
}
```

**Request Fields**:

- `links`: Array of link specifications (required)
  - `a_interface_id`: First interface ID (required)
  - `b_interface_id`: Second interface ID (required)
  - `length_km`: Cable length (default: 0.0)
  - `status`: Link status (default: "active")
  - `metadata`: JSON metadata (default: {})
- `dry_run`: Validate without committing (default: false)
- `skip_optical_recompute`: Skip optical path recomputation (default: false)
- `request_id`: Correlation ID for tracing (optional)

**Response (201)**:

```json
{
  "created_link_ids": [101, 102, 103],
  "failed_links": [
    {
      "index": 4,
      "a_interface_id": 7,
      "b_interface_id": 8,
      "error_code": "INTERFACE_NOT_FOUND",
      "error_message": "Interface 7 does not exist"
    }
  ],
  "total_requested": 5,
  "total_created": 3,
  "duration_ms": 420,
  "request_id": "batch-001",
  "backend": "go"
}
```

**Response Fields**:

- `created_link_ids`: Array of successfully created link IDs
- `failed_links`: Array of failures with error details
  - `index`: Position in input array (0-based)
  - `a_interface_id`: First interface ID
  - `b_interface_id`: Second interface ID
  - `error_code`: Error code (see below)
  - `error_message`: Human-readable error message
- `total_requested`: Number of links in request
- `total_created`: Number of successfully created links
- `duration_ms`: Processing time in milliseconds
- `request_id`: Correlation ID (echoed from request)
- `backend`: Which backend processed request (`"go"` or `"python"`)

**Error Codes**:

- `INTERFACE_NOT_FOUND`: Interface ID doesn't exist
- `INTERFACE_ALREADY_LINKED`: Interface already in another link
- `INTERFACE_SAME_DEVICE`: Both interfaces on same device (self-link)
- `DEVICE_NOT_FOUND`: Interface's device doesn't exist
- `TRANSACTION_FAILED`: Database transaction error
- `VALIDATION_ERROR`: Request validation failed
- `FALLBACK_NOT_IMPLEMENTED`: Python fallback stub (Go service unavailable)

### Batch Delete Links

```http
POST /api/v1/links/batch/delete
Content-Type: application/json

{
  "link_ids": [101, 102, 103],
  "skip_optical_recompute": false,
  "request_id": "batch-delete-001"
}
```

**Response (200)**:

```json
{
  "deleted_link_ids": [101, 102],
  "failed_links": [
    {
      "link_id": 103,
      "error_code": "LINK_NOT_FOUND",
      "error_message": "Link 103 does not exist"
    }
  ],
  "total_requested": 3,
  "total_deleted": 2,
  "duration_ms": 150,
  "request_id": "batch-delete-001",
  "backend": "go"
}
```

### Health Check

```http
GET /api/v1/batch/health
```

**Response (200)**:

```json
{
  "status": "ok",
  "backend": "go",
  "available": true,
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

### Dry Run Mode

Set `dry_run: true` to validate requests without committing:

```json
{
  "links": [...],
  "dry_run": true
}
```

Response will show which links would succeed/fail without creating anything.

### Performance Optimization

**Go Service (port 50052)**:

- Parallel interface validation (goroutines)
- Single DB transaction for all links
- Batch optical recomputation
- ~200ms latency for 64 links

**Python Fallback**:

- Sequential validation
- One-by-one link creation
- Individual DB commits
- ~30s latency for 64 links (stub returns errors)

**Recommendation**: Keep Go batch service running for production workloads.

### Example: Create 64-ONT Topology

```python
import httpx

# Prepare 64 links (ODF → ONT)
links = []
for i in range(1, 65):
    links.append({
        "a_interface_id": odf_interface_ids[i-1],
        "b_interface_id": ont_interface_ids[i-1],
        "length_km": 0.5,
        "status": "active",
        "metadata": {"strand": str((i-1) // 8 + 1)}
    })

# Batch create
response = httpx.post("http://localhost:5001/api/v1/links/batch", json={
    "links": links,
    "dry_run": False,
    "request_id": "deploy-64-ont"
})

result = response.json()
print(f"Created {result['total_created']} links in {result['duration_ms']}ms")
# Output: Created 64 links in 420ms
```

## 4.6 Link Events

Link operations emit WebSocket events:

- `link.created`: New link created
- `link.deleted`: Link deleted
- `link.updated`: Link updated
- `link.status_changed`: Effective status changed
- `batch.completed`: Batch operation finished

**Example Event**:

```json
{
  "type": "link.created",
  "data": {
    "link_id": 123,
    "a_interface_id": 1,
    "b_interface_id": 2,
    "effective_status": "UP"
  },
  "correlation_id": "batch-001",
  "timestamp": "2025-10-05T10:00:00Z"
}
```

## 4.7 Testing

**Integration Tests**: `backend/tests/test_batch_operations_integration.py`

6 tests covering:

1. Single link creation (success path)
2. Validation errors (non-existent interfaces)
3. Batch link deletion
4. Health check endpoint
5. End-to-end latency measurement
6. Python fallback behavior

**Run Tests**:

```bash
pytest backend/tests/test_batch_operations_integration.py -v
```

**Expected Results**:

- All tests pass with Go service running (port 50052)
- Tests fallback to Python stub if Go service unavailable
- Latency test: <5s for 10 links

## 4.8 Troubleshooting

**Problem**: Batch operations return `FALLBACK_NOT_IMPLEMENTED` errors

**Solution**: Go batch service not running. Start it:

```bash
cd engine-go/cmd/batch_service
go run main.go
```

**Problem**: Slow batch operations (>10s for 64 links)

**Solution**:

1. Check Go service is running: `GET /api/v1/batch/health`
2. Verify response shows `"backend": "go"`
3. Restart Go service if needed

**Problem**: Interface validation errors

**Solution**:

1. Ensure devices are provisioned (creates interfaces)
2. Check interface IDs exist: `GET /api/v1/interfaces`
3. Verify interfaces not already linked: `GET /api/v1/links`

## 4.9 Future Enhancements

**Planned (Week 3 Day 15)**:

- Full Python fallback implementation (not just stub)
- Batch optical recomputation optimization
- WebSocket progress updates for large batches
- CSV import/export for bulk topology changes

**Under Consideration**:

- Link templates (pre-configured fiber strands)
- Batch link updates (modify existing links in bulk)
- Transaction rollback on partial failures
- Rate limiting for batch operations
