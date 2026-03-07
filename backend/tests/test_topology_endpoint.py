from fastapi.testclient import TestClient

from backend.main import app


def test_topology_version_empty():
    client = TestClient(app)
    r = client.get("/api/topology/version")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert body["optical"]["nodes"] == 0
    assert body["optical"]["edges"] == 0
    assert body["logical"]["nodes"] == 0
    assert body["logical"]["edges"] == 0


def test_topology_version_minimal_graph():
    client = TestClient(app)
    # create two routers and a link between them
    r = client.post(
        "/api/devices",
        json={"id": "r1", "name": "r1", "type": "CORE_ROUTER", "status": "UP"},
    )
    assert r.status_code == 201
    r = client.post(
        "/api/devices",
        json={"id": "r2", "name": "r2", "type": "EDGE_ROUTER", "status": "UP"},
    )
    assert r.status_code == 201
    r = client.post(
        "/api/links",
        json={
            "id": "r1__r2",
            "a_interface_id": "r1-if0",
            "b_interface_id": "r2-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r.status_code == 201
    rv = client.get("/api/topology/version")
    assert rv.status_code == 200
    body = rv.json()
    # logical graph should have 2 nodes, 1 edge; optical graph may mirror it
    assert body["logical"]["nodes"] == 2
    assert body["logical"]["edges"] == 1
