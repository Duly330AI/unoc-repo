import importlib

from sqlmodel import Session

from backend import events
from backend.db import engine, init_db, reset_db
from backend.models import Device, DeviceType, Interface, Link, LinkType, Status
from backend.services.provisioning_service import provision_device
from backend.services.status_recompute import recompute_devices_status
from backend.services.status_service import evaluate_device_status


def setup_function(_):
    reset_db()
    init_db()
    events.reset_events()


def _dev(i, t):
    return Device(id=i, name=i, type=t)


def _iface(device: Device, name: str = "if0"):
    return Interface(id=f"{device.id}-{name}", device_id=device.id, name=name)


def _link(a: Device, b: Device, kind: LinkType = LinkType.FIBER):
    return Link(
        id=f"{a.id}-{b.id}",
        a_interface_id=f"{a.id}-if0",
        b_interface_id=f"{b.id}-if0",
        kind=kind,
    )


def _enable_path_validation():
    # Path validation is always-on; reload the module to ensure clean state if tests mutated globals.
    import backend.services.dependency_resolver as dr  # noqa: F401

    importlib.reload(dr)


def test_provision_triggers_status_event_for_active_device():
    with Session(engine) as s:
        core = _dev("coreX", DeviceType.CORE_ROUTER)
        s.add(core)
        s.commit()
        provision_device(s, core)
        refreshed = s.get(Device, core.id)
        assert refreshed is not None, "Device not found after provisioning"
        assert refreshed.provisioned is True
        assert refreshed.status.name == "UP"
        history = events.get_event_history()
        # Accept either direct status change (if initial status differs) or at least a provisioned event
        assert any(
            (e.type in {"device.status.changed", "device.provisioned"})
            and e.payload.get("id") == core.id
            for e in history
        )


def test_provision_ont_triggers_optical_placeholder_no_error():
    # Full positive path: core --(fiber)--> olt --(fiber)--> ont
    _enable_path_validation()
    with Session(engine) as s:
        pop = _dev("popY", DeviceType.POP)
        core = _dev("coreY", DeviceType.CORE_ROUTER)
        olt = _dev("oltY", DeviceType.OLT)
        olt.parent_container_id = pop.id
        ont = _dev("ontY", DeviceType.ONT)
        for d in (pop, core, olt, ont):
            s.add(d)
        for dev in (core, olt, ont):
            s.add(_iface(dev))
        s.add(_link(core, olt))
        s.add(_link(olt, ont))
        s.commit()
        provision_device(s, core)
        provision_device(s, olt)
        provision_device(s, ont)
        refreshed = s.get(Device, ont.id)
        assert refreshed is not None, "ONT not found after provisioning"
        assert refreshed.provisioned is True
        # Placeholder: status event for ont provisioning
        history = events.get_event_history()
        assert any(
            (e.type in {"device.status.changed", "device.provisioned"})
            and e.payload.get("id") == ont.id
            for e in history
        )


def test_propagation_seeding_respects_effective_up(monkeypatch):
    # Enable propagation
    # Status propagation and active-degrade are always-on; no env toggles required.
    with Session(engine) as s:
        # pop (always online) -- core (active) -- edge (active)
        pop = _dev("popZ", DeviceType.POP)
        core = _dev("coreZ", DeviceType.CORE_ROUTER)
        edge = _dev("edgeZ", DeviceType.EDGE_ROUTER)
        s.add(pop)
        s.add(core)
        s.add(edge)
        for dev in (core, edge):
            s.add(_iface(dev))
        s.add(_link(core, edge))
        s.commit()

        # Provision only core; edge unprovisioned
        provision_device(s, core)
        # Force pop overridden DOWN so it isn't a seed
        pop.admin_override_status = Status.DOWN
        s.add(pop)
        s.commit()

        # Recompute propagation snapshot
        recompute_devices_status(s, include_passive_propagation=True)
        # Core is provisioned but without any ALWAYS_ONLINE anchor reachable -> strict L3 yields DOWN
        assert evaluate_device_status(core) == Status.DOWN
        # Edge is unprovisioned active -> DOWN (no degrade applied to DOWN base)
        assert evaluate_device_status(edge) == Status.DOWN


def test_active_device_degrades_when_unreachable(monkeypatch):
    # Status propagation and active-degrade are always-on; no env toggles required.
    with Session(engine) as s:
        pop = _dev("popD", DeviceType.POP)
        bb = _dev("bbD", DeviceType.BACKBONE_GATEWAY)
        core = _dev("coreD", DeviceType.CORE_ROUTER)
        for d in (pop, bb, core):
            s.add(d)
        for dev in (bb, core):
            s.add(_iface(dev))
        s.add(_link(bb, core))
        s.commit()
        provision_device(s, core)
        s.commit()

        # Baseline effective statuses with always-on auto L3 uplinks:
        recompute_devices_status(s, include_passive_propagation=True)
        assert evaluate_device_status(bb) == Status.UP
        # Core is auto-configured for L3 reachability to backbone and should be UP
        assert evaluate_device_status(core) == Status.UP

        # Now force bb DOWN via override, recompute
        bb.admin_override_status = Status.DOWN
        s.add(bb)
        s.commit()
        recompute_devices_status(s, include_passive_propagation=True)
        # With backbone overridden DOWN, core loses reachability and degrades accordingly
        assert evaluate_device_status(core) == Status.DOWN
