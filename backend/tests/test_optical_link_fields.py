from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _mk_device(id: str, type: str, parent: str | None = None):
    payload = {"id": id, "name": id, "type": type, "status": "UP"}
    if parent is not None:
        payload["parent_container_id"] = parent
    r = client.post("/api/devices", json=payload)
    assert r.status_code == 201, r.text


def test_create_link_with_optical_fields_ok():
    _mk_device("pop1", "POP")
    _mk_device("oltZ", "OLT", parent="pop1")
    _mk_device("odfZ", "ODF")
    # Create OLT <-> ODF with explicit length
    payload = {
        "id": "odfZ__oltZ" if "odfZ" < "oltZ" else "oltZ__odfZ",
        "a_interface_id": "oltZ-if0",
        "b_interface_id": "odfZ-if0",
        "kind": "FIBER",
        "status": "UP",
        "length_km": 12.34,
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["length_km"] == 12.34
    assert isinstance(data.get("physical_medium_id"), int | type(None))


def test_create_link_with_invalid_length():
    _mk_device("pop1", "POP")
    _mk_device("oltX", "OLT", parent="pop1")
    _mk_device("odfX", "ODF")
    payload = {
        "id": "odfX__oltX" if "odfX" < "oltX" else "oltX__odfX",
        "a_interface_id": "oltX-if0",
        "b_interface_id": "odfX-if0",
        "kind": "FIBER",
        "status": "UP",
        "length_km": -1.0,
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 400


def test_create_link_without_physical_medium_defaults_ok():
    _mk_device("pop1", "POP")
    _mk_device("oltY", "OLT", parent="pop1")
    _mk_device("odfY", "ODF")
    payload = {
        "id": "odfY__oltY" if "odfY" < "oltY" else "oltY__odfY",
        "a_interface_id": "oltY-if0",
        "b_interface_id": "odfY-if0",
        "kind": "FIBER",
        "status": "UP",
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert isinstance(data.get("physical_medium_id"), int)
