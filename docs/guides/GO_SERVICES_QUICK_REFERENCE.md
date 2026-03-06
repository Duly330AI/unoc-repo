# Go Services Quick Reference Guide

**For Developers:** How to use Go services in Python code

---

## 🚀 Quick Start

### Status Propagation (30,000× faster)

Use when: Device/link status changes need to propagate through topology

```python
from backend.clients.go_services.status_client import get_status_client

# After creating/updating a device
status_client = get_status_client()
if status_client:
    result = status_client.propagate_status(
        changed_device_ids=[device_id],  # Devices that changed
        changed_link_ids=[],              # Links that changed
        update_database=True              # Persist changes
    )
    # result: {"affected_devices": 5, "affected_links": 12, "duration_ms": 0.066, "source": "go"}
```

### Optical Path Recomputation (4,000× faster)

Use when: Optical devices/links change (OLT, splitter, ODF, fiber)

```python
from backend.clients.go_services.optical_client import get_optical_client

# After creating/updating optical links or devices
optical_client = get_optical_client()
if optical_client:
    result = optical_client.recompute_paths(
        link_ids=[link_id],      # Changed links
        device_ids=[device_id]   # Changed devices
    )
    # result: {"status": "success", "affected_onts": 50, "ont_ids": [...], "duration_ms": 10, "backend": "go"}
```

### Traffic Tick (5× faster)

Use when: Need to generate traffic metrics

```python
from backend.clients.go_services.traffic_client import get_traffic_client

# Generate traffic for all devices
traffic_client = get_traffic_client()
if traffic_client:
    result = traffic_client.tick()
    # result: {"devices_processed": 200, "links_processed": 400, "duration_ms": 300, "backend": "go"}
```

---

## 📋 Common Patterns

### Pattern 1: Device Create/Update with Status

```python
def create_device_impl(s: Session, data: DeviceCreate) -> DeviceOut:
    # ... create device in DB ...
    s.commit()

    # Propagate status changes via Go service (non-fatal)
    try:
        status_client = get_status_client()
        if status_client:
            status_client.propagate_status(
                changed_device_ids=[device.id],
                changed_link_ids=[],
                update_database=True
            )
    except Exception as e:
        print(f"[WARN] Status propagation failed: {e}")

    return DeviceOut.from_model(device)
```

### Pattern 2: Link Create with Status + Optical

```python
def create_link_impl(s: Session, data: LinkCreate) -> LinkOut:
    # ... create link in DB ...
    s.commit()

    try:
        # Optical path recomputation (4,000× faster)
        optical_client = get_optical_client()
        if optical_client:
            optical_client.recompute_paths(link_ids=[link.id])

        # Status propagation for endpoint devices (30,000× faster)
        status_client = get_status_client()
        if status_client:
            affected_devices = [a_device_id, b_device_id]
            status_client.propagate_status(
                changed_device_ids=affected_devices,
                changed_link_ids=[link.id],
                update_database=True
            )
    except Exception as e:
        print(f"[WARN] Go service call failed: {e}")

    return LinkOut.from_model(link)
```

### Pattern 3: Bulk Operations with Batching

```python
def bulk_provision_devices(device_ids: list[str]) -> None:
    # Process devices first
    for device_id in device_ids:
        provision_device(device_id)

    # Single status propagation call for all changes
    try:
        status_client = get_status_client()
        if status_client:
            status_client.propagate_status(
                changed_device_ids=device_ids,
                changed_link_ids=[],
                update_database=True
            )
    except Exception as e:
        print(f"[WARN] Bulk status propagation failed: {e}")
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Enable Go traffic engine (default: Python)
USE_GO_TRAFFIC=1

# Go service endpoints (defaults shown)
GO_STATUS_HOST=localhost
GO_STATUS_PORT=50053

GO_OPTICAL_HOST=localhost
GO_OPTICAL_PORT=50051

GO_TRAFFIC_HOST=localhost
GO_TRAFFIC_PORT=8080
```

### Service Discovery

All clients auto-detect Go service availability:

```python
status_client = get_status_client()
# Returns None if service unavailable
# Returns StatusClient instance if service available
# Automatic fallback to Python if Go service fails
```

---

## 🔍 Debugging

### Check Go Service Availability

