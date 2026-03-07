from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, Status
from backend.services.status_service import evaluate_link_status


def _mk_dev(id: str, t: DeviceType, status: Status = Status.UP, provisioned: bool = True):
    with get_session() as s:
        if not s.get(Device, id):
            d = Device(id=id, name=id, type=t, status=status, provisioned=provisioned)
            s.add(d)
            s.commit()
            if_id = f"{id}-if0"
            if not s.get(Interface, if_id):
                s.add(Interface(id=if_id, device_id=id, name="if0"))
                s.commit()


def _mk_link(a: str, b: str) -> Link:
    with get_session() as s:
        lid = "__".join(sorted([a, b]))
        ln = s.get(Link, lid)
        if not ln:
            ln = Link(
                id=lid, a_interface_id=f"{a}-if0", b_interface_id=f"{b}-if0", status=Status.UP
            )
            s.add(ln)
            s.commit()
        return ln


def test_link_effective_status_follows_endpoints():
    init_db()
    _mk_dev("core", DeviceType.CORE_ROUTER)
    _mk_dev("edge", DeviceType.EDGE_ROUTER)
    ln = _mk_link("core", "edge")

    # Initially both endpoints UP -> effective link status is stored status (UP)
    assert evaluate_link_status(ln) == Status.UP

    # Override edge DOWN -> link effective status becomes DOWN
    with get_session() as s:
        e = s.get(Device, "edge")
        assert e
        e.admin_override_status = Status.DOWN
        s.add(e)
        s.commit()
    assert evaluate_link_status(ln) == Status.DOWN

    # Bring edge back UP -> link effective status returns to UP
    with get_session() as s:
        e = s.get(Device, "edge")
        assert e
        e.admin_override_status = None
        s.add(e)
        s.commit()
    assert evaluate_link_status(ln) == Status.UP
