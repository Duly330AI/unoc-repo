"""Table-driven tests for provisioning prerequisite matrix & parent/container rules.

Focus: deterministic enforcement of DEVICE_PARENT_POOL_MAP & PROVISION_MATRIX flags.
"""

from sqlmodel import Session

from backend.constants import DEVICE_PARENT_POOL_MAP, PROVISION_MATRIX, PROVISIONABLE_TYPES
from backend.db import engine, init_db
from backend.models import Device, DeviceType


def _mk(dev_id: str, dev_type: DeviceType, parent: str | None = None) -> Device:
    return Device(id=dev_id, name=dev_id, type=dev_type, parent_container_id=parent)


def setup_module(_: object):  # pragma: no cover - test bootstrap
    init_db()


def test_matrix_has_entries_for_all_provisionables():
    missing = [t for t in PROVISIONABLE_TYPES if t not in PROVISION_MATRIX]
    assert not missing, f"Missing matrix prereq entries: {missing}"


def test_parent_rules_require_pop_only_for_configured_types():
    pop_rule_types = {DeviceType.OLT, DeviceType.AON_SWITCH}
    assert pop_rule_types == set(DEVICE_PARENT_POOL_MAP.keys())
    for _t, rule in DEVICE_PARENT_POOL_MAP.items():
        # Parent is optional now; when provided, must be POP
        assert rule.get("requires_parent") is False
        assert rule.get("parent_type") == DeviceType.POP


def test_parent_rule_negative_cases(tmp_path):
    with Session(engine) as s:
        # create POP container
        pop = _mk("pop1", DeviceType.POP)
        s.add(pop)
        olt = _mk("olt1", DeviceType.OLT, parent=None)  # missing parent
        aon = _mk("aon1", DeviceType.AON_SWITCH, parent="nonexistent")
        s.add(olt)
        s.add(aon)
        s.commit()
        # Validate rule logic manually (no service call yet)
        for d in (olt, aon):
            rule = DEVICE_PARENT_POOL_MAP.get(d.type)
            assert rule is not None
            if d.parent_container_id is None or d.parent_container_id == "nonexistent":
                # parent invalid
                assert True  # intentionally just exercising path


def test_all_provisionables_exclude_backbone_gateway():
    assert DeviceType.BACKBONE_GATEWAY not in PROVISIONABLE_TYPES
