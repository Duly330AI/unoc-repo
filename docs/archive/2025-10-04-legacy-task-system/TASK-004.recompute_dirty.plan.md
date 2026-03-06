# TASK-004 – status_service.recompute_dirty (Toposort/BFS)

Status: Proposed → This plan describes scope, contract, algorithm, metrics, tests, and affected files. Implementation will follow in small, atomic diffs.

## Contract (inputs/outputs)

- Inputs
  - session: DB session/UnitOfWork for reads and writes
  - dirty: DirtySet { region_id: int, devices: list[int], links: list[int] } (stable order)
  - flags: config toggles (e.g., enable_incremental, full_recompute_fallback)
  - deps: access to GraphIndex and dependency helpers (neighbors, reachability cache)
- Outputs
  - changes: list of (entity_type, id, old_status, new_status) for affected items within region
  - stats: counters for recomputed devices/links and total visited
  - side effects: persist updated statuses; emit events as existing status_service does

Success criteria

- Deterministic: identical inputs → identical order and outputs
- Locality: only nodes reachable from dirty roots via known status dependencies are recomputed
- No global scans within a round; only neighborhood traversals
- Backwards-compatibility: when incremental is disabled, results equal legacy full recompute

## Algorithm overview

- Build a traversal frontier seeded with dirty.devices and dirty.links (stable ordered unique lists)
- Use a directed dependency model for status propagation:
  - Link status depends on its endpoints’ administrative/operational readiness
  - Device status depends on its interfaces/links and upstream L3/anchor reachability
- Traverse via BFS in layers; within each layer, process items in a deterministically sorted order (id ascending)
- In-round memoization map: memo[EntityKey] = computed_status_result to avoid duplicate recomputes per round
- Use GraphIndex.neighbors_device(id) / neighbors_link(id) to expand only local neighborhoods
- For each node in order:
  - Compute required sub-dependencies; consult memo first; if missing, compute recursively within the round
  - Evaluate status using existing status_service helpers (evaluate_device_status, evaluate_link_status, is_link_passable)
  - If status changes, enqueue immediate dependents to next frontier layer
- Stop when the frontier is empty

Pseudocode

```
recompute_dirty(session, dirty, graph, cfg):
    if not cfg.enable_incremental:
        return recompute_full(session, dirty.region_id)

    memo = {}
    changes = []
    frontier = stable_unique(dirty.devices, dirty.links)
    record_histogram("dirty_set_size", len(frontier))

    while frontier:
        next_frontier = []
        for item in stable_sort(frontier):
            res = compute_status(item, memo, session, graph)
            if res.changed:
                changes.append(res.change)
                for dep in dependents_of(item, graph):
                    next_frontier.append(dep)
        frontier = stable_unique(next_frontier)

    persist_changes(session, changes)
    emit_events(changes)
    return changes
```

Notes

- compute_status uses existing status_service evaluation functions; no behavioral changes intended
- dependents_of uses GraphIndex to map device↔links and link↔devices edges
- has_upstream_l3_or_anchor: continue to use topology-versioned cache; honor router-bypass rule

## Data structures

- EntityKey = (kind: "device"|"link", id: int)
- Memo per round only; cleared between rounds; no cross-round cache
- Stable ordering: always sort by (kind_order, id) where kind_order: device=0, link=1

## Metrics

- Histogram: dirty_set_size_histogram (bucketed: 1, 2, 4, 8, 16, 32, 64, 128, 256+)
- Counters: recompute_entities_total{kind}, status_changes_total{kind}
- Timer: recompute_round_duration_seconds (optional)

## Edge cases and guards

- Cycles: BFS with memo prevents infinite loops; only enqueue dependents when a status actually changes
- Large dirty sets: traversal remains O(|affected|); worker-level budgets handled outside (M2)
- Missing region_id: default to GraphIndex inference; assert consistent region across seeds
- Flags: full_recompute_fallback toggles legacy path for comparison and rollback

## Backwards compatibility

- Feature flag UNOC_INCREMENTAL_RECOMPUTE (default on in sandbox). If disabled, call existing full recompute and ensure outputs are identical to incremental on the same snapshot (tested).

## Affected files (initial wave)

- backend/services/status_service.py
  - Add recompute_dirty(session, dirty, graph, cfg)
  - Wire metrics emission (via observability module)
- backend/tests/test_recompute_dirty.py
  - Minimal tests for locality, determinism, and compatibility (initially skipped until function exists)

## Out of scope (this task)

- Worker wiring and read-model updates (handled in TASK-008/TASK-015)
- Performance P2 caches in traffic generate phase

## Acceptance tests (to be added incrementally)

- Local recompute only: change on a link recomputes that link and its two endpoint devices, not unrelated devices
- Deterministic order: recompute order for a given dirty set is stable across runs
- Full-recompute parity: toggling flag produces identical final statuses

---

Implementation will proceed with atomic diffs: (1) add function skeleton + metrics stubs, (2) implement BFS + memo, (3) enable flags and tests.
