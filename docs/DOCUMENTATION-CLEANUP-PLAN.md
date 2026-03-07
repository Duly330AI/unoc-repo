# Documentation Cleanup Plan (Phase 0.1)

**Date:** 2025-10-04
**Goal:** Clean, structured documentation base for Go Hybrid migration
**Estimated Time:** 4-6 hours

---

## 1. Prometheus/Grafana Rollback (Rolled Back in HGO-010)

### Actions:

- [x] Move `docs/operations/observability/prometheus_grafana.md` → `docs/archive/2025-10-04-prometheus/`
- [ ] Update `docs/README.md` - Remove prometheus_grafana reference
- [ ] Update `docs/performance/EXECUTIVE_SUMMARY.md` - Remove HGO-012 (Prometheus/Grafana)
- [ ] Update `docs/topology/example_topology.md` - Remove Grafana reference
- [ ] Update `docs/architecture/IPAM-Architecture-Future.md` - Remove Prometheus TODO

**Rationale:** Prometheus/Grafana integration was rolled back. Move to archive to preserve history, remove from active docs.

---

## 2. Performance Documentation Consolidation

### Current State (Fragmented):

```
docs/performance/
  - EXECUTIVE_SUMMARY.md       (outdated - mentions HGO-012 Prometheus)
  - HGO-010-LoadTest-Results.md (complete)
  - HGO-011-LoadTest-Results.md (complete)
  - HGO-010-STATUS.md          (outdated - HGO-010 is complete)
  - HYBRID_GO_ROADMAP.md       (outdated - superseded by OPERATION-STABLE-FOUNDATION)
  - OPTIMIZATION_ROADMAP.md    (outdated - superseded by OPERATION-STABLE-FOUNDATION)
  - PERFORMANCE_ANALYSIS_2025-10-03.md (snapshot - useful but not roadmap)
  - harness.md                 (current - test harness guide)
  - metrics.md                 (current - Go engine metrics)
  - profiling.md               (current - profiling guide)
  - README.md                  (index - needs update)
```

### Actions:

- [ ] **Archive outdated roadmaps:**
  - Move `HYBRID_GO_ROADMAP.md` → `archive/2025-10-04-old-roadmaps/`
  - Move `OPTIMIZATION_ROADMAP.md` → `archive/2025-10-04-old-roadmaps/`
  - Move `HGO-010-STATUS.md` → `archive/2025-10-04-old-roadmaps/` (HGO-010 is complete)
- [ ] **Update EXECUTIVE_SUMMARY.md:**
  - Remove HGO-012 (Prometheus/Grafana) - rolled back
  - Update status: HGO-010 ✅ COMPLETE, HGO-011 ✅ COMPLETE
  - Add note: "Go Hybrid migration underway (see docs/roadmap/OPERATION-STABLE-FOUNDATION.md)"
- [ ] **Create performance/INDEX.md:**
  - Clear roadmap to current performance state
  - Links to: HGO-010, HGO-011, harness.md, metrics.md, profiling.md
  - Link to active roadmap: `../roadmap/OPERATION-STABLE-FOUNDATION.md`

**Rationale:** Consolidate fragmented performance docs, remove outdated roadmaps superseded by OPERATION-STABLE-FOUNDATION.

---

## 3. Architecture Documentation Updates

### Current State:

```
docs/architecture/
  - overview.md                (needs Go Hybrid section)
  - topology-engine.md         (current - Go engine architecture)
  - recompute-pipeline.md      (needs update - optical O(N²) documented)
  - status_service.md          (current)
  - events-and-ws.md           (current)
  - data-model.md              (current)
  - caching-and-snapshots.md   (current)
  - IPAM-Architecture-Future.md (current - remove Prometheus TODO)
```

### Actions:

- [ ] **Update architecture/overview.md:**
  - Add "Hybrid Python+Go Architecture" section
  - Document current state:
    - Python: FastAPI, SQLAlchemy, business logic
    - Go: Traffic Engine (DONE), Optical/Batch/Status (Week 2-3)
  - Add diagram showing Python ↔ Go service layer
