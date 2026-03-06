import importlib

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from backend.db import engine, init_db, reset_db
from backend.models import Device, DeviceType, Interface, Link, LinkType
from backend.services.provisioning_service import provision_device


def setup_function(_):
    reset_db()
    init_db()


def _dev(id_, t):
    return Device(id=id_, name=id_, type=t)


def enable_flag():
    # Path validation is now always-on; reload kept for legacy behavior isolation in tests.
    import backend.services.dependency_resolver as dr  # noqa
    import backend.services.provisioning_service as ps  # noqa

    importlib.reload(dr)
    importlib.reload(ps)
    return dr


def test_olt_requires_core_path():
    enable_flag()
    with Session(engine) as s:
        # Provide required POP parent so container rule passes first
        pop = _dev("pop1", DeviceType.POP)
        s.add(pop)
        s.commit()
        olt = _dev("olt1", DeviceType.OLT)
        olt.parent_container_id = pop.id
        s.add(olt)
        s.commit()
        with pytest.raises(HTTPException) as e:
            provision_device(s, olt)
        # Expect path invalid (no core reachable). Reason suffix may or may not be appended yet.
        assert e.value.detail.startswith("INVALID_PROVISION_PATH")


def test_ont_requires_olt_optical_path():
    enable_flag()
    with Session(engine) as s:
        ont = _dev("ont1", DeviceType.ONT)
        s.add(ont)
        # add core (not enough) and provision OLT missing => still fail
        core = _dev("core1", DeviceType.CORE_ROUTER)
        s.add(core)
        s.commit()
        with pytest.raises(HTTPException) as e:
            provision_device(s, ont)
        assert e.value.detail.startswith("INVALID_PROVISION_PATH")


def test_aon_cpe_requires_aon_switch():
    enable_flag()
    with Session(engine) as s:
        cpe = _dev("cpe1", DeviceType.AON_CPE)
        core = _dev("coreZ", DeviceType.CORE_ROUTER)
        s.add(cpe)
        s.add(core)
        s.commit()
        with pytest.raises(HTTPException) as e:
            provision_device(s, cpe)
        assert e.value.detail.startswith("INVALID_PROVISION_PATH")


def test_success_provision_core_router():
    enable_flag()
    with Session(engine) as s:
        core = _dev("coreX", DeviceType.CORE_ROUTER)
        s.add(core)
        s.commit()
        provision_device(s, core)
        assert core.provisioned is True


def _iface(device: Device, name: str = "if0"):
    return Interface(id=f"{device.id}-{name}", device_id=device.id, name=name)


def _link(a: Device, b: Device, kind: LinkType = LinkType.FIBER):
    return Link(
        id=f"{a.id}-{b.id}",
        a_interface_id=f"{a.id}-if0",
        b_interface_id=f"{b.id}-if0",
        kind=kind,
    )


def test_positive_path_ont_via_olt_to_core():
    enable_flag()
    with Session(engine) as s:
        # Create POP parent, Core, OLT (with POP parent), ONT
        pop = _dev("popP", DeviceType.POP)
        core = _dev("coreA", DeviceType.CORE_ROUTER)
        olt = _dev("oltA", DeviceType.OLT)
        olt.parent_container_id = pop.id
        ont = _dev("ontA", DeviceType.ONT)
        for d in (pop, core, olt, ont):
            s.add(d)
        # interfaces
        for dev in (core, olt, ont):
            s.add(_iface(dev))
        # logical link core<->olt (FIBER) - should NOT be optical by classification
        s.add(_link(core, olt, LinkType.FIBER))
        # separate optical segment olt<->ont
        s.add(_link(olt, ont, LinkType.FIBER))
        s.commit()
        provision_device(s, core)
        provision_device(s, olt)
        provision_device(s, ont)
        assert ont.provisioned is True


def test_positive_path_aon_cpe_via_aon_switch_to_core():
    enable_flag()
    with Session(engine) as s:
        pop = _dev("popQ", DeviceType.POP)
        core = _dev("coreB", DeviceType.CORE_ROUTER)
        sw = _dev("swA", DeviceType.AON_SWITCH)
        sw.parent_container_id = pop.id
        cpe = _dev("cpeA", DeviceType.AON_CPE)
        for d in (pop, core, sw, cpe):
            s.add(d)
        for dev in (core, sw, cpe):
            s.add(_iface(dev))
        # logical adjacency core<->switch, and switch<->cpe
        s.add(_link(core, sw, LinkType.FIBER))
        s.add(_link(sw, cpe, LinkType.FIBER))
        s.commit()
        provision_device(s, core)
        provision_device(s, sw)
        provision_device(s, cpe)
        assert cpe.provisioned is True


def test_olt_requires_link_to_core_in_strict_mode():
    enable_flag()
    with Session(engine) as s:
        pop = _dev("popR", DeviceType.POP)
        core = _dev("coreC", DeviceType.CORE_ROUTER)
        olt = _dev("oltR", DeviceType.OLT)
        olt.parent_container_id = pop.id
        for d in (pop, core, olt):
            s.add(d)
        for dev in (core, olt):
            s.add(_iface(dev))
        s.commit()
        provision_device(s, core)
        # No link core<->olt present; strict mode must reject
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            provision_device(s, olt)
