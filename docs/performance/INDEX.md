# Performance Documentation Index

**Last Updated:** 2025-10-04

## 🎯 Current Performance State

**Go Traffic Engine:** ✅ **PRODUCTION-READY**

- **HGO-010:** 200-device load test → p95=~400ms ✅ (target: <500ms)
- **HGO-011:** 1000-device load test → p95=774.7ms ✅ (target: <2500ms)
- **Result:** 3-5× faster than Python engine for traffic ticks
- **Monitoring:** Prometheus/Grafana ✅ **AKTIV** (metrics collection + dashboards)

**Bottleneck Discovered:** Sandbox CRUD operations (link creation, device provisioning)

- **Root Cause:** O(N²) optical recompute in Python
- **Impact:** 64 links = 37 minutes (expected <30 seconds)
- **Solution:** Hybrid Python+Go architecture migration (see roadmap below)

---

## 📊 Load Test Results

### ✅ HGO-010: 200-Device Load Test (Phase 1)

- **File:** [HGO-010-LoadTest-Results.md](HGO-010-LoadTest-Results.md)
- **Status:** ✅ COMPLETE (2025-10-04)
- **Summary:**
  - Topology: 200 devices, 197 links, 192 ONTs
  - Performance: p95=~400ms (69% under 500ms target)
  - Decision: GO FOR PHASE 2 ✅

### ✅ HGO-011: 1000-Device Load Test (Phase 2)

- **File:** [HGO-011-LoadTest-Results.md](HGO-011-LoadTest-Results.md)
- **Status:** ✅ COMPLETE (2025-10-04)
- **Summary:**
  - Topology: 1000 devices, ~997 links, 1000 ONTs
  - Performance: p95=774.7ms (69% under 2500ms target), p99=1464ms
  - IP Pool Fix: Changed ont_mgmt from /24 (254 IPs) to /16 (65,534 IPs)
  - Decision: GO FOR PRODUCTION ✅

### ⏸️ HGO-012: UI Performance Testing (Manual)

- **File:** [../guides/UI-Testing-Guide.md](../guides/UI-Testing-Guide.md)
- **Status:** ⏸️ DEFERRED (pending Go Hybrid migration completion)
- **Goal:** Manually test Go engine in browser UI to verify perceived performance improvement
- **Expected:** See 3-5× speedup vs Python engine in real user workflows

---

## 🚀 Active Roadmap

### Operation Stable Foundation (3-Week Plan)

- **File:** [../roadmap/OPERATION-STABLE-FOUNDATION.md](../roadmap/OPERATION-STABLE-FOUNDATION.md)
- **Status:** 🟢 ACTIVE → **Week 2 in Progress** (Week 1: ✅ COMPLETE)
- **Goal:** Hybrid Python+Go architecture for 60-120× speedup in Sandbox operations
- **Timeline:**
  - **Week 1 (Complete):** ✅ Documentation cleanup + Go service scaffolding (gRPC, protobuf, Python clients) - [See WEEK1_COMPLETE.md](../roadmap/WEEK1_COMPLETE.md)
  - **Week 2 (Current):** 🚀 Optical compute migration to Go (800× speedup target) - [See WEEK2_KICKOFF.md](../roadmap/WEEK2_KICKOFF.md)
  - **Week 3 (Planned):** Batch operations in Go (260× speedup target)
- **Expected Results:**
  - Single link creation: 35s → 200ms (175× speedup)
  - 64 links batch: 37 min → 8s (262× speedup)
  - 64 ONTs provision: 60 min → 30s (120× speedup)
  - Overall Sandbox: 60-90 min → 45-60s (60-120× speedup)
- **Week 1 Achievements:**
  - ✅ All 3 Go services built and operational (Optical :50051, Batch :50052, Status :50053)
  - ✅ Python gRPC clients with fallback logic
  - ✅ Integration tests passing (3/3 PASS)
  - ✅ Startup scripts ready (start_services.ps1, stop_services.ps1)

---

## 🔧 Tools & Guides

### Test Harness

