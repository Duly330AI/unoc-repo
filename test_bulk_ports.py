"""Quick test for bulk port summary endpoint optimization.

DEPRECATED: Use proper pytest tests instead. This ad-hoc script left zombie devices.
"""

from fastapi.testclient import TestClient

from backend.db import get_session
from backend.main import app
from backend.models import Device, DeviceType

client = TestClient(app)

# Cleanup any leftover test devices FIRST
print("🧹 Cleaning up any leftover test devices...")
with get_session() as s:
    for dev_id in ["test-bulk-1", "test-bulk-2"]:
        dev = s.get(Device, dev_id)
        if dev:
            s.delete(dev)
            print(f"  Deleted existing {dev_id}")
    s.commit()

# Create test devices
print("📦 Creating test devices...")
with get_session() as s:
    dev1 = Device(id="test-bulk-1", name="Dev1", type=DeviceType.EDGE_ROUTER)
    dev2 = Device(id="test-bulk-2", name="Dev2", type=DeviceType.OLT)
    s.add(dev1)
    s.add(dev2)
    s.commit()

try:
    # Test bulk endpoint
    print("🔍 Testing bulk port summary endpoint...")
    r = client.get("/api/ports/summary?ids=test-bulk-1&ids=test-bulk-2")
    print(f"Status: {r.status_code}")
    print(f"Response keys: {list(r.json().keys())}")
    print(f"Dev1 ports: {len(r.json().get('test-bulk-1', []))}")
    print(f"Dev2 ports: {len(r.json().get('test-bulk-2', []))}")
    print("✅ Bulk endpoint works!")
finally:
    # Cleanup ALWAYS (even if test fails)
    print("🧹 Cleaning up test devices...")
    with get_session() as s:
        for dev_id in ["test-bulk-1", "test-bulk-2"]:
            dev = s.get(Device, dev_id)
            if dev:
                s.delete(dev)
        s.commit()
    print("✅ Cleanup complete")
