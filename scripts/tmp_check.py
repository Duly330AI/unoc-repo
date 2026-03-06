import sys

sys.path.insert(0, r"c:\noc_project\UNOC\unoc")
from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, Status
from backend.services.dependency_resolver import evaluate_upstream_dependencies
from backend.services.status_propagation_store import is_up
from backend.services.status_recompute import recompute_devices_status
from backend.services.status_service import evaluate_device_status

init_db()
with get_session() as s:
    # Clear tables by resetting DB is not available here; assume fresh or ids unique
    for id_, t in [
        ("bb", DeviceType.BACKBONE_GATEWAY),
        ("core", DeviceType.CORE_ROUTER),
        ("edge", DeviceType.EDGE_ROUTER),
    ]:
        if s.get(Device, id_) is None:
            s.add(Device(id=id_, name=id_, type=t, provisioned=True))
    for id_ in ("bb", "core", "edge"):
        if s.get(Interface, f"{id_}-if0") is None:
            s.add(Interface(id=f"{id_}-if0", device_id=id_, name="if0"))
    if s.get(Link, "bb__core") is None:
        s.add(
            Link(
                id="bb__core", a_interface_id="bb-if0", b_interface_id="core-if0", status=Status.UP
            )
        )
    if s.get(Link, "core__edge") is None:
        s.add(
            Link(
                id="core__edge",
                a_interface_id="core-if0",
                b_interface_id="edge-if0",
                status=Status.UP,
            )
        )
    s.commit()
    recompute_devices_status(s)
    core = s.get(Device, "core")
    edge = s.get(Device, "edge")
    print("is_up core before:", is_up("core"))
    print("is_up edge before:", is_up("edge"))
    print("eval core status before:", evaluate_device_status(core))
    print("eval edge status before:", evaluate_device_status(edge))
    ln = s.get(Link, "core__edge")
    ln.admin_override_status = Status.DOWN
    s.add(ln)
    s.commit()
    recompute_devices_status(s)
    core = s.get(Device, "core")
    edge = s.get(Device, "edge")
    print("is_up core after:", is_up("core"))
    print("is_up edge after:", is_up("edge"))
    print("resolver core after:", evaluate_upstream_dependencies(s, core).ok)
    print("resolver edge after:", evaluate_upstream_dependencies(s, edge).ok)
    print("eval core status after:", evaluate_device_status(core))
    print("eval edge status after:", evaluate_device_status(edge))
    # Now simulate bb forced DOWN scenario
    bb = s.get(Device, "bb")
    bb.admin_override_status = Status.DOWN
    s.add(bb)
    s.commit()
    recompute_devices_status(s)
    core = s.get(Device, "core")
    print("bb down -> is_up core:", is_up("core"))
    print("bb down -> resolver core:", evaluate_upstream_dependencies(s, core).ok)
    print("bb down -> eval core:", evaluate_device_status(core))
