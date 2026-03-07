from backend.db import get_session
from backend.models import Device, DeviceType
from backend.utils import canonical_link_id, ensure_default_interface, validate_parent_child


def test_ensure_default_interface_creates_if_missing():
    with get_session() as s:
        s.add(Device(id="d1", name="d1", type=DeviceType.CORE_ROUTER))
        s.commit()
        iface = ensure_default_interface(s, "d1-if0")
        assert iface is not None
        assert iface.id == "d1-if0"
        # second call should return existing
        iface2 = ensure_default_interface(s, "d1-if0")
        assert iface2 is not None
        assert iface2.id == "d1-if0"


def test_canonical_link_id_sorts_and_strips_if0():
    assert canonical_link_id("b-if0", "a-if0") == "a__b", "should sort and strip -if0 suffix"
    assert canonical_link_id("aa", "b-if0") == "aa__b"


def test_validate_parent_child_rules():
    with get_session() as s:
        pop = Device(id="pop1", name="pop1", type=DeviceType.POP)
        core = Device(id="core1", name="core1", type=DeviceType.CORE_ROUTER)
        olt = Device(id="olt1", name="olt1", type=DeviceType.OLT)
        ont = Device(id="ont1", name="ont1", type=DeviceType.ONT)
        s.add(pop)
        s.add(core)
        s.add(olt)
        s.add(ont)
        s.commit()

        ok, err = validate_parent_child(s, DeviceType.POP, None)
        assert ok and err is None
        ok, err = validate_parent_child(s, DeviceType.POP, "pop1")
        assert not ok and "must not have a parent" in str(err)

        ok, err = validate_parent_child(s, DeviceType.CORE_ROUTER, None)
        assert ok
        ok, err = validate_parent_child(s, DeviceType.CORE_ROUTER, "pop1")
        assert not ok and "CORE_ROUTER parent must be CORE_SITE" in str(err)

        # OLT without parent is allowed (optional parent)
        ok, err = validate_parent_child(s, DeviceType.OLT, None)
        assert ok
        ok, err = validate_parent_child(s, DeviceType.OLT, "pop1")
        assert ok

        ok, err = validate_parent_child(s, DeviceType.ONT, "pop1")
        assert not ok and "must not be directly parented by container (POP/CORE_SITE)" in str(err)
        ok, err = validate_parent_child(s, DeviceType.ONT, None)
        assert ok
