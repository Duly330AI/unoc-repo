from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_tariff_crud_happy_path():
    c = _client()
    # Create
    r = c.post(
        "/api/tariffs",
        json={"name": "Basic 100/20", "max_up_mbps": 20.0, "max_down_mbps": 100.0},
    )
    assert r.status_code == 201, r.text
    t1 = r.json()
    assert isinstance(t1["id"], int)
    tid = t1["id"]
    assert t1["name"] == "Basic 100/20"
    assert t1["max_up_mbps"] == 20.0
    assert t1["max_down_mbps"] == 100.0

    # List
    r = c.get("/api/tariffs")
    assert r.status_code == 200
    items = r.json()
    assert any(it["id"] == tid for it in items)

    # Get by id
    r = c.get(f"/api/tariffs/{tid}")
    assert r.status_code == 200
    got = r.json()
    assert got["id"] == tid

    # Update
    r = c.put(
        f"/api/tariffs/{tid}",
        json={"name": "Pro 1000/300", "max_up_mbps": 300.0, "max_down_mbps": 1000.0},
    )
    assert r.status_code == 200
    upd = r.json()
    assert upd["name"] == "Pro 1000/300"
    assert upd["max_up_mbps"] == 300.0
    assert upd["max_down_mbps"] == 1000.0

    # Delete
    r = c.delete(f"/api/tariffs/{tid}")
    assert r.status_code == 204

    # Ensure gone
    r = c.get(f"/api/tariffs/{tid}")
    assert r.status_code == 404


def test_tariff_create_duplicate_name_conflict():
    c = _client()
    payload = {"name": "Starter", "max_up_mbps": 10.0, "max_down_mbps": 50.0}
    r1 = c.post("/api/tariffs", json=payload)
    assert r1.status_code == 201
    r2 = c.post("/api/tariffs", json=payload)
    assert r2.status_code == 409
    assert r2.json()["detail"] == "TARIFF_NAME_EXISTS"


def test_tariff_update_duplicate_name_conflict():
    c = _client()
    # Create A and B
    r = c.post("/api/tariffs", json={"name": "A", "max_up_mbps": 1.0, "max_down_mbps": 10.0})
    assert r.status_code == 201
    r = c.post("/api/tariffs", json={"name": "B", "max_up_mbps": 2.0, "max_down_mbps": 20.0})
    assert r.status_code == 201
    tid_b = r.json()["id"]
    # Try rename B -> A
    r = c.put(f"/api/tariffs/{tid_b}", json={"name": "A"})
    assert r.status_code == 409
    assert r.json()["detail"] == "TARIFF_NAME_EXISTS"


def test_tariff_validation_negative_values_and_missing_name():
    c = _client()
    # Negative up
    r = c.post("/api/tariffs", json={"name": "NegUp", "max_up_mbps": -1, "max_down_mbps": 1})
    assert r.status_code == 422
    # Negative down
    r = c.post("/api/tariffs", json={"name": "NegDown", "max_up_mbps": 1, "max_down_mbps": -1})
    assert r.status_code == 422
    # Missing name
    r = c.post("/api/tariffs", json={"max_up_mbps": 1, "max_down_mbps": 1})
    assert r.status_code == 422


def test_tariff_list_sorted_by_name():
    c = _client()
    c.post("/api/tariffs", json={"name": "Zeta", "max_up_mbps": 1, "max_down_mbps": 1})
    c.post("/api/tariffs", json={"name": "Alpha", "max_up_mbps": 1, "max_down_mbps": 1})
    r = c.get("/api/tariffs")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert names == sorted(names)
