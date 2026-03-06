# Architecture Documentation Index

**Last Updated:** 2025-10-04  
**Status:** Active | **Version:** 2.0 (Hybrid Python+Go)

---

## 🏗️ **Architecture Overview**

### **Current State (v2.0): Hybrid Python+Go**

```
┌───────────────────────────────────────────────────────────┐
│  BROWSER (Vue 3 + Vite)                                   │
└──────────────────┬────────────────────────────────────────┘
                   │ HTTP/REST
                   ▼
┌───────────────────────────────────────────────────────────┐
│  PYTHON LAYER (FastAPI)                                   │
│  • REST endpoints                                         │
│  • Auth/RBAC                                              │
│  • Request validation                                     │
│  • DB migrations (Alembic)                                │
│  • Business logic                                         │
└────┬──────────────────┬─────────────────────────────────┘
     │ gRPC/HTTP        │ gRPC/HTTP
     ▼                  ▼
┌──────────────────┐  ┌─────────────────────────────────────┐
│  GO SERVICES     │  │  GO SERVICES (Week 2-3)             │
│  • Traffic Engine│  │  • Optical Compute Service          │
│    (DONE! ✅)    │  │  • Status Propagation Service       │
│                  │  │  • Batch Operations Service         │
└──────────────────┘  └─────────────────────────────────────┘
     │                  │
     └──────┬───────────┘
            ▼
   ┌─────────────────┐
   │   PostgreSQL    │
   └─────────────────┘
```

---

## 📚 **Core Architecture Documents**

### 1. **[ARCHITECTURE.md](ARCHITECTURE.md)** — **System Overview (Start Here)**

- High-level architecture
- Component interactions
- Data flow
- Technology stack
- Current: Python FastAPI + Go Traffic Engine

### 2. **[HYBRID-ARCHITECTURE.md](HYBRID-ARCHITECTURE.md)** _(TODO: Week 1)_

- **Hybrid Python+Go Design**
- Service boundaries (Python vs Go)
- Communication patterns (gRPC, HTTP)
- Data serialization (Protobuf)
- Deployment architecture

### 3. **[data-model.md](data-model.md)**

- Database schema (PostgreSQL)
- Entity relationships
- Constraints and indexes
- Migrations (Alembic)

### 4. **[topology-engine.md](topology-engine.md)**

- **Go Traffic Engine** ✅ DONE
- Adjacency graph construction
- Congestion detection
- Traffic aggregation
- Performance: 300ms p50 (5× faster than Python)

### 5. **[recompute-pipeline.md](recompute-pipeline.md)** ⚠️ **MIGRATION PLANNED (Week 2)**

- **Optical path resolution** (currently Python)
- Status propagation (currently Python)
- Dependency resolution
- **Target:** Migrate to Go for 800× speedup

### 6. **[caching-and-snapshots.md](caching-and-snapshots.md)**

- Snapshot architecture
- Caching strategies
- Performance optimizations

### 7. **[events-and-ws.md](events-and-ws.md)**

- WebSocket protocol
- Event publishing (Python)
- Real-time UI updates
- Correlation IDs

### 8. **[status_service.md](status_service.md)** ⚠️ **MIGRATION PLANNED (Week 2)**

- Device/Link status management
- Status propagation rules
- Gating logic (optical thresholds)
- **Target:** Migrate to Go for parallel processing

---

## 🎯 **Specialized Architecture Documents**

### IPAM (IP Address Management)

- **[IPAM-Architecture-Future.md](IPAM-Architecture-Future.md)**
  - Multi-region support planning
  - Prefix allocation strategies
  - Address audit logging

### Container Rendering

- **[adr/ADR-008-containers-link-rendering.md](adr/ADR-008-containers-link-rendering.md)**
  - Container-based topology visualization
  - Link rendering strategies
  - Performance considerations

### Design Guides

- **[design-guides/fully_integrate_core_site_container.md](design-guides/fully_integrate_core_site_container.md)**

  - Core/Site/Container integration
  - Hierarchical topology management

- **[design-guides/TASK-800-container-nodes-plan.md](design-guides/TASK-800-container-nodes-plan.md)**
  - Container nodes feature planning
  - Implementation roadmap

---

## 🚀 **Migration Roadmap**

### **Week 1 (Oct 7-11): Foundation**

- Documentation cleanup
- Go service infrastructure setup
- Protobuf service contracts
- Python client wrappers

### **Week 2 (Oct 14-18): Optical Compute Migration**

- Port `resolve_optical_path()` to Go
- Implement smart affected-ONT detection
- Add parallel processing (goroutines)
- **Target:** 800× speedup (20-40s → 50-100ms)

### **Week 3 (Oct 21-25): Batch Operations**

- Bulk link/device creation in Go
- Single recompute at end (not per-item)
- FastAPI wrapper endpoints
- **Target:** 262× speedup (64 links: 37min → 8s)

---

## 🔗 **Related Documentation**

- **[../roadmap/OPERATION-STABLE-FOUNDATION.md](../roadmap/OPERATION-STABLE-FOUNDATION.md)** — 3-week hybrid migration plan
- **[../performance/INDEX.md](../performance/INDEX.md)** — Performance benchmarks and targets
- **[../operations/prometheus-grafana-setup.md](../operations/prometheus-grafana-setup.md)** — **Monitoring (AKTIV)** ✅
- **[../setup/local-dev.md](../setup/local-dev.md)** — Development environment setup

---

## 📝 **Decision Records (ADRs)**

Architecture Decision Records are stored in `adr/`:

- **[ADR-008-containers-link-rendering.md](adr/ADR-008-containers-link-rendering.md)** — Container rendering strategy

_(More ADRs to be added during hybrid migration)_

---

**Note:** This architecture is actively evolving. The hybrid Python+Go approach was decided on 2025-10-04 to address performance bottlenecks in Sandbox CRUD operations while maintaining Python's strengths in REST API orchestration.
