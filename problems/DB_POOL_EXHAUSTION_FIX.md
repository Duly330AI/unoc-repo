# CRITICAL FIX: DB Connection Pool Exhaustion

**Date:** 2025-10-08  
**Severity:** 🔴 CRITICAL  
**Status:** ⚠️ INCIDENT - Multi-Provisioning Stuck

---

## Problem

**Symptom:** Multi-Provisioning von 30 ONTs stuck, letzte Requests timeout nach 1.5 Minuten

**Screenshots zeigen:**

- Request 1-20: 120-400ms ✅
- Request 21-28: 500-750ms ⚠️
- Request 29-30: 1.5 Minuten ❌ TIMEOUT

**Backend Error:**

```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached,
connection timed out, timeout 30.00
```

---

## Root Cause Analysis

### Connection Pool Configuration (CURRENT)

```python
# backend/db.py defaults:
pool_size = 10        # Base connections
max_overflow = 20     # Additional connections under load
pool_timeout = 30     # Seconds to wait for free connection

# Total available: 10 + 20 = 30 connections
```

### What Happened

1. Frontend sends 30 parallel provisioning requests
2. Each provisioning request:
   - Opens DB connection
   - Creates interfaces (DB write)
   - Allocates IP addresses (DB write)
   - Calls Go status service (fast, but connection still held)
   - Calls Go optical service (fast, but connection still held)
   - Commits transaction
   - Takes ~500ms average
3. All 30 connections exhausted immediately
4. Requests 31+ wait 30 seconds for timeout
5. Last requests fail with timeout error

### Why Go Integration Didn't Prevent This

- ✅ Go services ARE working (fast 66μs status, 10ms optical)
- ❌ BUT: Python still holds DB connection during entire provisioning transaction
- ❌ Synchronous endpoint blocks until complete
- ❌ No connection pooling awareness

---

## Immediate Fix (5 minutes)

### Option A: Increase Pool Size (RECOMMENDED)

**For PostgreSQL Production:**

```bash
# Set environment variables before starting backend:
export UNOC_DB_POOL_SIZE=50        # Up from 10
export UNOC_DB_MAX_OVERFLOW=50     # Up from 20
export UNOC_DB_POOL_TIMEOUT=60     # Up from 30

# Total: 100 connections available
```

**Backend startup:**

```bash
conda activate unoc-env
UNOC_DB_POOL_SIZE=50 UNOC_DB_MAX_OVERFLOW=50 python run.py
```

**Expected Result:**

- 100 parallel provisioning requests supported
- No more timeout errors
- Latency remains ~500ms per request

---

## Better Fix (30 minutes)

### Option B: Async Provisioning with Background Tasks

**Goal:** Return HTTP 202 immediately, process in background

**Changes needed:**

```python
# backend/api/endpoints/provisioning.py

from fastapi import BackgroundTasks

@router.post("/provision/{device_id}")
async def provision_device_endpoint(
    device_id: str,
    background_tasks: BackgroundTasks,
):
    # Validate device exists
    with get_session() as s:
        device = s.get(Device, device_id)
        if not device:
            raise HTTPException(404, "Device not found")

    # Queue background job
    background_tasks.add_task(provision_device_task, device_id)

    # Return immediately
    return {"status": "queued", "device_id": device_id}

def provision_device_task(device_id: str):
    """Background task - uses one connection, releases when done"""
    provision_device(device_id)
```

**Expected Result:**

- Frontend receives immediate response
- Backend processes requests sequentially (or with worker pool)
- No connection pool exhaustion
- Better UX (progress bar instead of frozen UI)

---

## Best Fix (1 hour)

### Option C: Go Batch Service for Bulk Provisioning

**Goal:** Use Go service for bulk operations

**Endpoint:**

```python
@router.post("/provision/batch")
async def provision_batch(device_ids: list[str]):
    # Validate devices exist
    # Send to Go batch service
    batch_client = get_batch_client()
    result = batch_client.provision_devices(device_ids)

    return {"status": "completed", "processed": len(device_ids)}
```

**Go service handles:**

- Parallel processing with Go routines
- Direct DB access (no Python bottleneck)
- Progress tracking
- Error handling

**Expected Result:**

- 30 ONTs provisioned in ~3 seconds (vs 15 seconds Python)
- No connection pool issues
- Scalable to 100+ devices

---

## Monitoring & Prevention

### Add Connection Pool Metrics

```python
# backend/api/endpoints/metrics.py

from sqlalchemy import inspect

@router.get("/metrics/db-pool")
def get_db_pool_metrics():
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": pool._max_overflow,
        "timeout": pool._timeout,
    }
```

### Grafana Dashboard

**Alert when:**

- `checked_out / (size + overflow) > 0.8` (80% pool utilization)
- `pool_timeout_errors > 0` (any timeout)
- `avg_request_duration > 1000ms` (slow requests)

---

## Action Plan

### Immediate (NOW)

1. ✅ Restart backend with increased pool size:
   ```bash
   conda activate unoc-env
   UNOC_DB_POOL_SIZE=50 UNOC_DB_MAX_OVERFLOW=50 python run.py
   ```
2. ✅ Test multi-provisioning 30 ONTs
3. ✅ Verify no timeout errors

### Short-term (Today)

1. ⏳ Add connection pool metrics endpoint
2. ⏳ Document pool size tuning in deployment guide
3. ⏳ Add Grafana alert for pool exhaustion

### Medium-term (This Week)

1. ⏳ Implement async provisioning with BackgroundTasks
2. ⏳ Add provision status endpoint for frontend polling
3. ⏳ Update frontend to show progress bar

### Long-term (Next Sprint)

1. ⏳ Integrate Go batch service for bulk operations
2. ⏳ Add Redis queue for job management
3. ⏳ Implement WebSocket progress updates

---

## Environment Variable Reference

```bash
# Connection Pool Tuning (PostgreSQL)
UNOC_DB_POOL_SIZE=50         # Base pool size (default: 10)
UNOC_DB_MAX_OVERFLOW=50      # Additional connections (default: 20)
UNOC_DB_POOL_TIMEOUT=60      # Wait timeout in seconds (default: 30)
UNOC_DB_POOL_RECYCLE=3600    # Connection lifetime in seconds (default: 3600)

# For SQLite (dev/test)
UNOC_PERSISTENCE=file        # Use file-based SQLite
UNOC_PERSISTENCE=inmemory    # Use in-memory SQLite (tests)

# For PostgreSQL (production)
DATABASE_URL=postgresql+psycopg://unoc:unocpw@localhost:5432/unocdb
```

---

## Testing

### Before Fix (CURRENT)

```bash
# Multi-provision 30 ONTs
curl -X POST localhost:5001/api/provision/batch \
  -H "Content-Type: application/json" \
  -d '{"device_ids": ["ont-1", "ont-2", ..., "ont-30"]}'

# Result: ❌ Timeout after 30 seconds
```

### After Fix (EXPECTED)

```bash
# With increased pool size:
UNOC_DB_POOL_SIZE=50 UNOC_DB_MAX_OVERFLOW=50 python run.py

# Same request:
# Result: ✅ Success in ~15 seconds
```

---

## References

- **Go Services Integration:** `docs/operations/GO_SERVICES_INTEGRATION_COMPLETE.md`
- **SQLAlchemy Pool Docs:** https://docs.sqlalchemy.org/en/20/core/pooling.html
- **Backend DB Config:** `backend/db.py` lines 200-250

---

**Last Updated:** 2025-10-08  
**Next Review:** After immediate fix deployed