- [ ] **Update architecture/recompute-pipeline.md:**
  - Document O(N²) optical recompute bug (root cause of crisis)
  - Add "Future: Go Optical Service" section (Week 2 plan)
  - Add "Migration Strategy" section
- [ ] **Create architecture/HYBRID-ARCHITECTURE.md (NEW):**
  - Detailed design for hybrid Python+Go architecture
  - gRPC/HTTP communication patterns
  - Service boundaries (Python: REST, Go: Compute)
  - Migration principles (incremental, low-risk)
- [ ] **Update architecture/IPAM-Architecture-Future.md:**
  - Remove Prometheus TODO (rolled back)

**Rationale:** Architecture docs must reflect hybrid approach before we start building Go services.

---

## 4. Guides & Playbooks Cleanup

### Current State:

```
docs/guides/
  - UI-Testing-Guide.md (current - for HGO-012)
  - gpon-odf-acceptance-criteria.md (current)
  - l3-auto-provisioning.md (current)
  - archive/ipam_gpon_ethernet_dg.md (duplicate)
  - network-design/ipam_gpon_ethernet_dg.md (active)
  - network-design/pop_coreSide.md (active)
  - ui/bulk-create-modal.md (active)

docs/playbooks/
  - 14_commands_playbook.md (symlink to llm/14_commands_playbook.md)
```

### Actions:

- [ ] **Remove duplicate:** `docs/guides/archive/ipam_gpon_ethernet_dg.md` (exists in network-design/)
- [ ] **Update UI-Testing-Guide.md:**
  - Add note: "DEFERRED until Go Hybrid complete"
  - Add reference to OPERATION-STABLE-FOUNDATION.md

**Rationale:** Remove duplicates, update guides to reflect current priorities.

---

## 5. LLM Context Consolidation

### Current State (Fragmented):

```
docs/llm/
  - ARCHITECTURE.md (outdated - no Go Hybrid)
  - ROADMAP.md (outdated - superseded by OPERATION-STABLE-FOUNDATION)
  - BACKLOG.md (outdated - task system deprecated)
  - COMPLETED_TASKS.md (outdated - task system deprecated)
  - TASK.md (outdated - task system deprecated)
  - TASK-004.recompute_dirty.plan.md (outdated)
  - task_001-099.md to task_900-999.md (outdated - legacy task system)
  - 01_overview_and_domain_model.md to 14_commands_playbook.md (current - good!)
```

### Actions:

- [ ] **Move legacy task files to archive:**
  - Move `BACKLOG.md`, `COMPLETED_TASKS.md`, `TASK.md`, `TASK-004.*.md` → `archive/2025-10-04-legacy-task-system/`
  - Move `task_*.md` files → `archive/2025-10-04-legacy-task-system/`
- [ ] **Update ARCHITECTURE.md:**
  - Add "Hybrid Python+Go Architecture (2025-10-04)" section
  - Document current state vs planned state
  - Link to `../roadmap/OPERATION-STABLE-FOUNDATION.md`
- [ ] **Update ROADMAP.md:**
  - Deprecation notice: "Superseded by docs/roadmap/OPERATION-STABLE-FOUNDATION.md"
  - Historical note: "See archive/2025-10-04-old-roadmaps/ for previous plans"
- [ ] **Keep module docs (01-14):** These are excellent, up-to-date summaries!

**Rationale:** LLM context should focus on hybrid architecture, not legacy task tracking. Module docs (01-14) are valuable and current.

---

## 6. Roadmap Folder Structure

### Current State:

```
docs/roadmap/
  - OPERATION-STABLE-FOUNDATION.md (NEW - active 3-week plan)
```

### Actions:

- [ ] **Create roadmap/README.md:**
  - Index of all roadmaps (active + archived)
  - Clear pointer to OPERATION-STABLE-FOUNDATION.md as active roadmap
