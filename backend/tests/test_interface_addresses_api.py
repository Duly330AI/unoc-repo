from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def _client() -> TestClient:
    return TestClient(app)


def _create_device_with_interface(c: TestClient) -> tuple[str, str]:
    # Create device
    r = c.post(
        "/api/devices",
        json={
            "id": "ifaddr-dev1",
            "name": "ifaddr-dev1",
            "type": "CORE_ROUTER",
        },
    )
    assert r.status_code == 201, r.text
    # Create extra interface if1
    r = c.post("/api/devices/ifaddr-dev1/interfaces", json={"name": "if1"})
    assert r.status_code == 201, r.text
    iface_id = r.json()["id"]
    return "ifaddr-dev1", iface_id


def test_create_list_delete_interface_addresses_happy_path():
    c = _client()
    device_id, iface_id = _create_device_with_interface(c)

    # Initially empty
    r = c.get(f"/api/interfaces/{iface_id}/addresses")
    assert r.status_code == 200
    assert r.json() == []

    # Create address
    r = c.post(
        f"/api/interfaces/{iface_id}/addresses",
        json={"ip": "10.10.10.5", "prefix_len": 24},
    )
    assert r.status_code == 201, r.text
    a1 = r.json()
    assert a1["ip"] == "10.10.10.5"
    assert a1["prefix_len"] == 24

    # Create second address
    r = c.post(
        f"/api/interfaces/{iface_id}/addresses",
        json={"ip": "10.10.10.6", "prefix_len": 24},
    )
    assert r.status_code == 201
    a2 = r.json()
    assert a2["ip"] == "10.10.10.6"

    # List should include both
    r = c.get(f"/api/interfaces/{iface_id}/addresses")
    assert r.status_code == 200
    items = r.json()
    got_ips = {x["ip"] for x in items}
    assert got_ips == {"10.10.10.5", "10.10.10.6"}

    # Delete first
    r = c.delete(f"/api/interfaces/{iface_id}/addresses/{a1['id']}")
    assert r.status_code == 204

    # Ensure list now only has second
    r = c.get(f"/api/interfaces/{iface_id}/addresses")
    assert r.status_code == 200
    items = r.json()
    got_ips = {x["ip"] for x in items}
    assert got_ips == {"10.10.10.6"}


def test_address_validation_errors():
    c = _client()
    _, iface_id = _create_device_with_interface(c)

    # Missing fields
    r = c.post(f"/api/interfaces/{iface_id}/addresses", json={})
    assert r.status_code == 422

    # Invalid IP format
    r = c.post(
        f"/api/interfaces/{iface_id}/addresses",
        json={"ip": "999.999.1.1", "prefix_len": 24},
    )
    assert r.status_code == 422

    # Non IPv4 (IPv6)
    r = c.post(
        f"/api/interfaces/{iface_id}/addresses",
        json={"ip": "2001:db8::1", "prefix_len": 64},
    )
    assert r.status_code == 422

    # Invalid prefix len type
    r = c.post(
        f"/api/interfaces/{iface_id}/addresses",
        json={"ip": "10.0.0.1", "prefix_len": "not-int"},
    )
    assert r.status_code == 422

    # Out of range prefix len
    for bad in (0, 33):
        r = c.post(
            f"/api/interfaces/{iface_id}/addresses",
            json={"ip": "10.0.0.2", "prefix_len": bad},
        )
        assert r.status_code == 422

    # DELETE non-existent address
    r = c.delete(f"/api/interfaces/{iface_id}/addresses/9999")
    assert r.status_code == 404
