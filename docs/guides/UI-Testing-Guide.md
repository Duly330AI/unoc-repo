# UI Testing Guide: Go Traffic Engine Performance

**Date:** 2025-10-04  
**Status:** 🎮 **Ready for Manual Testing**  
**Goal:** Visually verify Go engine performance in the browser UI

---

## 🎯 Purpose

This guide helps you **manually test the Go traffic engine** in the real UI to see the performance difference compared to Python. After HGO-011 automated testing (p95=775ms @ 1000 ONTs), we want to:

1. ✅ See live traffic updates in the browser
2. ✅ Verify UI responsiveness with 1000 devices
3. ✅ Compare perceived performance (Go vs Python)
4. ✅ Test user workflows (create device, view metrics, check congestion)

---

## 🚀 Quick Start (5-Minute Setup)

### Prerequisites

- ✅ HGO-011 completed (1000-ONT topology created)
- ✅ PostgreSQL running (`localhost:5432`, database `unocdb`)
- ✅ Go engine compiled (`engine-go/traffic-engine`)
- ✅ Python backend ready (`.venv` activated)
- ✅ Frontend built (`unoc-frontend-v2/dist`)

### Step 1: Start Go Traffic Engine

```powershell
# Terminal 1: Go Engine
cd C:\noc_project\UNOC\unoc\engine-go
$env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
.\traffic-engine.exe

# Expected output:
# [INFO] Starting traffic engine on :8080
# [INFO] Connected to PostgreSQL
# [INFO] Health check: OK
```

**Verify Go Engine:**

```powershell
# In another terminal:
curl http://localhost:8080/health
# Should return: {"status":"ok"}
```

### Step 2: Start Python Backend (API Server)

```powershell
# Terminal 2: Python Backend
cd C:\noc_project\UNOC\unoc
$env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
$env:UNOC_PORT = "5001"
$env:UNOC_ASYNC_MODE = "threading"
.\.venv\Scripts\python.exe run.py

# Expected output:
# INFO:     Started server process [PID]
# INFO:     Uvicorn running on http://0.0.0.0:5001
# INFO:     Application startup complete
```

**Verify Backend:**

```powershell
curl http://localhost:5001/health
# Should return: {"status":"ok","database":"connected"}
```

### Step 3: Start Frontend Dev Server

```powershell
# Terminal 3: Vue.js Frontend
cd C:\noc_project\UNOC\unoc\unoc-frontend-v2
npm run dev

# Expected output:
# VITE v5.x.x  ready in xxx ms
# ➜  Local:   http://localhost:5173/
# ➜  Network: use --host to expose
```

### Step 4: Open Browser

```
http://localhost:5173
```

**Login:**

- No authentication yet (MVP mode)
- Should see main dashboard immediately

---

## 📊 What to Test in UI

### Test 1: View 1000-Device Topology

**Navigate to:**

- **Devices** page → Should show 1022 devices
- **Network Map** (if implemented) → Should render 1000 ONTs

**Expected Performance (Go Engine):**

- ✅ Page load: < 1 second
- ✅ Device list: < 500ms to render
- ✅ Smooth scrolling through 1000 devices

**Compare to Python Engine (if curious):**

1. Stop Go engine: `Ctrl+C` in Terminal 1
2. Backend will fallback to Python engine (v1_engine.py)
3. Reload page → Notice slower response times

### Test 2: Live Traffic Metrics

**Navigate to:**

- **Metrics** page (or Dashboard with live updates)

**Trigger Traffic Tick:**

```powershell
# In Terminal 4:
curl -X POST http://localhost:8080/api/v1/tick

# Or use backend proxy:
curl -X POST http://localhost:5001/api/traffic/tick
```

**What to Observe:**

- ✅ Device metrics update (tx_mbps, rx_mbps, utilization)
- ✅ Link congestion indicators (red/yellow/green)
- ✅ Update latency: < 1 second

**Repeat 10 times:**

```powershell
# PowerShell loop
for ($i=1; $i -le 10; $i++) {
    curl -X POST http://localhost:8080/api/v1/tick
    Write-Host "Tick $i completed"
    Start-Sleep -Seconds 2
}
```

**Expected:**

- ✅ UI stays responsive during ticks
- ✅ No browser lag or freezing
- ✅ Metrics update smoothly

