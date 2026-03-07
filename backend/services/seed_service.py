"""Seed utilities (TASK-052).

Thin orchestration layer that re-exports stable public functions while the
implementations live in logically grouped helpers under
``backend/services/seed_service/`` (ipam.py, catalog.py). This keeps behavior
and public imports stable and improves maintainability.
"""

from __future__ import annotations

import os

from sqlmodel import Session, select

from backend.models import (
    VRF,
    Device,
    DeviceType,
    HardwareModel,
    Interface,
    InterfaceAddress,
    InterfaceRole,
    PhysicalMedium,
    PortProfile,
    Prefix,
    Status,
)
from backend.services.seed_helpers.catalog import (
    ensure_default_hardware_models as _ensure_default_hardware_models_impl,
)
from backend.services.seed_helpers.catalog import (
    ensure_default_tariffs as _ensure_default_tariffs_impl,
)
from backend.services.seed_helpers.ipam import ensure_ipam_defaults as _ensure_ipam_defaults_impl

BACKBONE_GATEWAY_ID = "backbone_gateway"
BACKBONE_GATEWAY_NAME = "Backbone Gateway"


def ensure_ipam_defaults(session: Session) -> None:
    """Shim: delegates to seed_service.ipam.ensure_ipam_defaults."""
    _ensure_ipam_defaults_impl(session)


def ensure_physical_media(session: Session) -> None:
    """Ensure canonical physical media exist (idempotent)."""
    desired: list[tuple[str, str, str, float | None]] = [
        ("SMF_G652D", "Single-mode G.652.D", "optical", None),
        ("SMF_G657A1", "Single-mode G.657.A1", "optical", None),
        ("SMF_G657A2", "Single-mode G.657.A2", "optical", None),
        ("MMF_OM3", "Multi-mode OM3", "optical", None),
        ("MMF_OM4", "Multi-mode OM4", "optical", None),
        ("CAT6A_UTP", "Category 6A UTP", "copper", 0.1),  # 100 meters
    ]
    existing_codes = {pm.code for pm in session.exec(select(PhysicalMedium)).all()}
    for code, name, kind, max_km in desired:
        if code in existing_codes:
            continue
        session.add(PhysicalMedium(code=code, name=name, kind=kind, max_range_km=max_km))
    session.flush()


def allocate_backbone_mgmt(session: Session, device: Device) -> None:
    """Allocate / reconcile backbone management interface & address (prefix-based).

    This replaces older IPPool-based allocation for the backbone gateway when created via
    the devices API. It mirrors the logic used during seeding so both code paths are
    consistent and purely Prefix/VRF driven (no mutable next_index counters).

    Safe + idempotent: if interface and at least one address already exist, it no-ops.
    """
    ensure_ipam_defaults(session)
    # Find mgmt VRF and core_mgmt prefix
    mgmt_vrf = session.exec(select(VRF).where(VRF.name == "mgmt")).first()
    if not mgmt_vrf:
        return
    prefix = session.exec(
        select(Prefix).where((Prefix.vrf_id == mgmt_vrf.id) & (Prefix.description == "core_mgmt"))
    ).first()
    if not prefix:
        return
    # Allocate next IP if mgmt interface is missing or has no address yet
    iface_id = f"{device.id}-mgmt0"
    iface = session.get(Interface, iface_id)
    # Skip if an InterfaceAddress already exists
    if session.exec(
        select(InterfaceAddress).where(InterfaceAddress.interface_id == iface_id)
    ).first():
        return
    if not iface:
        iface = Interface(
            id=iface_id,
            device_id=device.id,
            name="mgmt0",
            role=InterfaceRole.MANAGEMENT,
        )
        session.add(iface)
    else:
        iface.role = InterfaceRole.MANAGEMENT
    # Persist first-free InterfaceAddress within prefix if none exists
    from ipaddress import ip_network

    net = ip_network(prefix.prefix)
    # iterate hosts and pick the first free within this prefix scope
    for host in net.hosts():
        if not session.exec(
            select(InterfaceAddress).where(
                (InterfaceAddress.prefix_id == prefix.id) & (InterfaceAddress.ip == str(host))
            )
        ).first():
            session.add(
                InterfaceAddress(
                    interface_id=iface_id,
                    ip=str(host),
                    prefix_len=net.prefixlen,
                    prefix_id=prefix.id,
                    vrf_id=mgmt_vrf.id,
                )
            )
            break


