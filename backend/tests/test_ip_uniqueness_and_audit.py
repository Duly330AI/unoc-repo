"""TASK-514 tests: VRF-scoped IP uniqueness and provisioning audit records.

Covers:
- UniqueConstraint (vrf_id, ip) enforced across InterfaceAddress.
- Cross-VRF reuse allowed.
- ProvisioningRecord created on successful provisioning with mgmt IP.
"""

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import (
    VRF,
    Device,
    DeviceType,
    Interface,
    InterfaceAddress,
    InterfaceRole,
    Link,
    LinkType,
    Prefix,
    ProvisioningRecord,
)
from backend.services.provisioning_service import provision_device
from backend.services.seed_service import ensure_ipam_defaults


def _mk_dev(s, id: str, type: DeviceType, parent: Device | None = None) -> Device:
    d = Device(id=id, name=id, type=type)
    if parent:
        d.parent_container_id = parent.id
    s.add(d)
    s.commit()
    return d


def test_vrf_scoped_uniqueness_enforced_and_cross_vrf_reuse_allowed():
    init_db()
    with get_session() as s:
        ensure_ipam_defaults(s)
        # Create two VRFs and same /24 prefix in each
        vrf1 = s.exec(select(VRF).where(VRF.name == "mgmt")).first()
        assert vrf1 is not None and vrf1.id is not None
        vrf1_id: int = vrf1.id
        vrf2 = VRF(name="tenant2")
        s.add(vrf2)
        s.flush()
        assert vrf2.id is not None
        vrf2_id: int = vrf2.id
        p1 = Prefix(prefix="10.250.200.0/24", vrf_id=vrf1_id, description="core_mgmt")
        p2 = Prefix(prefix="10.250.200.0/24", vrf_id=vrf2_id, description="core_mgmt")
        s.add(p1)
        s.add(p2)
        s.commit()
        # Allocate same IP in both VRFs on different interfaces → allowed
        a_dev = _mk_dev(s, "coreA", DeviceType.CORE_ROUTER)
        b_dev = _mk_dev(s, "coreB", DeviceType.CORE_ROUTER)
        ia = Interface(
            id="coreA-mgmt0", device_id=a_dev.id, name="mgmt0", role=InterfaceRole.MANAGEMENT
        )
        ib = Interface(
            id="coreB-mgmt0", device_id=b_dev.id, name="mgmt0", role=InterfaceRole.MANAGEMENT
        )
        s.add(ia)
        s.add(ib)
        s.flush()
        # Insert first address in vrf1
        s.add(
            InterfaceAddress(
                interface_id=ia.id,
                ip="10.250.200.10",
                prefix_len=24,
                prefix_id=p1.id,
                vrf_id=vrf1_id,
            )
        )
        s.commit()
        # Insert same IP in vrf2 should be OK
        s.add(
            InterfaceAddress(
                interface_id=ib.id,
                ip="10.250.200.10",
                prefix_len=24,
                prefix_id=p2.id,
                vrf_id=vrf2_id,
            )
        )
        s.commit()
        # But duplicate in same VRF should fail
        dup = InterfaceAddress(
            interface_id=ia.id, ip="10.250.200.10", prefix_len=24, prefix_id=p1.id, vrf_id=vrf1_id
        )
        s.add(dup)
        failed = False
        try:
            s.commit()
        except Exception:
            s.rollback()
            failed = True
        assert failed, "Expected UNIQUE(vrf_id, ip) to enforce uniqueness within VRF"


def test_provisioning_creates_audit_record():
    init_db()
    with get_session() as s:
        ensure_ipam_defaults(s)
        # Minimal dependencies: POP parent for OLT and upstream CORE reachable via a link
        pop = _mk_dev(s, "pop1", DeviceType.POP)
        core = _mk_dev(s, "core1", DeviceType.CORE_ROUTER)
        d = _mk_dev(s, "olt1", DeviceType.OLT)
        d.parent_container_id = pop.id
        s.add(d)
        s.commit()

        # Ensure logical adjacency core<->olt for strict path validation
        s.add(Interface(id=f"{core.id}-if0", device_id=core.id, name="if0"))
        s.add(Interface(id=f"{d.id}-if0", device_id=d.id, name="if0"))
        s.add(
            Link(
                id=f"{core.id}-{d.id}",
                a_interface_id=f"{core.id}-if0",
                b_interface_id=f"{d.id}-if0",
                kind=LinkType.FIBER,
            )
        )
        s.commit()

        # Provision core first, then OLT
        provision_device(s, core)
        out = provision_device(s, d)
        assert out.provisioned is True
        # Verify InterfaceAddress exists and ProvisioningRecord created
        intf_id = f"{d.id}-mgmt0"
        addr = s.exec(
            select(InterfaceAddress).where(InterfaceAddress.interface_id == intf_id)
        ).first()
        assert addr is not None
        rec = s.exec(select(ProvisioningRecord).where(ProvisioningRecord.device_id == d.id)).first()
        assert rec is not None
        assert rec.interface_id == intf_id
        assert rec.ip == addr.ip
        assert rec.prefix_id == addr.prefix_id
