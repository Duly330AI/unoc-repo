from fastapi.testclient import TestClient

from backend.main import app


def test_create_core_site_succeeds():
    client = TestClient(app)
    r = client.post(
        "/api/devices",
        json={"id": "coreSite1", "name": "coreSite1", "type": "CORE_SITE", "status": "UP"},
    )
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["id"] == "coreSite1"
    assert j["type"] == "CORE_SITE"
    # role should be always_online like POP
    assert j["role"] == "always_online"


def test_assign_child_into_core_site_and_move_out():
    client = TestClient(app)
    # Create container and a child EDGE_ROUTER inside it (allowed)
    r = client.post(
        "/api/devices",
        json={"id": "cs2", "name": "cs2", "type": "CORE_SITE", "status": "UP"},
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/devices",
        json={
            "id": "edgeX",
            "name": "edgeX",
            "type": "EDGE_ROUTER",
            "status": "UP",
            "parent_container_id": "cs2",
        },
    )
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["parent_container_id"] == "cs2"

    # Create a POP to serve as an initial valid parent
    r = client.post(
        "/api/devices",
        json={"id": "p1", "name": "p1", "type": "POP", "status": "UP"},
    )
    assert r.status_code == 201, r.text
    # Create another EDGE_ROUTER under POP, then move into the CORE_SITE via PUT update
    r = client.post(
        "/api/devices",
        json={
            "id": "edgeY",
            "name": "edgeY",
            "type": "EDGE_ROUTER",
            "status": "UP",
            "parent_container_id": "p1",
        },
    )
    assert r.status_code == 201, r.text
    r = client.put(
        "/api/devices/edgeY",
        json={"parent_container_id": "cs2"},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["parent_container_id"] == "cs2"

    # Now move edgeY out of the CORE_SITE back to POP (edge is allowed in POP too)
    r = client.put(
        "/api/devices/edgeY",
        json={"parent_container_id": "p1"},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["parent_container_id"] == "p1"