def ensure_backbone_gateway(session: Session) -> Device | None:
    """Ensure the canonical backbone gateway exists (idempotent).

    Returns the created Device on first creation, else None for subsequent calls.
    Skips seeding if the flag is disabled or if a different BACKBONE_GATEWAY already exists.
    """
    raw_flag = os.getenv("ENSURE_SINGLE_BACKBONE_GATEWAY", "false")
    flag = raw_flag.lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not flag:
        return None
    # Detect any existing backbone gateway (by canonical ID or any BB type row)
    existing = session.get(Device, BACKBONE_GATEWAY_ID)
    if existing is None:
        existing = session.exec(
            select(Device).where(Device.type == DeviceType.BACKBONE_GATEWAY)
        ).first()
    # Debug flags removed (were unused)
    created = False
    if existing is None:
        # Abort if another backbone gateway (different ID) already exists
        # (No need for 'other' check now— we just established none exist)
        existing = Device(
            id=BACKBONE_GATEWAY_ID,
            name=BACKBONE_GATEWAY_NAME,
            type=DeviceType.BACKBONE_GATEWAY,
            status=Status.UP,
            provisioned=True,
        )
        session.add(existing)
        session.flush()
        created = True
        # (debug print removed)
    else:
        # Pre-existing device should NOT be treated as created; return None for idempotency.
        created = False
    # (Former SEED_DEBUG diagnostics removed; kept stub to avoid test churn)

    allow_mgmt = os.getenv("ALLOW_BACKBONE_MGMT_IP", "false").lower() in {"1", "true", "yes", "on"}

    def _pick_router_hardware_model() -> HardwareModel | None:
        try:
            ensure_default_hardware_models(session)
        except Exception:  # pragma: no cover - best effort
            pass
        candidates = session.exec(
            select(HardwareModel).where(
                (HardwareModel.device_type == DeviceType.BACKBONE_GATEWAY)
                | (HardwareModel.device_type == DeviceType.CORE_ROUTER)
                | (HardwareModel.device_type == DeviceType.EDGE_ROUTER)
            )
        ).all()
        if not candidates:
            return None
        # Preference order
        for dtype in (DeviceType.BACKBONE_GATEWAY, DeviceType.CORE_ROUTER, DeviceType.EDGE_ROUTER):
            defaults = [
                hm
                for hm in candidates
                if getattr(hm, "meta_source", None) == "default" and hm.device_type == dtype
            ]
            if defaults:
                return defaults[0]
        any_default = [hm for hm in candidates if getattr(hm, "meta_source", None) == "default"]
        if any_default:
            return any_default[0]
        return candidates[0]

    def _provision_interfaces_from_hardware(dev: Device, hm: HardwareModel) -> None:  # noqa: C901
        from sqlalchemy.exc import IntegrityError

        from backend.services.mac_allocator import next_mac

        profiles = session.exec(
            select(PortProfile).where(PortProfile.hardware_model_id == hm.id)
        ).all()

        def _alloc_unique_mac() -> str:
            attempt = 0
            while True:
                mac = next_mac()
                if not session.exec(
                    select(Interface.id).where(Interface.mac_address == mac)
                ).first():
                    return mac
                attempt += 1
                if attempt > 10_000:  # safety valve
                    suffix = f"{abs(hash(dev.id)) & 0xFFFFFF:06x}"
                    return f"02:55:4e:{suffix[0:2]}:{suffix[2:4]}:{suffix[4:6]}"

        with session.no_autoflush:
            pending: list[Interface] = []
            for p in profiles:
                count = max(0, int(p.count or 0))
                base = (p.name or "port").strip() or "port"
                # Skip mgmt profile when not allowed
                if (not allow_mgmt) and dev.type == DeviceType.BACKBONE_GATEWAY:
                    legacy_role = (getattr(p, "role", None) or "").lower()
                    if legacy_role == "management" or base.lower().startswith("mgmt"):
                        continue
                if count <= 0:
                    continue
                for idx in range(1, count + 1):
                    if count == 1 and base in {"mgmt0", "if0", "mgmt", "uplink"}:
                        if_name = base if base.endswith("0") else f"{base}0"
                    else:
                        if_name = f"{base}{idx}"
                    iface_id = f"{dev.id}-{if_name}"
                    if session.get(Interface, iface_id):  # already exists
                        continue
                    pending.append(
                        Interface(
                            id=iface_id,
                            device_id=dev.id,
                            name=if_name,
                            role=(
                                InterfaceRole.MANAGEMENT
                                if (getattr(p, "role", None) or "").lower() == "management"
                                else None
                            ),
                            capacity=(
                                int(p.speed_gbps * 1000) if p.speed_gbps is not None else None
                            ),
                            profile_name=base,
                            port_role=getattr(p, "port_role", None),
                            mac_address=_alloc_unique_mac(),
                        )
                    )
            if not pending:
                return
            session.add_all(pending)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                for i in pending:
                    if session.get(Interface, i.id):
                        continue
                    try:
                        i.mac_address = _alloc_unique_mac()
                    except Exception:
                        from backend.services.mac_allocator import next_mac as _nm

                        i.mac_address = _nm()
                    session.add(i)
                    try:
                        session.flush()
                    except IntegrityError:
                        session.rollback()
                        continue

    # Management interface reconcile
    if allow_mgmt:
        allocate_backbone_mgmt(session, existing)
    else:
        mgmt_id = f"{existing.id}-mgmt0"
        mgmt = session.get(Interface, mgmt_id)
        if mgmt:
            from backend.models import InterfaceAddress

            addrs = session.exec(
                select(InterfaceAddress).where(InterfaceAddress.interface_id == mgmt_id)
            ).all()
            for a in addrs:
                session.delete(a)
            session.delete(mgmt)

    # Hardware / interface reconcile
    if getattr(existing, "hardware_model_id", None) is None:
        hm = _pick_router_hardware_model()
        if hm and hm.id is not None:
            existing.hardware_model_id = int(hm.id)
            session.add(existing)
            session.flush()
            _provision_interfaces_from_hardware(existing, hm)
    else:
        hm_row = session.get(HardwareModel, existing.hardware_model_id)
        if hm_row:
            _provision_interfaces_from_hardware(existing, hm_row)

    if allow_mgmt:
        allocate_backbone_mgmt(
            session, existing
        )  # ensure mgmt interface after interface provisioning

    # Capture return value BEFORE commit side-effects just in case further logic mutates 'created'
    ret = existing if created else None
    session.commit()
    # (post-commit backbone debug removed)
    return ret


__all__ = ["ensure_backbone_gateway", "BACKBONE_GATEWAY_ID", "allocate_backbone_mgmt"]


# TASK-407: Default Tariffs (idempotent)
def ensure_default_tariffs(session: Session) -> None:
    """Shim: delegates to seed_service.catalog.ensure_default_tariffs."""
    _ensure_default_tariffs_impl(session)


__all__.append("ensure_default_tariffs")


# TASK-522: Default Hardware Catalog (idempotent)
def ensure_default_hardware_models(session: Session) -> None:
    """Shim: delegates to seed_service.catalog.ensure_default_hardware_models."""
    _ensure_default_hardware_models_impl(session)


__all__.append("ensure_default_hardware_models")
