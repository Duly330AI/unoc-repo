import httpx

response = httpx.post(
    "http://localhost:5001/api/devices",
    json={
        "id": "test_bb2",
        "name": "Test Backbone",
        "type": "BACKBONE_ROUTER",
        "status": "DOWN",
    },
    timeout=10.0,
)

print(f"Status: {response.status_code}")
print(f"Body: {response.text}")
