from backend.db import get_session, init_db
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status, Tariff
from backend.services.status_recompute import recompute_devices_status
from backend.services.traffic_engine import TrafficEngine


def _dev(i, t, prov=True):
    return Device(id=i, name=i, type=t, provisioned=prov, status=Status.UP)


def _iface(dev: Device, name: str = "if0"):
    return Interface(id=f"{dev.id}-{name}", device_id=dev.id, name=name)


def _link(a: Device, b: Device):
    a_id, b_id = sorted([a.id, b.id])
    return Link(
        id=f"{a_id}__{b_id}",
        a_interface_id=f"{a.id}-if0",
        b_interface_id=f"{b.id}-if0",
        kind=LinkType.FIBER,
        status=Status.UP,
    )


def _tariff(name: str, down: float, up: float) -> Tariff:
    return Tariff(name=name, max_down_mbps=down, max_up_mbps=up)


def test_leaf_traffic_stops_when_backbone_down_breaks_upstream_l3():
    """Ensure leaf (ONT) stops generating traffic once upstream L3 path fails.

    Topology: BACKBONE_GATEWAY(bb) -- CORE_ROUTER(core) -- OLT(olt) -- ONT(ont)
    Steps:
      1. Build chain, assign tariff to ONT, run tick => traffic generated.
      2. Force backbone DOWN (admin override) + recompute => upstream helper will fail => no new generation.
    """
    init_db()
    with get_session() as s:
        bb = _dev("bbT", DeviceType.BACKBONE_GATEWAY)
        core = _dev("coreT", DeviceType.CORE_ROUTER)
        olt = _dev("oltT", DeviceType.OLT)
        ont = _dev("ontT", DeviceType.ONT)
        for d in (bb, core, olt, ont):
            s.add(d)
            s.add(_iface(d))
        s.add(_link(bb, core))
        s.add(_link(core, olt))
        s.add(_link(olt, ont))
        # Tariff for ONT
        t = _tariff("100/50", 100.0, 50.0)
        s.add(t)
        s.commit()
        s.refresh(t)
        ont.tariff_id = t.id
        s.add(ont)
        s.commit()
        recompute_devices_status(s)

    eng = TrafficEngine()
    eng.random_seed = 123
    eng.run_tick()
    first = eng._debug_last_generated.get("ontT")
    assert first is not None, "ONT should generate traffic before failure"

    # Break upstream L3 by forcing backbone DOWN
    with get_session() as s:
        bbm = s.get(Device, "bbT")
        assert bbm
        bbm.admin_override_status = Status.DOWN
        s.add(bbm)
        s.commit()
        recompute_devices_status(s)

    eng.run_tick()
    # Should not generate new entry (value may persist from previous tick, so compare tick_seq change)
    # Simplest: ensure no update recorded for current tick by clearing and re-running
    eng._debug_last_generated.pop("ontT", None)
    eng.run_tick()
    assert (
        eng._debug_last_generated.get("ontT") is None
    ), "Leaf traffic should be gated after L3 loss"
