from fastapi.testclient import TestClient

from backend.api.endpoints.links import list_links
from backend.db import get_session, init_db
from backend.main import app
from backend.models import Device, DeviceType, Interface, Link, Status


def _mk_dev(id: str, t: DeviceType):
    with get_session() as s:
        if not s.get(Device, id):
            s.add(Device(id=id, name=id, type=t, provisioned=True))
            s.commit()
        if_id = f"{id}-if0"
        if not s.get(Interface, if_id):
            s.add(Interface(id=if_id, device_id=id, name="if0"))
            s.commit()


def _mk_link(a: str, b: str) -> str:
    with get_session() as s:
        lid = "__".join(sorted([f"{a}-if0", f"{b}-if0"]))
        if not s.get(Link, lid):
            s.add(
                Link(id=lid, a_interface_id=f"{a}-if0", b_interface_id=f"{b}-if0", status=Status.UP)
            )
            s.commit()
        return lid


def test_link_effective_status_field_reflects_override():
    init_db()
    _mk_dev("core", DeviceType.CORE_ROUTER)
    _mk_dev("edge", DeviceType.EDGE_ROUTER)
    lid = _mk_link("core", "edge")
    client = TestClient(app)

    # Initially effective_status should be UP
    links = list_links()
    eff = {item.id: item.effective_status for item in links}
    assert eff.get(lid) == "UP"

    # Force DOWN and check again via HTTP (async)
    r = client.patch(f"/api/links/{lid}/override", json={"admin_override_status": "DOWN"})
    assert r.status_code == 202
    # Drain queue so list reflects the change
    from backend.services.job_dispatcher import QUEUE, handle_batch
    from backend.services.worker import Worker

    if QUEUE.size() > 0:
        Worker().run_once(QUEUE, handle_batch, max_items=256)
    links2 = list_links()
    eff2 = {item.id: item.effective_status for item in links2}
    assert eff2.get(lid) == "DOWN"