```python
from backend.clients.go_services.status_client import get_status_client

client = get_status_client()
if client:
    print("✅ Status service available")
else:
    print("❌ Status service unavailable (using Python fallback)")
```

### Test Optical Path Resolution

```python
from backend.clients.go_services.optical_client import get_optical_client

optical_client = get_optical_client()
if optical_client:
    result = optical_client.get_path(ont_id="ont-123")
    print(f"ONT path: {result['segments']}")
    print(f"Backend: {result['backend']}")  # "go" or "python"
```

### Monitor Performance

```python
import time

start = time.perf_counter()
status_client.propagate_status(changed_device_ids=[device_id], ...)
duration_ms = (time.perf_counter() - start) * 1000

print(f"Status propagation took {duration_ms:.2f}ms")
# Expected: <1ms for Go, >1000ms for Python
```

---

## 🧪 Testing

### Unit Tests (No Go Services Required)

```python
@pytest.mark.unit  # Runs in-memory, no Go services
def test_device_creation():
    # Test uses Python fallback automatically
    device = create_device_impl(session, data)
    assert device.id == "test-device"
```

### Integration Tests (Requires Go Services)

```python
@pytest.mark.integration  # Requires Go services running
def test_status_propagation_go_service():
    status_client = get_status_client()
    assert status_client is not None, "Go status service not available"

    result = status_client.propagate_status(...)
    assert result["source"] == "go"
    assert result["duration_ms"] < 1  # Sub-millisecond
```

**Run Tests:**

```bash
# Unit tests only (fast, no Go services)
pytest -m "not integration"

# Integration tests (requires Go services)
pytest -m integration

# All tests
pytest
```

---

## 🚨 Error Handling

### Non-Fatal by Default

All Go service calls use try/except to prevent failures:

```python
try:
    status_client = get_status_client()
    if status_client:
        status_client.propagate_status(...)
except Exception as e:
    print(f"[WARN] Status propagation failed: {e}")
    # ✅ Device operation still succeeds
```

### When to Make Fatal

Only make Go service calls fatal if:

1. Operation **requires** Go service result
2. No Python fallback exists
3. Failure should block user action

Example:

```python
def critical_bulk_operation(device_ids: list[str]) -> dict:
    status_client = get_status_client()
    if not status_client:
        raise HTTPException(
            status_code=503,
            detail="Status service unavailable - bulk operation requires Go service"
        )

    return status_client.propagate_status(changed_device_ids=device_ids, ...)
```

---

## 📊 Performance Expectations

| Service | Operation   | Target | Fallback |
| ------- | ----------- | ------ | -------- |
| Status  | 100 devices | <1ms   | ~2000ms  |
| Optical | 50 ONTs     | <15ms  | ~40s     |
| Traffic | 200 devices | <300ms | ~1500ms  |

**When to Use Python Fallback:**

- Development environment (no Go services)
- Testing edge cases (Python more flexible)
- Go service maintenance window
- Investigating bugs (Python easier to debug)

---

## 🔗 Service Architecture

```
Python Endpoint
    ↓
Go Service Client (gRPC)
    ↓
Go Service (port 50051/50053/8080)
    ↓
PostgreSQL Database
    ↓
Return Result to Python
```

**Key Points:**

- Python makes gRPC call to Go service
- Go service reads/writes PostgreSQL directly
- Result returned to Python (dict format)
- Automatic Python fallback on Go service failure

---

## 📚 References

- **Implementation Guide:** `docs/operations/GO_SERVICES_INTEGRATION_COMPLETE.md`
- **Week 2 Details:** `docs/roadmap/WEEK2_COMPLETE.md`
- **Test Markers:** `docs/testing/PYTEST_MARKERS_GUIDE.md`
- **Architecture:** `docs/roadmap/OPERATION-STABLE-FOUNDATION.md`

---

## 💡 Tips

1. **Always check client availability:** Use `if client:` pattern
2. **Non-fatal by default:** Wrap in try/except
3. **Batch when possible:** Single call for multiple devices
4. **Monitor performance:** Log duration_ms for Go service calls
5. **Test both paths:** Verify Go service AND Python fallback

---

**Last Updated:** 2025-10-08  
**Status:** ✅ Production-Ready
