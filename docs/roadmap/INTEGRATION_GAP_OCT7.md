# GO Services Integration Gap - Critical Issue Discovery

**Date:** October 7, 2025  
**Discovered By:** New LLM agent during code review  
**Status:** 🚨 **CRITICAL** - Production speedups unavailable  
**Priority:** **HIGHEST** - Must integrate before any other work

---

## Executive Summary

GO microservices (Optical PathFinder, Status Propagation, Batch Operations) are **fully built, tested, and running** but **NOT integrated** into FastAPI production code paths. This means the promised 4,000× and 30,000× performance improvements are unavailable to users.

**Impact:**

- Optical operations: Running at 40s/ONT (Python) instead of 10ms (GO)
- Status propagation: Running at 2000ms (Python) instead of 66μs (GO)
- Sandbox provisioning: Takes 60 minutes instead of <60 seconds
- **Result:** User experience unchanged despite 3 weeks of GO development

**Root Cause:**
Previous LLM agent completed Week 1-2 roadmap (build GO services, write tests) but **skipped the integration step**. Services listen on ports, pass tests, but production FastAPI endpoints never call them.

---

## Service-by-Service Analysis

### 1. Traffic Engine (Port 8080) ✅ **THE EXCEPTION - WORKS CORRECTLY**

**Status:** ✅ Integrated & Working  
**Code:** `backend/services/traffic_engine.py` Line ~140

```python
from backend.clients.traffic_go_client import TrafficGoClient

class TrafficEngine:
    def __init__(self):
        self._go_client = TrafficGoClient(use_fallback=True)  # ✅ Correct

    def tick(self):
        result = self._go_client.tick(...)  # ✅ Calls GO service
```

**Evidence (Terminal Logs):**

```json
{"level":"info","service":"traffic","method":"POST","path":"/tick","status":200,"duration_ms":48}
{"level":"info","service":"traffic","method":"GET","path":"/snapshot","status":200,"duration_ms":2}
```

**Why It Works:** `traffic_engine.py` correctly instantiates `TrafficGoClient` and calls it. This is the **reference pattern** for Optical/Status integration.

---

### 2. Optical PathFinder (Port 50051) ❌ **BUILT BUT NOT USED**

**Status:** ❌ Service runs, production code ignores it  
**GO Service:** Operational, Dijkstra algorithm implemented, 4,000× faster than Python  
**Problem:** Python code still calls `resolve_optical_path()` function

**Current Code (WRONG):**

```python
# backend/services/optical_service.py (Line 46-178)
from backend.services.optical_path_resolver import resolve_optical_path

def recompute_optical_paths_for_affected_onts(...):
    for ont in onts:
        result = resolve_optical_path(ont.id)  # ❌ Python function (40s)
```

**Should Be (CORRECT):**

```python
# backend/services/optical_service.py
from backend.clients.go_services.optical_client import get_optical_client

def recompute_optical_paths_for_affected_onts(...):
    client = get_optical_client()  # ✅ GO client
    for ont in onts:
        result = client.get_path(ont_id=ont.id)  # ✅ gRPC call (10ms)
```

**Evidence (Terminal Logs):**

```json
{"level":"info","service":"optical-service","message":"listening on [::]:50051"}
{"level":"debug","service":"optical-service","message":"Health check"}
# NO GetPath or RecomputePaths calls! Only health checks every 60s.
```

**Files to Modify:**

1. `backend/services/optical_service.py` (Line 46-178) - Main integration point
2. `backend/api/endpoints/links_helpers_create.py` (Line 254) - Link creation hook
3. `backend/api/endpoints/devices_helpers_mutation_core.py` (Line 396) - Device mutation hook

**Client Already Exists:** `backend/clients/go_services/optical_client.py` ✅ Ready to use!

---

### 3. Status Propagation (Port 50053) ❌ **BUILT BUT NOT USED**

**Status:** ❌ Service runs, production code ignores it  
**GO Service:** Operational, BFS causal chain detection, 30,000× faster than Python  
**Problem:** Python code still uses `status_recompute.py` Python BFS

