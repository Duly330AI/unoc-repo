# Port Summary Integration Checklist

Checklist für Python Backend Integration des Port Summary Service.

---

## ✅ **Phase 1: Setup & Validation** (30 min)

### **Service Setup**

- [ ] Port Summary Service gebaut (`go build`)
- [ ] Service startet erfolgreich
- [ ] Database connection funktioniert
- [ ] Initial load successful (5-10ms)
- [ ] ONT paths computed (83 ONTs expected)
- [ ] PON occupancy computed (83 ONTs across 2 PON ports)

**Validation Command**:

```powershell
cd engine-go/cmd/port-summary-service
$env:DATABASE_URL="postgresql://unoc:unocpw@localhost:5432/unocdb?sslmode=disable"
$env:PORT="50054"
.\port-summary-service.exe
```

**Expected Output**:

```
✅ Loaded 113 devices, 368 interfaces, 112 links in 5.6ms
✅ Found 83 ONT devices, computed optical paths for 83 ONTs
✅ Port Summary Service listening on port 50054
```

---

## ✅ **Phase 2: Proto Generation** (15 min)

### **Python gRPC Code**

- [ ] `grpcio` installed (`pip install grpcio grpcio-tools`)
- [ ] Proto files generated:
  ```powershell
  cd engine-go
  python -m grpc_tools.protoc `
      --python_out=../backend/proto `
      --grpc_python_out=../backend/proto `
      --proto_path=proto `
      proto/port_summary/port_summary.proto
  ```
- [ ] Files created:
  - `backend/proto/port_summary/port_summary_pb2.py`
  - `backend/proto/port_summary/port_summary_pb2_grpc.py`
- [ ] Import test passes:
  ```python
  from backend.proto.port_summary import port_summary_pb2
  print("✅ Proto imported successfully!")
  ```

---

## ✅ **Phase 3: Python Client Integration** (30 min)

### **Client Setup**

- [ ] `port_summary_client.py` exists in `backend/clients/`
- [ ] Environment variables set:
  ```bash
  USE_PORT_SUMMARY_SERVICE=1
  PORT_SUMMARY_SERVICE_HOST=localhost
  PORT_SUMMARY_SERVICE_PORT=50054
  ```
- [ ] Client connects successfully:

  ```python
  from backend.clients.port_summary_client import get_port_summary_client

  client = get_port_summary_client()
  assert client.is_available(), "❌ Service not available!"
  print("✅ Client connected!")
  ```

### **Health Check Test**

- [ ] Health check works:

  ```python
  from backend.proto.port_summary import port_summary_pb2

  client = get_port_summary_client()
  # Should not raise exception
  ```

---

## ✅ **Phase 4: Endpoint Integration** (1 hour)

### **Option A: New Endpoint (Recommended for testing)**

Create new endpoint first to test integration:

```python
# backend/api/endpoints/ports.py (NEW FILE)

from fastapi import APIRouter, HTTPException
from backend.clients.port_summary_client import get_port_summary_client

router = APIRouter(prefix="/ports", tags=["ports"])

@router.get("/devices/{device_id}/summary")
async def get_port_summary(device_id: str):
    """
    Get port summary for a device (FAST - via Go service).

    Returns interface occupancy data with 50-100× speedup!
    """
    client = get_port_summary_client()

    if not client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Port Summary Service unavailable"
        )

    summary = await client.get_port_summary(device_id)

    if summary is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to get port summary"
        )

    return {
        "device_id": device_id,
        **summary
    }

@router.get("/devices/bulk")
async def get_bulk_port_summary(device_ids: list[str]):
    """
    Get port summaries for multiple devices (BATCH).

    Much faster than individual requests!
    """
    client = get_port_summary_client()

    if not client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Port Summary Service unavailable"
        )

    summaries = await client.get_bulk_port_summary(device_ids)

    return {
        "count": len(summaries),
        "summaries": summaries
    }
```

