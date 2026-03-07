# Priorities (near-term)

1. Stabilize and document test infra

- Ensure shared in-memory SQLite is default in tests; remove dual-backend remnants
- Add quick-start in docs/testing

2. Performance Phase 1 (completed) and verify

- Request-level SQL metrics (perf.log) in CI smoke
- Backfill a short perf harness that loads demo topology and exercises endpoints

3. Background recomputes hardening

- Coalesce recompute tasks per device/link
- Add simple work queue abstraction with visibility into pending work

4. Snapshot caching & ETags

- Implement snapshot caching keyed by topology_version
- Add If-None-Match/ETag handling to snapshot endpoints

5. Docs overhaul completion

- Remove or archive legacy docs in docs root
- Fill operations, testing, and playbooks with concrete runbooks

6. Scale path groundwork (target 1k–10k)

- Indexes for hot queries; stored computed columns if needed
- Incremental recompute and dependency tracking persisted

Acceptance criteria per item are listed inline in respective docs sections.
