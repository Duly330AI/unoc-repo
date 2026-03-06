from sqlmodel import Session, select

from backend.db import engine, init_db, reset_db
from backend.models import Device, DeviceType, Interface, Link, LinkType
from backend.services import dependency_resolver as dr
from backend.services.pathfinding import DeviceRecord


def collect(session: Session):
    devs = session.exec(select(Device)).all()
    links = session.exec(select(Link)).all()
    drec = [DeviceRecord(id=d.id, type=d.type.value) for d in devs]

    def derive_dev(iface_id: str) -> str:
        return iface_id[:-4] if iface_id.endswith("-if0") else iface_id

    lrec = []
    for link in links:
        a = derive_dev(link.a_interface_id)
        b = derive_dev(link.b_interface_id)
        lrec.append(dr.LinkRecord(id=link.id, a_device_id=a, b_device_id=b, kind=link.kind.value))
    return drec, lrec


def main():
    reset_db()
    init_db()
    with Session(engine) as s:
        pop = Device(id="popP", name="popP", type=DeviceType.POP)
        core = Device(id="coreA", name="coreA", type=DeviceType.CORE_ROUTER)
        olt = Device(id="oltA", name="oltA", type=DeviceType.OLT, parent_container_id="popP")
        s.add(pop)
        s.add(core)
        s.add(olt)
        for dev in (core, olt):
            s.add(Interface(id=f"{dev.id}-if0", device_id=dev.id, name="if0"))
        s.add(
            Link(
                id="L1",
                a_interface_id="coreA-if0",
                b_interface_id="oltA-if0",
                kind=LinkType.FIBER,
            )
        )
        s.commit()
        drec, lrec = collect(s)
        lg = dr.build_logical_graph(drec, lrec, relaxed=False)
        print("Nodes:", lg.nodes(data=True))
        print("Edges:", list(lg.edges()))
        print(
            "OLT has path to CORE?",
            "oltA" in lg and "coreA" in lg and __import__("networkx").has_path(lg, "oltA", "coreA"),
        )


if __name__ == "__main__":
    main()
