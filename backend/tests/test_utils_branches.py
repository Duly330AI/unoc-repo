from backend.db import get_session, init_db
from backend.models import Device, DeviceType
from backend.utils import canonical_link_id, ensure_default_interface, validate_parent_child


def test_validate_parent_child_core_edge_and_pop_rules():
    init_db()
    with get_session() as s:
        # POP must not have parent
        ok, err = validate_parent_child(s, DeviceType.POP, parent_id="x")
    assert not ok and err is not None and "must not have a parent" in err

    # Prepare valid parents
    with get_session() as s:
        s.add(Device(id="p1", name="p1", type=DeviceType.POP))
        s.add(Device(id="cs1", name="cs1", type=DeviceType.CORE_SITE))
        s.commit()
        # CORE_ROUTER: allowed with CORE_SITE parent, rejected with POP
        ok, err = validate_parent_child(s, DeviceType.CORE_ROUTER, parent_id="cs1")
        assert ok and err is None
        ok, err = validate_parent_child(s, DeviceType.CORE_ROUTER, parent_id="p1")
        assert not ok and err is not None and "CORE_ROUTER parent must be CORE_SITE" in err

        # EDGE_ROUTER: optional parent; POP or CORE_SITE are valid
        ok, err = validate_parent_child(s, DeviceType.EDGE_ROUTER, parent_id=None)
        assert ok and err is None
        ok, err = validate_parent_child(s, DeviceType.EDGE_ROUTER, parent_id="p1")
        assert ok and err is None
        ok, err = validate_parent_child(s, DeviceType.EDGE_ROUTER, parent_id="cs1")
        assert ok and err is None


def test_validate_parent_child_olt_and_passive_and_ont_rules():
    init_db()
    with get_session() as s:
        # OLT: parent is optional now; None is accepted
        ok, err = validate_parent_child(s, DeviceType.OLT, parent_id=None)
        assert ok and err is None

        # Create non-POP parent and ensure rejection
        s.add(Device(id="dnp", name="dnp", type=DeviceType.CORE_ROUTER))
        s.add(Device(id="popA", name="popA", type=DeviceType.POP))
        s.commit()
        ok, err = validate_parent_child(s, DeviceType.OLT, parent_id="dnp")
        assert not ok and err is not None and "must be POP" in err
        ok, err = validate_parent_child(s, DeviceType.OLT, parent_id="popA")
        assert ok and err is None

        # Passive with unknown parent is rejected
        ok, err = validate_parent_child(s, DeviceType.SPLITTER, parent_id="missing")
        assert not ok and err is not None and "Parent container not found" in err

        # ONT must not be parented by container (POP/CORE_SITE)
        ok, err = validate_parent_child(s, DeviceType.ONT, parent_id="popA")
        assert (
            not ok
            and err is not None
            and "must not be directly parented by container (POP/CORE_SITE)" in err
        )


def test_ensure_default_interface_and_canonical_link_id():
    init_db()
    with get_session() as s:
        s.add(Device(id="aa", name="aa", type=DeviceType.CORE_ROUTER))
        s.commit()
        iface = ensure_default_interface(s, "aa-if0")
        assert iface is not None and iface.device_id == "aa"

        # canonical id should order endpoints and strip '-if0'
        assert canonical_link_id("bb-if0", "aa-if0") == "aa__bb"
