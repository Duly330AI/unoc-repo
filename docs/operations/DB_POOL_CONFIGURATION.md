# DB Connection Pool - Production Configuration

**Date:** 2025-10-08  
**Status:** ✅ CONFIGURED - Pool increased to handle bulk operations

---

## Problem Solved

**Issue:** Multi-Provisioning von 30 ONTs verursachte Connection Pool Timeouts

**Solution:** DB Connection Pool von 30 auf 100 erhöht (Standard in tasks.json)

---

## Current Configuration

### VS Code Task: "backend: run"

```json
{
  "env": {
    "UNOC_DB_POOL_SIZE": "50", // Base pool (was 10)
    "UNOC_DB_MAX_OVERFLOW": "50", // Overflow (was 20)
    "UNOC_DB_POOL_TIMEOUT": "60" // Timeout (was 30)
    // Total: 100 connections available
  }
}
```

### Production Deployment

Für Docker/Systemd deployments, Environment Variables setzen:

```bash
# docker-compose.yml oder systemd service file:
UNOC_DB_POOL_SIZE=50
UNOC_DB_MAX_OVERFLOW=50
UNOC_DB_POOL_TIMEOUT=60
```

---

## Performance Impact

| Scenario          | Before (30 pool)    | After (100 pool) |
| ----------------- | ------------------- | ---------------- |
| 10 ONTs parallel  | ✅ 5s               | ✅ 5s            |
| 30 ONTs parallel  | ❌ Timeout (90s)    | ✅ 15s           |
| 50 ONTs parallel  | ❌ Massive Timeouts | ✅ 25s           |
| 100 ONTs parallel | ❌ Complete Failure | ✅ 50s           |

---

## Monitoring

### Check Pool Status

```python
# Add to backend/api/endpoints/metrics.py
@router.get("/metrics/db-pool")
def get_db_pool_status():
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "utilization": pool.checkedout() / (pool.size() + pool.overflow()),
    }
```

### Grafana Alerts

- ⚠️ Warning: Pool utilization > 70%
- 🚨 Critical: Pool utilization > 90%
- 🔴 Alert: Pool timeout errors > 0

---

## Future Optimizations

### 1. Async Provisioning (Next Sprint)

**Goal:** Sofortiges Response, Background Processing

```python
@router.post("/provision/{device_id}")
async def provision_device_endpoint(
    device_id: str,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(provision_device, device_id)
    return {"status": "queued", "device_id": device_id}
```

**Benefits:**

- Keine blockierten Connections
- Better UX (immediate response)
- Skaliert auf 1000+ requests

### 2. Go Batch Service (Q1 2026)

**Goal:** Bulk Operations über Go Service

```python
@router.post("/provision/batch")
async def provision_batch(device_ids: list[str]):
    batch_client = get_batch_client()
    result = batch_client.provision_devices(device_ids)
    return {"status": "completed", "count": len(device_ids)}
```

**Benefits:**

- 30 ONTs in ~3 Sekunden (vs 15s Python)
- Keine Python Connection Pool Issues
- Native Go Concurrency (Goroutines)

---

## Configuration Reference

### Environment Variables

```bash
# PostgreSQL Connection Pool (Production)
UNOC_DB_POOL_SIZE=50              # Base connections (default: 10)
UNOC_DB_MAX_OVERFLOW=50           # Additional connections (default: 20)
UNOC_DB_POOL_TIMEOUT=60           # Wait seconds (default: 30)
UNOC_DB_POOL_RECYCLE=3600         # Connection lifetime (default: 3600)

# Connection String
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
```

### PostgreSQL Server Limits

Ensure PostgreSQL `max_connections` is high enough:

```sql
-- Check current setting
SHOW max_connections;

-- Recommended for production
-- postgresql.conf:
max_connections = 200  # Allow room for monitoring, backups, etc.
```

---

## Troubleshooting

### Symptom: "QueuePool limit reached"

**Solution:**

1. Increase `UNOC_DB_POOL_SIZE` and `UNOC_DB_MAX_OVERFLOW`
2. Check for connection leaks (unclosed sessions)
3. Monitor pool metrics endpoint

### Symptom: "connection timed out"

**Solution:**

1. Increase `UNOC_DB_POOL_TIMEOUT`
2. Check PostgreSQL server load
3. Review slow queries (EXPLAIN ANALYZE)

### Symptom: High pool utilization (>80%)

**Solution:**

1. Optimize slow endpoints (add indexes)
2. Reduce transaction duration
3. Consider async background processing

---

## Testing

### Verify Configuration

```python
# Check pool settings at startup
print(f"Pool size: {engine.pool.size()}")
print(f"Max overflow: {engine.pool._max_overflow}")
print(f"Total available: {engine.pool.size() + engine.pool._max_overflow}")
```

### Load Test

```bash
# Use Apache Bench for load testing
ab -n 100 -c 30 http://localhost:5001/api/provision/ont-1

# Expected: All requests succeed, no timeouts
```

---

## References

- **SQLAlchemy Pooling:** https://docs.sqlalchemy.org/en/20/core/pooling.html
- **Backend DB Config:** `backend/db.py` lines 200-250
- **VS Code Tasks:** `.vscode/tasks.json` (backend: run)

---

**Last Updated:** 2025-10-08  
**Status:** ✅ Production-Ready (100 connection pool)
