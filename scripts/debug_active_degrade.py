from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, Status, Tariff
from backend.services import status_propagation_store as store
from backend.services.status_recompute import recompute_devices_status
from backend.services.status_service import evaluate_device_status


def mk_dev(id: str, t: DeviceType, provisioned: bool = True):
    with get_session() as s:
        if not s.get(Device, id):
            d = Device(id=id, name=id, type=t, provisioned=provisioned)
            s.add(d)
            s.commit()
        if_id = f"{id}-if0"
        if not s.get(Interface, if_id):
            s.add(Interface(id=if_id, device_id=id, name="if0"))
            s.commit()


def mk_link(a_dev: str, b_dev: str) -> str:
    with get_session() as s:
        lid = "__".join(sorted([f"{a_dev}-if0", f"{b_dev}-if0"]))
        if not s.get(Link, lid):
            s.add(
                Link(
                    id=lid,
                    a_interface_id=f"{a_dev}-if0",
                    b_interface_id=f"{b_dev}-if0",
                    status=Status.UP,
                )
            )
            s.commit()
        return lid


def main():
    init_db()
    mk_dev("bb", DeviceType.BACKBONE_GATEWAY, provisioned=True)
    mk_dev("core", DeviceType.CORE_ROUTER, provisioned=True)
    mk_dev("edge", DeviceType.EDGE_ROUTER, provisioned=True)
    mk_dev("sw", DeviceType.AON_SWITCH, provisioned=True)
    mk_dev("cpe", DeviceType.AON_CPE, provisioned=True)
    with get_session() as s:
        if s.get(Tariff, 1) is None:
            s.add(Tariff(id=1, name="t", max_up_mbps=10, max_down_mbps=10))
            s.commit()
        cpe = s.get(Device, "cpe")
        assert cpe is not None
        cpe.tariff_id = 1
        s.add(cpe)
        s.commit()
    mk_link("bb", "core")
    core_edge = mk_link("core", "edge")
    mk_link("edge", "sw")
    mk_link("sw", "cpe")
    with get_session() as s:
        recompute_devices_status(s)
        for id_ in ["bb", "core", "edge", "sw", "cpe"]:
            d = s.get(Device, id_)
            print(id_, "status:", evaluate_device_status(d))
    print("reachable before:", store.is_up("edge"))
    with get_session() as s:
        ln = s.get(Link, core_edge)
        ln.admin_override_status = Status.DOWN
        s.add(ln)
        s.commit()
        recompute_devices_status(s)
        edge = s.get(Device, "edge")
        core = s.get(Device, "core")
        print("reachable after edge:", store.is_up("edge"))
        print("reachable after core:", store.is_up("core"))
        print("eval edge:", evaluate_device_status(edge))
        print("eval core:", evaluate_device_status(core))


if __name__ == "__main__":
    main()