**Current Code (WRONG):**

```python
# backend/services/status_recompute.py
# Uses pure Python BFS algorithm (2000ms for 200 devices)
def recompute_devices_status(...):
    # Python BFS traversal
    visited = set()
    queue = deque(changed_devices)
    while queue:
        # ... (2000ms)
```

**Should Be (CORRECT):**

```python
# backend/services/status_recompute.py
from backend.clients.go_services.status_client import get_status_client

def recompute_devices_status(...):
    client = get_status_client()
    if client._go_available:
        result = client.propagate_status(
            changed_device_ids=[d.id for d in changed],
            update_database=True
        )  # ✅ GO gRPC call (66μs)
    else:
        # Fallback to Python BFS (resilience)
        result = python_bfs_propagation(...)
```

**Evidence (Terminal Logs):**

```json
{"level":"info","service":"status-service","message":"listening on [::]:50053"}
{"level":"debug","service":"status-service","message":"Health check"}
# NO PropagateStatus calls! Only health checks.
```

**Files to Modify:**

1. `backend/services/status_recompute.py` (entire file) - Main integration point

**Client Already Exists:** `backend/clients/go_services/status_client.py` ✅ Ready to use!

---

### 4. Batch Operations (Port 50052) ⚠️ **PARTIAL INTEGRATION**

**Status:** ⚠️ Service runs, API endpoint exists, **no frontend UI**  
**GO Service:** Operational, bulk SQL INSERT + optical coordination  
**Problem:** Frontend doesn't call `/api/links/batch` endpoint

**Current Code (GOOD):**

```python
# backend/api/endpoints/links.py (Line 113-181)
@router.post("/batch", response_model=BatchCreateLinksResponse, status_code=201)
def batch_create_links_endpoint(payload: BatchLinkCreateRequest):
    client = get_batch_client()
    result = client.batch_create_links(...)  # ✅ Correct!
    return BatchCreateLinksResponse(**result)
```

**Evidence (Terminal Logs):**

```json
{"level":"info","service":"batch-service","message":"listening on [::]:50052"}
{"level":"debug","service":"batch-service","message":"Health check"}
# NO BatchCreateLinks calls! Endpoint unused by frontend.
```

**What's Missing:**

1. Frontend Vue component for bulk link creation UI
2. Frontend routing to `/api/links/batch`
3. UI integration tests

**Client Already Exists:** `backend/clients/go_services/batch_client.py` ✅ Ready to use!

---

## Integration Plan (3 Phases)

### Phase 1: Optical Service Integration (HIGHEST PRIORITY)

**Why First:**

- Biggest user impact (4,000× speedup)
- Smallest code change (~30 lines, 3 files)
- Critical for link/device creation workflows
- Batch service depends on it

**Tasks:**

1. Modify `backend/services/optical_service.py`:
   - Import `get_optical_client()`
   - Replace `resolve_optical_path(ont_id)` with `client.get_path(ont_id=ont_id)`
   - Keep Python fallback logic
2. Modify `backend/api/endpoints/links_helpers_create.py` (Line 254)
3. Modify `backend/api/endpoints/devices_helpers_mutation_core.py` (Line 396)
4. Test:
   - Run integration tests: `pytest backend/tests/test_optical_compute_integration.py`
   - Create device → Check GO logs show `GetPath` requests
   - Stop GO service → Verify Python fallback works

**Estimated Time:** 30 minutes  
**Risk:** Low (fallback ensures resilience)

---

### Phase 2: Status Service Integration (HIGH PRIORITY)

**Why Second:**

- Also huge impact (30,000× speedup)
- Slightly more complex (status hooks scattered across codebase)
- Independent of Optical service

**Tasks:**

1. Modify `backend/services/status_recompute.py`:
   - Import `get_status_client()`
   - Add GO client call before Python BFS
   - Keep Python fallback if GO unavailable
