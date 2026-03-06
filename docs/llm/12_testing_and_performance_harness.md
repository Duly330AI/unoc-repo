

## 12. Testing and Performance Harness

Authoritative notes on deterministic tests, async recompute coalescing, SQL profiling, and coverage.

### 12.1 Test database and determinism

- The test suite runs exclusively against a fast, isolated, shared in-memory SQLite database to maximize speed and prevent state pollution between tests. This is configured in `backend/tests/conftest.py` (engine URL with shared cache; scoped sessions; cleanup fixtures).
- The main development environment, in contrast, targets PostgreSQL (via Docker) for a realistic, production-like experience. Use SQLite only for tests.
- **Functional parity**: While PostgreSQL-specific features (e.g., row-level locks, serializable isolation) exist in production, the current test suite remains functionally complete. No critical gaps exist between SQLite and PostgreSQL for existing workflows. Future PG-specific behavior would require dedicated integration tests.
- Async recompute is coalesced per tick to avoid flapping and race conditions; background tasks honor a single in-flight recompute with queuing.
- For DB-integrated sequences (provision, link CRUD), recompute triggers are deferred out of the transaction for stability.

### 12.2 SQL profiling

- Lightweight SQL profiling hooks capture SELECT/INSERT/UPDATE stats per request during development when `UNOC_DEV_FEATURES` is set.
- Use these stats to spot N+1 patterns and validate indexing assumptions.

### 12.3 Coverage workflow

- Typical local gates (Windows/PowerShell):
  - Lint: `ruff check .`
  - Tests: `pytest -q`
  - Coverage: `python -m coverage run -m pytest -q; coverage report -m; coverage html`
- VS Code tasks are provided for quick runs (see Tasks: backend: tests, coverage: report, coverage: html).

### 12.4 Recompute hooks

- Provisioning/Link CRUD fire recompute hooks for optical paths and status; TEv2 emits periodic ticks.
- Coalescing ensures only one recompute per affected area per tick.
- **Async testing**: Tests triggering recomputes must wait for background tasks to complete before assertions. Use helper utilities (e.g., polling for stable topology versions) to synchronize with async workflows.

### 12.5 Fixtures and seeding

- Seed service can populate IPAM defaults and demo topologies in dev (guarded by `UNOC_DEV_FEATURES`).
- Tests rely on explicit fixture names and avoid time-based sleeps; prefer explicit tick advancement where applicable.

### 12.6 Performance notes

- Keep ticks and recomputes lightweight; avoid large graph rebuilds when small deltas occur.
- Use VRF- and Prefix-scoped uniqueness to keep IPAM operations O(1) lookups.

### 12.7 Performance Harness (`pytest -m perf`)

- **Purpose**: Automated load and performance tests for large topologies (TASK-912).
- **Location**: See `backend/tests/perf/test_large_scale.py` and companion factories.
- **Topology factories**:
  - Generate scalable device/link graphs (POP → ODF → OLT/ONT trees and core routers) with parameterized sizes.
  - Realistic structural patterns: Mimic GPON split ratios (1:32, 1:64), varied link lengths, and heterogeneous device distributions.
- **Bulk mode**:
  - Suppresses per-entity recomputes, performing a single consolidated recompute post-bulk mutations.
  - **Recompute measurement**: Track timestamp deltas before/after `PATHFINDING_STORE.bump_version()` and wait for coalescer idle to capture bulk recompute duration.
- **Measurement**:
  - Integrate `pyinstrument` (and optionally `py-spy`) to record profiles of heavy workflows (e.g., provision, link CRUD, snapshot).
  - **Profiling automation**: Local/adhoc CI artifact generation; manual comparison across versions. Future roadmap includes automated delta analysis.
- **Invocation**: Mark tests with `@pytest.mark.perf` and run selectively with `pytest -m perf -q`. Combine with environment flags (e.g., `UNOC_DEV_FEATURES`) for detailed logging.

---

**Key Additions**:
- Clarified functional parity between SQLite/PostgreSQL in 12.1.
- Expanded 12.4 with async testing guidance.
- Enhanced 12.7 with bulk recompute measurement and realistic topology patterns.
- Added notes on profiling automation and future roadmap in 12.7.