"""Helpers to resolve effective parameters from overrides and catalog (TASK-523).

Order: override on Device/Interface -> HardwareModel/PortProfile default -> fallback.
"""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import Device, DeviceType, HardwareModel, Interface, InterfaceRole, PortProfile

# Default device capacity fallbacks (Mbps) per DeviceType
DEFAULT_DEVICE_CAPACITY_MBPS: dict[DeviceType, int] = {
    DeviceType.BACKBONE_GATEWAY: 100_000,  # 100 Gbps
    DeviceType.POP: 10_000,  # 10 Gbps
    DeviceType.CORE_ROUTER: 40_000,  # 40 Gbps
    DeviceType.EDGE_ROUTER: 10_000,  # 10 Gbps
    DeviceType.AON_SWITCH: 10_000,  # 10 Gbps
    DeviceType.OLT: 10_000,  # 10 Gbps aggregate
    DeviceType.ONT: 1_000,  # 1 Gbps typical
    DeviceType.BUSINESS_ONT: 1_000,
    DeviceType.AON_CPE: 1_000,
    # Passive/inline elements: effectively non-bottlenecking
    DeviceType.SPLITTER: 1_000_000,  # 1 Tbps placeholder to avoid false congestion
    DeviceType.HOP: 1_000_000,
    DeviceType.NVT: 1_000_000,
    DeviceType.ODF: 1_000_000,
}


def _get_model(session: Session, device: Device) -> HardwareModel | None:
    if getattr(device, "hardware_model_id", None) is None:
        return None
    return session.get(HardwareModel, device.hardware_model_id)


def get_effective_tx_power_dbm(session: Session, olt: Device) -> float:
    # Override on device wins
    if getattr(olt, "tx_power_dbm", None) is not None:
        return float(olt.tx_power_dbm)  # type: ignore[return-value]
    m = _get_model(session, olt)
    if m and m.tx_power_dbm is not None:
        return float(m.tx_power_dbm)
    return 0.0


def get_effective_sensitivity_dbm(session: Session, ont: Device) -> float:
    if getattr(ont, "sensitivity_min_dbm", None) is not None:
        return float(ont.sensitivity_min_dbm)  # type: ignore[return-value]
    m = _get_model(session, ont)
    if m and m.sensitivity_min_dbm is not None:
        return float(m.sensitivity_min_dbm)
    return -30.0


def get_effective_device_capacity_mbps(session: Session, device: Device) -> int | None:
    cap = getattr(device, "capacity", None)
    if cap is not None:
        return int(cap)
    m = _get_model(session, device)
    if m and m.capacity_gbps is not None:
        return int(float(m.capacity_gbps) * 1000)
    # Fallback to defaults per device type
    try:
        if isinstance(device.type, DeviceType):
            return DEFAULT_DEVICE_CAPACITY_MBPS.get(device.type)
        # type may be raw str in some contexts
        dt = DeviceType(str(device.type))
        return DEFAULT_DEVICE_CAPACITY_MBPS.get(dt)
    except Exception:
        return None


def _base_from_name(name: str) -> str:
    # strip trailing digits to infer base (e.g., uplink2 -> uplink)
    i = len(name)
    while i > 0 and name[i - 1].isdigit():
        i -= 1
    return name[:i] or name


def get_effective_interface_capacity_mbps(session: Session, interface: Interface) -> int | None:
    # Override on Interface wins
    cap = getattr(interface, "capacity", None)
    if cap is not None:
        return int(cap)
    # Try profile_name direct mapping
    profile = None
    if getattr(interface, "profile_name", None):
        profile = session.exec(
            select(PortProfile).where(
                PortProfile.hardware_model_id
                == select(Device.hardware_model_id)
                .where(Device.id == interface.device_id)
                .scalar_subquery(),
                PortProfile.name == interface.profile_name,
            )
        ).first()
    # Fallback: infer base from name and lookup
    if not profile:
        base = _base_from_name(interface.name)
        profile = session.exec(
            select(PortProfile).where(
                PortProfile.hardware_model_id
                == select(Device.hardware_model_id)
                .where(Device.id == interface.device_id)
                .scalar_subquery(),
                PortProfile.name == base,
            )
        ).first()
    if profile and profile.speed_gbps is not None:
        return int(float(profile.speed_gbps) * 1000)
    # Role-based fallback if profile/model is not available
    role = getattr(interface, "role", None)
    if isinstance(role, InterfaceRole):
        if role == InterfaceRole.ACCESS:
            return 1000
        if role == InterfaceRole.P2P_UPLINK:
            return 10_000
        if role == InterfaceRole.MANAGEMENT:
            return 1000
    return None


__all__ = [
    "get_effective_tx_power_dbm",
    "get_effective_sensitivity_dbm",
    "get_effective_device_capacity_mbps",
    "get_effective_interface_capacity_mbps",
]