- [ ] **Keep OPERATION-STABLE-FOUNDATION.md as-is** (created yesterday, comprehensive)

**Rationale:** Central roadmap folder with clear active/archived distinction.

---

## 7. Operations & Setup Documentation

### Current State:

```
docs/operations/
  - runbook.md (current)
  - bootstrap/bootstrap_anchors.md (current)
  - observability/prometheus_grafana.md (NEEDS ARCHIVE)
  - planning/New Roadmap.md (outdated?)
  - planning/Priorities.md (outdated?)
  - process/Definition-of-Done.md (current)

docs/setup/
  - local-dev.md (current)
  - backend.md (current)
  - frontend.md (current)
  - database.md (current)
  - env.md (current)
```

### Actions:

- [ ] **Move prometheus_grafana.md** (already planned in §1)
- [ ] **Review operations/planning/:**
  - Check if "New Roadmap.md" is superseded by OPERATION-STABLE-FOUNDATION
  - Archive if outdated
  - Check if "Priorities.md" is current
- [ ] **Setup docs:** Review for Go Hybrid updates (e.g., Go engine setup in local-dev.md)

**Rationale:** Operations docs should reflect current architecture (no Prometheus, add Go setup).

---

## 8. Root-Level README Updates

### Actions:

- [ ] **Update docs/README.md:**
  - Add "Active Roadmap" section → `roadmap/OPERATION-STABLE-FOUNDATION.md`
  - Remove prometheus_grafana reference
  - Add "Hybrid Architecture" section → `architecture/HYBRID-ARCHITECTURE.md` (when created)
  - Update performance docs index → `performance/INDEX.md` (when created)

**Rationale:** Root README is the entry point - must reflect current state.

---

## Summary of File Moves

### Archive Targets:

```
docs/archive/2025-10-04-prometheus/
  - prometheus_grafana.md (from operations/observability/)

docs/archive/2025-10-04-old-roadmaps/
  - HYBRID_GO_ROADMAP.md (from performance/)
  - OPTIMIZATION_ROADMAP.md (from performance/)
  - HGO-010-STATUS.md (from performance/)

docs/archive/2025-10-04-legacy-task-system/
  - BACKLOG.md (from llm/)
  - COMPLETED_TASKS.md (from llm/)
  - TASK.md (from llm/)
  - TASK-004.recompute_dirty.plan.md (from llm/)
  - task_*.md (from llm/, all 9 files)
```

### New Files to Create:

```
docs/performance/INDEX.md
docs/architecture/HYBRID-ARCHITECTURE.md
docs/roadmap/README.md
```

### Files to Update:

```
docs/README.md
docs/performance/EXECUTIVE_SUMMARY.md
docs/architecture/overview.md
docs/architecture/recompute-pipeline.md
docs/architecture/IPAM-Architecture-Future.md
docs/guides/UI-Testing-Guide.md
docs/llm/ARCHITECTURE.md
docs/llm/ROADMAP.md
docs/topology/example_topology.md
```

---

## Success Criteria

- [x] No Prometheus/Grafana references in active docs (only in archive)
- [ ] Single source of truth for roadmap: `docs/roadmap/OPERATION-STABLE-FOUNDATION.md`
- [ ] Architecture docs reflect Hybrid Python+Go approach
- [ ] Performance docs consolidated (no duplicate/outdated roadmaps)
- [ ] LLM context clean (no legacy task system noise)
- [ ] Clear index/navigation (README.md, INDEX.md files)

---

## Next Steps (After Cleanup)

1. **Phase 0.2:** Finalize Master Plan (review OPERATION-STABLE-FOUNDATION.md)
2. **Phase 0.3:** Update Prompt Files (INSTRUCTIONS.md, LLMTOOL.toolsets.jsonc, README.MD.prompt.md)
3. **Week 1, Day 1:** Begin Go Hybrid migration (gRPC scaffolding)
