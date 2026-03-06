from fastapi.testclient import TestClient

from backend.main import app


def test_health_metrics_and_layout_endpoints():
    client = TestClient(app)

    # metrics/events
    r = client.get("/api/metrics/events")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict) and "events" in body

    # layout: patch with items
    r2 = client.patch(
        "/api/layout/positions",
        json={
            "positions": [
                {
                    "id": "node-1",
                    "x": 10,
                    "y": 20,
                    "userPinned": True,
                    "systemPinned": False,
                }
            ]
        },
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["applied"] == 1
    assert isinstance(b2["version"], int)

    # layout: patch with empty list (covers else branch)
    r3 = client.patch("/api/layout/positions", json={"positions": []})
    assert r3.status_code == 200
    b3 = r3.json()
    assert b3["applied"] == 0
    assert isinstance(b3["version"], int)

    # layout: get positions
    r4 = client.get("/api/layout/positions")
    assert r4.status_code == 200
    b4 = r4.json()
    assert "version" in b4 and isinstance(b4.get("positions"), list)
