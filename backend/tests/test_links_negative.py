from fastapi.testclient import TestClient

from backend.db import get_session
from backend.main import app
from backend.models import Interface, InterfaceRole


def _mk_device(client: TestClient, id: str, type: str, parent: str | None = None):
    r = client.post(
        "/api/devices",
        json={
            "id": id,
            "name": id,
            "type": type,
            "status": "UP",
            "parent_container_id": parent,
        },
    )
    assert r.status_code == 201, r.text


def test_link_create_rejects_management_interface_and_non_canonical_id():
    client = TestClient(app)
    # Create parent POP and two active devices
    _mk_device(client, "pop1", "POP")
    _mk_device(client, "bb1", "BACKBONE_GATEWAY")
    _mk_device(client, "er1", "EDGE_ROUTER")
    # Ensure a management interface exists on bb1
    with get_session() as s:
        if not s.get(Interface, "bb1-mgmt0"):
            s.add(
                Interface(
                    id="bb1-mgmt0",
                    device_id="bb1",
                    name="mgmt0",
                    role=InterfaceRole.MANAGEMENT,
                )
            )
            s.commit()
    # Attempt to create a link using the management interface -> should be rejected
    payload = {
        "id": "bb1__er1",
        "a_interface_id": "bb1-mgmt0",
        "b_interface_id": "er1-if0",
        "status": "UP",
        "admin_override_status": None,
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 400
    assert "management interface" in r.text

    # Now trigger non-canonical rejection with existing devices
    _mk_device(client, "aa", "CORE_ROUTER")
    _mk_device(client, "bb", "CORE_ROUTER")
    payload2 = {
        "id": "x__y",  # unrelated id, while endpoints map to aa__bb
        "a_interface_id": "aa-if0",
        "b_interface_id": "bb-if0",
        "status": "UP",
        "admin_override_status": None,
    }
    r = client.post("/api/links", json=payload2)
    assert r.status_code == 400
    assert "not canonical" in r.text


def test_link_create_disallows_pop_participation():
    client = TestClient(app)
    _mk_device(client, "popx", "POP")
    _mk_device(client, "cr1", "CORE_ROUTER")
    # create default interface for POP to force attempt (auto-create if0 exists via ensure_default_interface on devices only; for POP, we create explicitly)
    with get_session() as s:
        if not s.get(Interface, "popx-if0"):
            s.add(Interface(id="popx-if0", device_id="popx", name="if0"))
            s.commit()
    payload = {
        "id": "popx__cr1",
        "a_interface_id": "popx-if0",
        "b_interface_id": "cr1-if0",
        "status": "UP",
        "admin_override_status": None,
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 400
    assert "POP" in r.text


def test_link_create_disallows_odf_to_odf_cascade():
    client = TestClient(app)
    # Create two ODF devices (passive aggregators)
    _mk_device(client, "odfA", "ODF")
    _mk_device(client, "odfB", "ODF")
    # Attempt to create a direct link between them should be rejected by backend rule
    payload = {
        "id": "odfA__odfB",
        "a_interface_id": "odfA-if0",
        "b_interface_id": "odfB-if0",
        "status": "UP",
        "admin_override_status": None,
    }
    r = client.post("/api/links", json=payload)
    assert r.status_code == 400
    body = r.json()
    # Standardized error code is included in detail
    assert "LINK_INVALID_PAIRING" in body.get("detail", "")
    assert "ODF" in body.get("detail", "")
