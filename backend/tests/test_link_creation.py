from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _mk_device(dev_id: str, dev_type: str):
    r = client.post(
        "/api/devices",
        json={"id": dev_id, "name": dev_id, "type": dev_type, "status": "UP"},
    )
    assert r.status_code == 201, r.text


def test_link_create_between_new_devices():
    _mk_device("backbone_gateway", "BACKBONE_GATEWAY")
    _mk_device("core1", "CORE_ROUTER")

    # create link (should auto-use if0 interfaces)
    payload = {
        "id": "backbone_gateway__core1",
        "a_interface_id": "backbone_gateway-if0",
        "b_interface_id": "core1-if0",
        "kind": "FIBER",
        "status": "UP",
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] == "backbone_gateway__core1"
    assert body["a_interface_id"].endswith("-if0")
    assert body["b_interface_id"].endswith("-if0")

    # duplicate create should yield 409
    r2 = client.post("/api/links", json=payload)
    assert r2.status_code == 409

    # list should show exactly one link
    r3 = client.get("/api/links")
    assert r3.status_code == 200
    links = r3.json()
    assert len(links) == 1
    assert links[0]["a_device_id"] in {"backbone_gateway", "core1"}
    assert links[0]["b_device_id"] in {"backbone_gateway", "core1"}


def test_multiple_link_creations():
    # first pair
    _mk_device("backbone_gateway", "BACKBONE_GATEWAY")
    _mk_device("core1", "CORE_ROUTER")
    r1 = client.post(
        "/api/links",
        json={
            "id": "backbone_gateway__core1",
            "a_interface_id": "backbone_gateway-if0",
            "b_interface_id": "core1-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r1.status_code == 201, r1.text

    # second independent pair
    _mk_device("backbone_gateway2", "BACKBONE_GATEWAY")
    _mk_device("core2", "CORE_ROUTER")
    r2 = client.post(
        "/api/links",
        json={
            "id": "backbone_gateway2__core2",
            "a_interface_id": "backbone_gateway2-if0",
            "b_interface_id": "core2-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r2.status_code == 201, r2.text

    # third link across existing device and new device
    r3 = client.post(
        "/api/links",
        json={
            "id": "core1__core2",
            "a_interface_id": "core1-if0",
            "b_interface_id": "core2-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r3.status_code == 201, r3.text

    # list should show 3 links
    rlist = client.get("/api/links")
    assert rlist.status_code == 200
    assert len(rlist.json()) == 3


def test_link_with_underscored_ids():
    _mk_device("backbone_gateway_2", "BACKBONE_GATEWAY")
    _mk_device("core_switch_2", "CORE_ROUTER")
    payload = {
        "id": "backbone_gateway_2__core_switch_2",
        "a_interface_id": "backbone_gateway_2-if0",
        "b_interface_id": "core_switch_2-if0",
        "kind": "FIBER",
        "status": "UP",
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] == payload["id"]
    assert body["a_interface_id"].endswith("-if0")
    assert body["b_interface_id"].endswith("-if0")


def test_link_same_interface_endpoint_error():
    _mk_device("devx", "CORE_ROUTER")
    payload = {
        "id": "devx__devx",
        "a_interface_id": "devx-if0",
        "b_interface_id": "devx-if0",
        "kind": "FIBER",
        "status": "UP",
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 400
    assert "Endpoints must differ" in r.text


def test_link_non_canonical_id_rejected():
    _mk_device("aa", "CORE_ROUTER")
    _mk_device("bb", "CORE_ROUTER")
    # Wrong id ordering (expected aa__bb)
    payload = {
        "id": "zz__aa",  # garbage ordering
        "a_interface_id": "aa-if0",
        "b_interface_id": "bb-if0",
        "kind": "FIBER",
        "status": "UP",
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 400
    assert "Link id not canonical" in r.text


def test_link_duplicate_id_conflict():
    _mk_device("gwA", "BACKBONE_GATEWAY")
    _mk_device("coreA", "CORE_ROUTER")
    ok_payload = {
        "id": "gwA__coreA",
        "a_interface_id": "gwA-if0",
        "b_interface_id": "coreA-if0",
        "kind": "FIBER",
        "status": "UP",
    }
    r1 = client.post("/api/links", json=ok_payload)
    assert r1.status_code == 201, r1.text
    # same id but different interface order (should still 409 because id taken)
    dup_payload = {
        "id": "gwA__coreA",
        "a_interface_id": "coreA-if0",
        "b_interface_id": "gwA-if0",
        "kind": "FIBER",
        "status": "UP",
    }
    r2 = client.post("/api/links", json=dup_payload)
    assert r2.status_code == 409