**Checklist**:

- [ ] New file created: `backend/api/endpoints/ports.py`
- [ ] Router registered in `backend/api/routes.py`:

  ```python
  from backend.api.endpoints import ports

  # In create_router():
  api_router.include_router(ports.router)
  ```

- [ ] Endpoint accessible: `GET /api/ports/devices/{id}/summary`
- [ ] Response format correct (see below)

### **Option B: Update Existing Endpoint**

Update existing device endpoint with fallback logic:

```python
# backend/api/endpoints/devices.py (MODIFY EXISTING)

from backend.clients.port_summary_client import get_port_summary_client

@router.get("/{device_id}/ports")
async def get_device_ports(device_id: str, db: Session = Depends(get_db)):
    """Get port summary with automatic fallback."""

    # Try Go service first (FAST: 5-10ms)
    client = get_port_summary_client()
    if client.is_available():
        summary = await client.get_port_summary(device_id)
        if summary is not None:
            return summary

    # Fallback to Python implementation (SLOW: 250-700ms)
    logger.warning(f"Port Summary Service unavailable, using fallback for {device_id}")
    return compute_ports_python(device_id, db)  # Your existing code
```

**Checklist**:

- [ ] Existing endpoint identified
- [ ] Import added: `from backend.clients.port_summary_client import get_port_summary_client`
- [ ] Try/catch logic added
- [ ] Fallback to existing Python code works
- [ ] Logging added for fallback cases

---

## ✅ **Phase 5: Testing** (1 hour)

### **Manual Testing**

- [ ] Service running in terminal
- [ ] GET `/api/ports/devices/{olt_id}/summary` works
- [ ] Response format correct:
  ```json
  {
    "interfaces": [
      {
        "id": "uuid",
        "name": "PON1",
        "port_role": "PON",
        "effective_status": "up",
        "occupancy": 42,
        "capacity": 128
      }
    ]
  }
  ```
- [ ] Bulk endpoint works (if implemented)
- [ ] Error handling works (service down = fallback)

### **Performance Testing**

- [ ] Time measurement added:

  ```python
  import time

  start = time.time()
  summary = await client.get_port_summary(device_id)
  duration_ms = (time.time() - start) * 1000

  logger.info(f"Port summary fetched in {duration_ms:.2f}ms")
  ```

- [ ] Typical response time: **1-5ms** ✅
- [ ] Compare to old Python code: **250-700ms** → **5-10ms** 🚀

### **Unit Tests**

- [ ] Test file created: `backend/tests/test_port_summary_client.py`
- [ ] Test cases:
  - [ ] Client connects successfully
  - [ ] Health check works
  - [ ] Get port summary returns data
  - [ ] Bulk request works
  - [ ] Graceful fallback when service down
- [ ] All tests pass: `pytest backend/tests/test_port_summary_client.py`

---

## ✅ **Phase 6: Production Readiness** (2 hours)

### **Deployment**

- [ ] Start script created: `scripts/start_port_summary_service.sh`
- [ ] systemd service file (Linux) or Windows Service
- [ ] Auto-restart on crash
- [ ] Environment variables in .env
- [ ] Port 50054 open in firewall

### **Monitoring**

- [ ] Prometheus metrics endpoint (future Phase 2)
- [ ] Logging configured:
  ```python
  logger.info("✅ Port Summary Service connected")
  logger.warning("⚠️ Port Summary Service unavailable, using fallback")
  logger.error("❌ Port Summary Service error: ...")
  ```
- [ ] Health check in monitoring system
- [ ] Alert if service down for >5 minutes

### **Documentation**

- [ ] README updated with Port Summary section
- [ ] API docs updated (OpenAPI/Swagger)
- [ ] Team notified about new service
- [ ] Runbook created for operations team

---

## ✅ **Phase 7: Rollout** (1 hour)

### **Feature Flag**

