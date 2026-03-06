from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, Status
from backend.services.status_service import evaluate_link_status, is_link_passable


def _mk_device(session, did: str, dtype: DeviceType) -> Device:
    dev = Device(id=did, name=did, type=dtype, provisioned=True)
    session.add(dev)
    # default interface to simplify link creation
    iface = Interface(id=f"{did}-if0", device_id=did, name="if0")
    session.add(iface)
    return dev


def test_link_override_immediate_passability_reflection():
    """Force a link DOWN via admin override and assert evaluate_link_status + is_link_passable
    reflect this immediately (no wait for recompute cascade)."""
    init_db()
    with get_session() as s:
        # Build two active devices with a single link
        _mk_device(s, "core1", DeviceType.CORE_ROUTER)
        _mk_device(s, "edge1", DeviceType.EDGE_ROUTER)
        lnk = Link(
            id="core1-if0__edge1-if0",
            a_interface_id="core1-if0",
            b_interface_id="edge1-if0",
            status=Status.UP,
        )
        s.add(lnk)
        s.commit()
    # Reload objects in fresh session to avoid stale state
    with get_session() as s:
        link = s.exec(select(Link).where(Link.id == "core1-if0__edge1-if0")).first()
        assert link is not None
        assert evaluate_link_status(link) == Status.UP
        assert is_link_passable(link) is True
        # Apply admin override DOWN on link
        link.admin_override_status = Status.DOWN
        s.add(link)
        s.commit()
    # Fresh session again to simulate API read
    with get_session() as s:
        link2 = s.exec(select(Link).where(Link.id == "core1-if0__edge1-if0")).first()
        assert link2 is not None
        eff = evaluate_link_status(link2)
        assert eff == Status.DOWN, f"Expected effective link status DOWN, got {eff}"
        assert is_link_passable(link2) is False