- **File:** [harness.md](harness.md)
- **Summary:** Guide for using `backend/tests/perf/` test harness
- **Key Features:**
  - PostgreSQL persistence override (bypasses inmemory mode)
  - Realistic topology builders (200-device, 1000-device)
  - `@pytest.mark.perf` marker for perf tests
  - Statistical analysis (p50, p95, p99)

### Profiling Guide

- **File:** [profiling.md](profiling.md)
- **Summary:** Tools for profiling Python backend and Go engine
- **Tools:**
  - Python: `cProfile`, `py-spy`, `memory_profiler`
  - Go: `pprof` (CPU, memory, goroutine, block profiles)
  - HTTP endpoints: `/debug/pprof/*` (Go engine)

### Metrics Reference

- **File:** [metrics.md](metrics.md)
- **Summary:** Go engine metrics exported via HTTP API
- **Endpoints:**
  - `GET /health` — Health check
  - `GET /api/v1/snapshot` — Current traffic state (devices, links, congestion)
  - `POST /api/v1/tick` — Trigger traffic simulation tick

---

## 📈 Executive Summary

- **File:** [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)
- **Summary:** High-level overview of Go engine migration journey
- **Status:** ⚠️ NEEDS UPDATE (remove HGO-012 Prometheus/Grafana reference)
- **Content:**
  - HGO-001 to HGO-011 milestones
  - Performance benchmarks
  - Decision points (GO/NO-GO gates)

---

## 📁 Archived Roadmaps

Previous roadmaps superseded by **Operation Stable Foundation**:

- [../archive/2025-10-04-old-roadmaps/HYBRID_GO_ROADMAP.md](../archive/2025-10-04-old-roadmaps/HYBRID_GO_ROADMAP.md) — Early Go migration plan
- [../archive/2025-10-04-old-roadmaps/OPTIMIZATION_ROADMAP.md](../archive/2025-10-04-old-roadmaps/OPTIMIZATION_ROADMAP.md) — Python-only optimization attempts
- [../archive/2025-10-04-old-roadmaps/HGO-010-STATUS.md](../archive/2025-10-04-old-roadmaps/HGO-010-STATUS.md) — HGO-010 planning doc (test now complete)

---

## 🔍 Key Insights

### What Worked

✅ **Go Traffic Engine:** 3-5× faster than Python for traffic simulation ticks  
✅ **PostgreSQL Test Harness:** Realistic performance measurements (not mocked)  
✅ **Load Tests:** Validated Go engine at 200 and 1000 device scale  
✅ **IP Pool Scaling:** Fixed IPAM to support 10k+ devices

### What's Next

🚀 **Hybrid Architecture:** Extend Go to cover CRUD operations (optical recompute, batch operations)  
🚀 **Week 2 Critical:** Port optical recompute to Go (800× speedup target)  
🚀 **Week 3 Enabler:** Batch link/device creation in Go (260× speedup target)

### Root Cause (Sandbox Slowness)

❌ **O(N²) Optical Recompute:**

```python
# backend/services/optical_service.py
def recompute_optical_paths_for_affected_onts(link_ids):
    onts = s.exec(select(Device).where(...)).all()  # ALL ONTs!
    for ont in onts:  # 64 iterations
        resolve_optical_path(ont.id)  # Graph traversal, 0.5s each
    # 64 links × 64 ONTs × 0.5s = 2048s = 34 minutes
```

**Solution:** Go optical service with smart affected-ONT detection (Week 2)

---

## 📖 Related Documentation

- **Architecture:** [../architecture/topology-engine.md](../architecture/topology-engine.md) — Go engine design
- **Architecture:** [../architecture/recompute-pipeline.md](../architecture/recompute-pipeline.md) — Optical recompute (needs Go migration)
- **IPAM:** [../architecture/IPAM-Architecture-Future.md](../architecture/IPAM-Architecture-Future.md) — Multi-region IPAM scaling
- **Testing:** [../testing/](../testing/) — Test strategy, fixtures, patterns

---

**Navigation:** [← Back to Docs Home](../README.md) | [→ Operation Stable Foundation Roadmap](../roadmap/OPERATION-STABLE-FOUNDATION.md)