- [ ] Feature flag implemented:

  ```python
  USE_PORT_SUMMARY_SERVICE = os.getenv("USE_PORT_SUMMARY_SERVICE", "0") == "1"

  if USE_PORT_SUMMARY_SERVICE:
      # Use Go service
  else:
      # Use Python legacy code
  ```

- [ ] Default: OFF (safe rollout)
- [ ] Enable per environment:
  - Dev: ON (testing)
  - Staging: ON (validation)
  - Production: OFF initially, then gradual rollout

### **Gradual Rollout**

- [ ] Week 1: Dev environment only
- [ ] Week 2: Staging + canary (10% production traffic)
- [ ] Week 3: 50% production traffic
- [ ] Week 4: 100% production traffic
- [ ] Monitor errors/latency at each step

### **Success Metrics**

- [ ] Average response time: <10ms ✅
- [ ] p95 latency: <20ms ✅
- [ ] Error rate: <0.1% ✅
- [ ] Fallback rate: <5% ✅ (service uptime >95%)
- [ ] User feedback: Positive (faster dashboards!)

---

## 📊 **Expected Results**

### **Performance Improvement**

```
Before (Python DB queries):
├─ Single OLT ports: 250-700ms
├─ 30 OLT dashboard: 15-20 seconds
└─ User experience: "Loading..." spinner

After (Go Service):
├─ Single OLT ports: 5-10ms (50-100× faster!)
├─ 30 OLT dashboard: 150-300ms (50× faster!)
└─ User experience: Instant response!
```

### **Resource Usage**

```
Go Service:
├─ Memory: ~50MB (in-memory data)
├─ CPU: <1% (idle), ~5% (under load)
├─ Initial load: 5-10ms
└─ Per-request: 1-2ms CPU time
```

---

## 🐛 **Common Issues & Solutions**

### **Issue 1: Service Won't Start**

```
Error: Failed to ping database: pq: SSL is not enabled
```

**Solution**: Add `?sslmode=disable` to DATABASE_URL

### **Issue 2: Proto Import Error**

```
ImportError: cannot import name 'port_summary_pb2'
```

**Solution**: Run proto generation command (Phase 2)

### **Issue 3: Client Always Unavailable**

```
WARNING: Port Summary Service unavailable (localhost:50054)
```

**Solution**: Check service is running on port 50054:

```powershell
Test-NetConnection localhost -Port 50054
```

### **Issue 4: Slow Performance**

```
Port summary still takes 200-500ms
```

**Solution**: Check you're actually calling Go service, not fallback:

```python
client = get_port_summary_client()
print(f"Using Go service: {client.is_available()}")
```

---

## 📞 **Support**

### **Logs to Check**

1. **Service logs**: Terminal where port-summary-service.exe runs
2. **Python logs**: FastAPI application logs
3. **Database logs**: PostgreSQL query logs (should be ZERO queries after service start!)

### **Debug Checklist**

- [ ] Service running? `Get-Process | Where-Object { $_.ProcessName -eq "port-summary-service" }`
- [ ] Port open? `Test-NetConnection localhost -Port 50054`
- [ ] Client connecting? Check Python logs for "✅ Port Summary Service connected"
- [ ] Using service? Check logs for "Using Go service: True"
- [ ] Performance good? Measure response times

---

## ✅ **Final Checklist**

Before marking integration COMPLETE:

- [ ] All Phase 1-7 checklists done
- [ ] Service running in production
- [ ] Feature flag enabled
- [ ] Performance metrics validated (50-100× speedup)
- [ ] Error rates acceptable (<0.1%)
- [ ] Team trained on new service
- [ ] Documentation complete
- [ ] Monitoring alerts configured

---

**Integration Status**: ⏳ IN PROGRESS

**Target Completion**: [DATE]

**Owner**: [TEAM/PERSON]

---

_For questions or issues, see [PORT_SUMMARY_PHASE1_COMPLETE.md](./PORT_SUMMARY_PHASE1_COMPLETE.md)_
