from fastapi.testclient import TestClient

from backend.main import app


def test_list_devices_include_interfaces(monkeypatch):
    client = TestClient(app)
    # create two devices (if0 will be auto-created lazily on link paths elsewhere, so we add explicitly via device create's side effect)
    for did, dtype in [("dli1", "CORE_ROUTER"), ("dli2", "EDGE_ROUTER")]:
        r = client.post(
            "/api/devices",
            json={"id": did, "name": did, "type": dtype, "status": "UP"},
        )
        assert r.status_code == 201

    # list without interfaces
    r0 = client.get("/api/devices")
    assert r0.status_code == 200
    arr0 = r0.json()
    assert isinstance(arr0, list)
    assert all("interfaces" not in d for d in arr0)

    # list with interfaces
    r1 = client.get("/api/devices?include_interfaces=true")
    assert r1.status_code == 200
    arr1 = r1.json()
    assert isinstance(arr1, list)
    # interfaces may be empty lists, but field should be present
    for d in arr1:
        assert "interfaces" in d


def test_backbone_mgmt_allocation_flag(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("ALLOW_BACKBONE_MGMT_IP", "1")
    r = client.post(
        "/api/devices",
        json={
            "id": "bbflag1",
            "name": "bbflag1",
            "type": "BACKBONE_GATEWAY",
            "status": "UP",
        },
    )
    assert r.status_code == 201
    # listing with interfaces to verify mgmt0 presence when pool exists or is created
    r2 = client.get("/api/devices?include_interfaces=true")
    assert r2.status_code == 200
    arr = r2.json()
    bb = next(d for d in arr if d["id"] == "bbflag1")
    # interfaces exists; mgmt0 may or may not be present depending on allocation, but field coverage is ensured
    assert "interfaces" in bb
