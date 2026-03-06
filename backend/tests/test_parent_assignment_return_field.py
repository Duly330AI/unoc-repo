from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_parent_field_roundtrip_for_aon_switch():
    # Create POP
    r_pop = client.post(
        "/api/devices",
        json={"id": "popZ", "name": "popZ", "type": "POP", "status": "UP"},
    )
    assert r_pop.status_code == 201, r_pop.text

    # Create AON_SWITCH with parent
    r_sw = client.post(
        "/api/devices",
        json={
            "id": "aonZ",
            "name": "aonZ",
            "type": "AON_SWITCH",
            "status": "UP",
            "parent_container_id": "popZ",
        },
    )
    assert r_sw.status_code == 201, r_sw.text
    body = r_sw.json()
    assert body.get("parent_container_id") == "popZ", body

    # Get device and confirm field present
    r_get = client.get("/api/devices/aonZ")
    assert r_get.status_code == 200
    assert r_get.json().get("parent_container_id") == "popZ"

    # Change name via update (ensuring parent retained in response)
    r_put = client.put("/api/devices/aonZ", json={"name": "aonZ_new"})
    assert r_put.status_code == 200
    body_put = r_put.json()
    assert body_put["name"] == "aonZ_new"
    # Parent must still be present
    assert body_put.get("parent_container_id") == "popZ"

    # EDGE_ROUTER may accept a POP parent (allowed)
    r_edge = client.post(
        "/api/devices",
        json={
            "id": "edgeZ",
            "name": "edgeZ",
            "type": "EDGE_ROUTER",
            "status": "UP",
            "parent_container_id": "popZ",
        },
    )
    assert r_edge.status_code == 201