2. Test:
   - Run status tests: `pytest backend/tests/test_status_client_integration.py`
   - Change device status → Check GO logs show `PropagateStatus` requests
   - Stop GO service → Verify Python fallback works
3. Test causal chain:
   - Stop core device → Verify cascade to downstream devices
   - Check propagation time (<1ms vs 2000ms)

**Estimated Time:** 45 minutes  
**Risk:** Medium (status propagation is critical for system integrity)

---

### Phase 3: Batch Service UI Integration (MEDIUM PRIORITY)

**Why Last:**

- API already integrated (backend done!)
- Just needs frontend work
- Lower priority than Optical/Status (less critical workflows)

**Tasks:**

1. Create Vue component: `unoc-frontend-v2/src/components/BatchLinkCreator.vue`
   - Form: Select multiple interfaces
   - Button: "Create Links in Batch"
   - Progress indicator
2. Wire to API: `POST /api/links/batch`
3. Add to UI: Link management page
4. Test:
   - Create 64 links via UI
   - Check time (<10s vs 37 min)
   - Verify GO logs show `BatchCreateLinks` requests

**Estimated Time:** 2 hours (frontend component + testing)  
**Risk:** Low (API already validated)

---

## Verification Checklist

After each phase, verify:

**1. GO Service Receives Requests:**

```bash
# Check terminal logs (PowerShell where GO service runs)
# BEFORE (Wrong):
{"level":"debug","message":"Health check"}

# AFTER (Correct):
{"level":"info","method":"GetPath","ont_id":"ont-1","duration_ms":10.5}
{"level":"info","method":"PropagateStatus","affected_devices":12}
{"level":"info","method":"BatchCreateLinks","created_links":64,"duration_ms":8200}
```

**2. Response Times Improved:**

```bash
# Optical: 40s → <20ms (device/link creation)
# Status: 2000ms → <1ms (device status change)
# Batch: 37min → <10s (64 links)
```

**3. Python Fallback Works:**

```bash
# Stop GO service
.\scripts\stop_all_services.ps1

# Run tests - should pass using Python fallback
.\.venv\Scripts\python.exe -m pytest -q

# Expected logs:
# "⚠️ Go optical-service unavailable, falling back to Python"
# "⚠️ Go status-service unavailable, falling back to Python"
```

**4. Integration Tests Pass:**

```bash
pytest backend/tests/test_optical_compute_integration.py  # Optical
pytest backend/tests/test_status_client_integration.py    # Status
pytest backend/tests/test_batch_operations_integration.py # Batch
```

---

## Lessons Learned

**What Went Wrong:**

1. **Incomplete roadmap execution:** Week 2 docs said "COMPLETE" but integration was skipped
2. **Test-only validation:** Integration tests passed (good!) but production code never updated
3. **No end-to-end verification:** Services ran but no smoke test for actual API usage
4. **Documentation mismatch:** Docs claimed "PRODUCTION-READY" but services were unused

**How to Prevent:**

1. **Define "complete" clearly:** Service is complete when **production code calls it**, not just tests
2. **Add E2E smoke tests:** After service starts, trigger actual API workflow and verify GO logs
3. **Code review checklist:** Before marking phase complete, grep codebase for client usage
4. **Log monitoring:** Alert if GO service receives <1 req/min (health checks only = not integrated)

---

## Success Criteria (Integration Complete)

- ✅ Optical service: `optical_service.py` calls `OpticalClient.get_path()`
- ✅ Status service: `status_recompute.py` calls `StatusClient.propagate_status()`
- ✅ Batch service: Frontend calls `/api/links/batch` endpoint
- ✅ GO service logs show actual API requests (not just health checks)
- ✅ Response times match targets (10ms optical, <1ms status, <10s batch)
- ✅ Python fallback works (stop GO → tests pass)
- ✅ Integration tests pass
- ✅ Manual smoke test: Create device → <1s response (was 40s)

---

**Next Action:** Begin Phase 1 - Optical Service Integration