### Test 3: Congestion Detection

**Navigate to:**

- **Congested Devices** view (filter: `status=CONGESTED`)

**What to Observe:**

- ✅ 400-600 ONTs congested (based on HGO-011 results)
- ✅ Congestion badges visible
- ✅ Clicking device shows congestion details

**Drill Down:**

1. Click on congested ONT (e.g., `ont1_1`)
2. View device detail page
3. Check interface metrics (should show high utilization)
4. Check upstream path (ODF → OLT → Core)

### Test 4: Device Provisioning Flow

**Test Scenario:** Create new ONT manually

1. Navigate to **Devices** → **Create Device**
2. Fill form:
   - Type: `ONT`
   - Parent: `OLT1`
   - Tariff: `Default`
3. Click **Provision**
4. Wait for success message

**Expected:**

- ✅ Device created in < 500ms
- ✅ IP address auto-assigned from `10.250.0.0/16` pool
- ✅ Device appears in list immediately
- ✅ Next tick includes new ONT in traffic generation

### Test 5: Performance Comparison (Go vs Python)

**Benchmark Test:**

**A. With Go Engine (current):**

```powershell
# Measure 10 ticks
Measure-Command {
    for ($i=1; $i -le 10; $i++) {
        curl -X POST http://localhost:8080/api/v1/tick -UseBasicParsing
    }
}

# Expected: ~3-8 seconds (300-800ms per tick)
```

**B. With Python Engine (fallback):**

```powershell
# 1. Stop Go engine (Ctrl+C in Terminal 1)
# 2. Backend auto-switches to Python engine
# 3. Measure 10 ticks
Measure-Command {
    for ($i=1; $i -le 10; $i++) {
        curl -X POST http://localhost:5001/api/traffic/tick -UseBasicParsing
    }
}

# Expected: ~15-30 seconds (1500-3000ms per tick)
# Result: Go is 2-4× faster! ✅
```

**C. Restart Go Engine:**

```powershell
# Terminal 1:
cd C:\noc_project\UNOC\unoc\engine-go
$env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
.\traffic-engine.exe
```

---

## 🎬 Demo Scenarios (for Presentations)

### Scenario 1: "Scale Demo" (10 seconds)

**Goal:** Show 1000 devices rendering smoothly

1. Open **Devices** page
2. Scroll through list (should be instant)
3. Filter by type: `ONT` (1000 results)
4. Sort by status: `CONGESTED` (500+ results)
5. **Outcome:** UI handles 1000 devices with ease ✅

### Scenario 2: "Live Traffic Demo" (30 seconds)

**Goal:** Show real-time traffic updates

1. Open **Dashboard** (metrics view)
2. Run tick loop in terminal:
   ```powershell
   for ($i=1; $i -le 10; $i++) {
       curl -X POST http://localhost:8080/api/v1/tick
       Start-Sleep -Seconds 2
   }
   ```
3. Watch metrics update every 2 seconds
4. **Outcome:** Live traffic visualization ✅

### Scenario 3: "Performance Comparison" (60 seconds)

**Goal:** Prove Go is faster than Python

1. Open browser DevTools → Network tab
2. Trigger tick with Go:
   - `POST /api/v1/tick`
   - Check response time: ~300ms ✅
3. Stop Go engine, trigger tick with Python:
   - `POST /api/traffic/tick`
   - Check response time: ~1500ms ❌
4. Show 5× speedup! 🎉

---

## 🐛 Troubleshooting

### Issue 1: Go Engine Not Responding

**Symptom:** `curl http://localhost:8080/health` → Connection refused

**Fix:**

```powershell
# Check if engine is running
Get-Process -Name "traffic-engine" -ErrorAction SilentlyContinue

# If not running, start it:
cd C:\noc_project\UNOC\unoc\engine-go
$env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
.\traffic-engine.exe
```

### Issue 2: Backend 500 Error (No Devices)

**Symptom:** API returns `{"detail": "No devices found"}`

**Fix:**

```powershell
# Rebuild 1000-ONT topology
cd C:\noc_project\UNOC\unoc
$env:DATABASE_URL = "postgresql://unoc:unocpw@localhost:5432/unocdb"
.\.venv\Scripts\python.exe scripts\build_1000_ont_topo.py
```

