# Pytest Markers & Test Execution Guide

## Test Categories

We use pytest markers to separate fast unit tests from slow integration tests:

### 1. **Unit Tests** (Default)

- **What**: Fast, in-memory SQLite tests
- **Duration**: ~20 seconds for 280+ tests
- **Requirements**: None (Python only)
- **Database**: In-memory SQLite (isolated, ephemeral)
- **Command**: `pytest` (uses defaults from pytest.ini)

### 2. **Integration Tests** (`@pytest.mark.integration`)

- **What**: Tests requiring Go services and PostgreSQL
- **Duration**: Variable (depends on Go service availability)
- **Requirements**:
  - Go services running (Traffic Engine :8080, Optical :50051, Status :50053, Batch :50052)
  - PostgreSQL running (:5432)
- **Database**: PostgreSQL (shared state, persistent)
- **Command**: `pytest -m integration`

### 3. **Performance Tests** (`@pytest.mark.perf`)

- **What**: Large-scale load tests (200-1000 devices)
- **Duration**: Minutes to hours
- **Requirements**: PostgreSQL, Go services
- **Database**: PostgreSQL (requires manual reset between runs)
- **Command**: `pytest -m perf backend/tests/perf/`

---

## Quick Reference

### Run fast unit tests only (default)

```bash
pytest
# OR explicitly:
pytest -m "not integration and not perf" --ignore=backend/tests/perf
```

**Result**: ~280 tests in 20s, in-memory, no external dependencies

### Run integration tests (Go services required)

```bash
pytest -m integration
```

**Prerequisites**:

- Start Go services: `docker-compose up -d` or run manually
- PostgreSQL must be running

### Run performance tests (load/stress testing)

```bash
pytest -m perf backend/tests/perf/
```

**Prerequisites**:

- PostgreSQL running
- Database reset: `python scripts/reset_dev_db.py --force --catalog-only`

### Run ALL tests (unit + integration, skip perf)

```bash
pytest -m "not perf"
```

**Prerequisites**: Go services + PostgreSQL must be running

### Run full suite (everything)

```bash
pytest -m "" --ignore-glob=""
```

⚠️ **WARNING**: Runs 300+ tests including perf suite (can take hours)

---

## File Naming Conventions

- `test_*.py` - Unit tests (default, in-memory)
- `test_*_integration.py` - Integration tests (requires Go services + PostgreSQL)
- `perf/test_*.py` - Performance tests (requires PostgreSQL, large datasets)

---

## Test Isolation

### Why We Use Markers

**Problem**: Integration tests are slow and depend on external services (Go + PostgreSQL).  
**Solution**: Mark them with `@pytest.mark.integration` so developers can run fast unit tests by default.

### Automatic Exclusion

`pytest.ini` is configured to **automatically skip** integration and perf tests:

```ini
[pytest]
addopts = -m "not perf and not integration" --ignore=backend/tests/perf
```

This ensures:

1. ✅ `pytest` runs only unit tests (fast, no dependencies)
2. ✅ `--ignore=backend/tests/perf` prevents perf/conftest.py from activating PostgreSQL
3. ✅ Developers get instant feedback (~20s test run)

### Manual Inclusion

To **explicitly run** integration or perf tests, override the markers:

```bash
# Run integration tests only
pytest -m integration

# Run both unit and integration tests
pytest -m "not perf"

# Run specific integration test file
pytest backend/tests/test_traffic_go_congestion.py
```

---

## Troubleshooting

### Tests hang or run very slow

**Cause**: PostgreSQL mode is activated (perf/conftest.py hook)  
**Solution**: Use `--ignore=backend/tests/perf` or run `pytest` without args (uses pytest.ini defaults)

### "No tests collected"

**Cause**: All tests are marked as integration/perf and excluded by default  
**Solution**: Run `pytest -m integration` or `pytest -m ""` to include all markers

### Integration tests fail with "connection refused"

**Cause**: Go services not running  
**Solution**: Start services with `docker-compose up -d` or run manually

### Database errors in unit tests

**Cause**: Missing `init_db()` call in test setup  
**Solution**: Add `init_db()` at start of test function or use pytest fixtures

---

## CI/CD Integration

### GitHub Actions / GitLab CI

```yaml
# Fast unit tests (always run)
- name: Unit Tests
  run: pytest -q

# Integration tests (optional, requires services)
- name: Integration Tests
  run: pytest -m integration
  services:
    postgres: ...
    # Start Go services via docker-compose
```

### Pre-commit Hooks

```bash
# .git/hooks/pre-commit
pytest -x  # Stop at first failure
```

---

## Coverage Targets

- **Unit tests**: Aim for 90%+ coverage of core logic
- **Integration tests**: Focus on end-to-end flows and Go service communication
- **Performance tests**: Validate scalability targets (e.g., 200 devices in <500ms/tick)

---

## Marking New Tests

### Unit Test (default)

```python
def test_my_feature():
    """Fast unit test using in-memory database."""
    init_db()
    # ... test code
```

### Integration Test

```python
import pytest

pytestmark = pytest.mark.integration  # Mark entire module

def test_go_service_integration():
    """Requires Traffic Engine Go service on port 8080."""
    # ... test code using Go service
```

### Performance Test

```python
import pytest

pytestmark = [pytest.mark.perf, pytest.mark.integration]

def test_large_scale_load():
    """Load test with 1000 devices (requires PostgreSQL)."""
    # ... perf test code
```

---

## Benefits

✅ **Fast feedback loop**: Developers run 280 tests in 20s  
✅ **Clear separation**: Unit tests (fast, isolated) vs integration tests (slow, requires services)  
✅ **CI-friendly**: Can run unit tests on every commit, integration tests on merge  
✅ **Deterministic**: In-memory tests are isolated and repeatable  
✅ **Scalable**: Perf tests can run nightly without slowing down development

---

## Version History

- **2025-10-08**: Added `@pytest.mark.integration` for Go service tests
- **2025-10-08**: Fixed perf/conftest.py PostgreSQL override issue with `--ignore`
- **2025-10-08**: Updated pytest.ini to skip integration tests by default
