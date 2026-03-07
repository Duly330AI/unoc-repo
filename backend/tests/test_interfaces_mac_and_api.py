from fastapi.testclient import TestClient

from backend.db import get_session, init_db, reset_db
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, LinkType
from backend.services.provisioning_service import provision_device


def setup_function():
    reset_db()


def test_provisioning_sets_mgmt0_mac():
    init_db()
    with get_session() as s:
        # Seed upstream
        s.add(Device(id="bb1", name="bb1", type=DeviceType.BACKBONE_GATEWAY))
        s.commit()
        core = Device(id="core1", name="core1", type=DeviceType.CORE_ROUTER)
        pop = Device(id="pop1", name="pop1", type=DeviceType.POP)
        olt = Device(id="olt1", name="olt1", type=DeviceType.OLT, parent_container_id="pop1")
        s.add(core)
        s.add(pop)
        s.add(olt)
        s.commit()
        # Ensure minimal logical adjacency core<->olt for strict path validation
        s.add(Interface(id=f"{core.id}-if0", device_id=core.id, name="if0"))
        s.add(Interface(id=f"{olt.id}-if0", device_id=olt.id, name="if0"))
        s.add(Interface(id="bb1-if0", device_id="bb1", name="if0"))
        s.add(
            Link(
                id=f"{core.id}-{olt.id}",
                a_interface_id=f"{core.id}-if0",
                b_interface_id=f"{olt.id}-if0",
                kind=LinkType.FIBER,
            )
        )
        s.add(
            Link(
                id="core1-bb1",
                a_interface_id="core1-if0",
                b_interface_id="bb1-if0",
                kind=LinkType.FIBER,
            )
        )
        s.commit()
        provision_device(s, core)
        provision_device(s, olt)
        s.commit()
        mgmt = s.get(Interface, "olt1-mgmt0")
        assert mgmt is not None
        assert isinstance(mgmt.mac_address, str)
        assert mgmt.mac_address.count(":") == 5


def test_interfaces_api_create_assigns_mac():
    client = TestClient(app)
    # create device via API
    r = client.post(
        "/api/devices",
        json={"id": "d-ifapi", "name": "d-ifapi", "type": "EDGE_ROUTER", "status": "UP"},
    )
    assert r.status_code == 201
    # create new interface
    r2 = client.post(
        "/api/devices/d-ifapi/interfaces",
        json={"name": "if9", "role": "access"},
    )
    assert r2.status_code == 201
    data = r2.json()
    assert data["id"] == "d-ifapi-if9"
    assert isinstance(data["mac_address"], str) and data["mac_address"].startswith("02:")
    # list interfaces
    r3 = client.get("/api/devices/d-ifapi/interfaces")
    assert r3.status_code == 200
    arr = r3.json()
    assert any(i["id"] == "d-ifapi-if9" and i["mac_address"] == data["mac_address"] for i in arr)