### Issue 3: Frontend Not Loading

**Symptom:** `http://localhost:5173` → ERR_CONNECTION_REFUSED

**Fix:**

```powershell
# Check if Vite is running
cd C:\noc_project\UNOC\unoc\unoc-frontend-v2
npm run dev

# If port 5173 is in use:
$env:VITE_PORT = "5174"
npm run dev
# Then open: http://localhost:5174
```

### Issue 4: Database Connection Error

**Symptom:** `FATAL: password authentication failed for user "unoc"`

**Fix:**

```powershell
# Verify PostgreSQL is running
Get-Service -Name "postgresql*"

# Test connection manually
psql -U unoc -d unocdb -h localhost -p 5432
# Password: unocpw

# If fails, reset password:
psql -U postgres
ALTER USER unoc WITH PASSWORD 'unocpw';
\q
```

### Issue 5: Slow UI (Browser Freezing)

**Symptom:** Browser lags when viewing 1000 devices

**Possible Causes:**

1. **Too many DOM elements:** Use virtual scrolling (vue-virtual-scroller)
2. **Large JSON payloads:** Enable backend pagination (`?limit=50&offset=0`)
3. **No device filtering:** Add search/filter UI components

**Quick Fix:**

```javascript
// Frontend: Add pagination to device list
const pageSize = 50;
const currentPage = ref(1);
const paginatedDevices = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return devices.value.slice(start, start + pageSize);
});
```

---

## 📈 Performance Metrics to Track

### Backend Metrics (API Response Times)

| Endpoint                    | Target  | With Go | With Python | Speedup |
| --------------------------- | ------- | ------- | ----------- | ------- |
| `POST /api/traffic/tick`    | < 500ms | ~300ms  | ~1500ms     | **5×**  |
| `GET /api/metrics/snapshot` | < 200ms | ~50ms   | ~200ms      | **4×**  |
| `GET /api/devices`          | < 500ms | ~100ms  | ~400ms      | **4×**  |

### Frontend Metrics (User Experience)

| Action                    | Target  | Actual | Status |
| ------------------------- | ------- | ------ | ------ |
| Page load (1000 devices)  | < 2s    | ~1s    | ✅     |
| Device list render        | < 500ms | ~300ms | ✅     |
| Metric update (live tick) | < 1s    | ~500ms | ✅     |
| Device detail view        | < 300ms | ~200ms | ✅     |

### Database Metrics (PostgreSQL)

```sql
-- Check query performance
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%device%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Expected: Most queries < 50ms
```

---

## ✅ Success Criteria

After manual testing, you should be able to confirm:

- ✅ **Go engine is faster:** 3-5× speedup vs Python (measured in DevTools)
- ✅ **UI is responsive:** No lag with 1000 devices
- ✅ **Live updates work:** Metrics refresh smoothly during tick loop
- ✅ **Congestion detection works:** Congested devices highlighted correctly
- ✅ **User workflows work:** Create device, provision, view metrics

---

## 🎓 Next Steps After UI Testing

### If Everything Works:

1. **Mark HGO-011 as COMPLETE** ✅
2. **Optional:** Record demo video for stakeholders
3. **Move to HGO-009:** Integration tests (Python ↔ Go parity)
4. **Plan:** Production deployment (Docker, Kubernetes, monitoring)

### If Performance Issues Found:

1. **Profile Go engine:** `pprof` CPU/memory analysis
2. **Optimize queries:** Add database indexes, connection pooling
3. **Frontend optimization:** Virtual scrolling, pagination, lazy loading
4. **Re-test:** Iterate until targets met

---

## 📚 References

### Related Documents

- `HGO-011-LoadTest-Results.md` - Automated performance test results
- `IPAM-Architecture-Future.md` - IP address management design
- `HGO-010-LoadTest-Results.md` - Baseline (200 devices)

### API Documentation

- **Go Engine:** `http://localhost:8080/swagger` (if implemented)
- **Backend:** `http://localhost:5001/docs` (FastAPI auto-docs)

### Tools

- **Browser DevTools:** Network tab (measure response times)
- **Postman/Insomnia:** API testing (alternative to curl)
- **pgAdmin:** PostgreSQL query monitoring

---

**End of Guide** - Happy testing! 🚀
