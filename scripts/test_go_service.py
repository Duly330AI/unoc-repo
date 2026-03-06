"""Test Go optical service with manual test data."""

import backend.models  # noqa: F401
from backend.clients.go_services.optical_client import OpticalClient

# Create client
print("Creating OpticalClient...")
client = OpticalClient()
print(f"Client created. Go available: {client._go_available}")

# Test with manual ONT we created
print("\nCalling get_path(ont_id='test-manual-ont-1')...")
result = client.get_path(ont_id="test-manual-ont-1")

print("\n📊 Result:")
print(f"  - backend: {result.get('backend')}")
print(f"  - ont_id: {result.get('ont_id')}")
print(f"  - olt_id: {result.get('olt_id')}")
print(f"  - path_exists: {result.get('path_exists')}")
print(f"  - segments: {len(result.get('segments', []))}")
print(f"  - error: {result.get('error')}")

if result.get("backend") == "go":
    print("\n✅ Go service successfully resolved path!")
else:
    print("\n⚠️ Fell back to Python implementation")
