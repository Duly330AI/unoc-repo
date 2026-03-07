"""Provisioning constants & skeleton logic (TASK-050..056).

Derived from ARCHITECTURE.md §§3,4,5,6 (subset – MVP scaffold).

This module intentionally keeps only data structures + very small helper
functions to allow incremental, testable build-out.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TypedDict

from fastapi import HTTPException
from sqlmodel import Session, select

from backend.models import Device, DeviceType, IPPool

# Provisionable device set (Backbone Gateway handled separately by bootstrap)
PROVISIONABLE: set[DeviceType] = {
    DeviceType.CORE_ROUTER,  # core router
    DeviceType.EDGE_ROUTER,  # edge router
    DeviceType.OLT,
    DeviceType.AON_SWITCH,
    DeviceType.ONT,
    DeviceType.BUSINESS_ONT,
    DeviceType.AON_CPE,
}

# Pool mapping (Section 3.11 / 4.1)
POOL_KEY_MAP: dict[DeviceType, str] = {
    DeviceType.CORE_ROUTER: "core_mgmt",
    DeviceType.EDGE_ROUTER: "core_mgmt",  # edge reuses core mgmt for MVP
    DeviceType.OLT: "access_mgmt",
    DeviceType.AON_SWITCH: "access_mgmt",
    DeviceType.ONT: "ont_mgmt",
    DeviceType.BUSINESS_ONT: "ont_mgmt",
    DeviceType.AON_CPE: "cpe_mgmt",
}


class ParentRule(TypedDict, total=False):
    requires_parent: bool
    parent_type: DeviceType | None


DEVICE_PARENT_POOL_MAP: dict[DeviceType, ParentRule] = {
    DeviceType.OLT: {"requires_parent": True, "parent_type": DeviceType.POP},
    DeviceType.AON_SWITCH: {"requires_parent": True, "parent_type": DeviceType.POP},
}


@dataclass(slots=True)
class ProvisionPrereq:
    requires_upstream_core: bool = False
    requires_reachable_olt: bool = False
    requires_reachable_aon_switch: bool = False


PROVISION_MATRIX: dict[DeviceType, ProvisionPrereq] = {
    DeviceType.CORE_ROUTER: ProvisionPrereq(),  # backbone assumed present
    DeviceType.EDGE_ROUTER: ProvisionPrereq(requires_upstream_core=True),
    DeviceType.OLT: ProvisionPrereq(requires_upstream_core=True),
    DeviceType.AON_SWITCH: ProvisionPrereq(requires_upstream_core=True),
    DeviceType.ONT: ProvisionPrereq(requires_reachable_olt=True),
    DeviceType.BUSINESS_ONT: ProvisionPrereq(requires_reachable_olt=True),
    DeviceType.AON_CPE: ProvisionPrereq(requires_reachable_aon_switch=True),
}

# Flags (configurable later via env)
ALLOW_RELAXED_UPSTREAM_CHECK = False
STRICT_ONT_DEPENDENCY = True


def classify_pool(device_type: DeviceType) -> str | None:
    return POOL_KEY_MAP.get(device_type)


def is_provisionable(device_type: DeviceType) -> bool:
    return device_type in PROVISIONABLE


# Pool CIDR definitions (Section 4.1)
POOL_DEFS: dict[str, str] = {
    "core_mgmt": "10.250.0.0/24",
    "access_mgmt": "10.250.4.0/24",
    "ont_mgmt": "10.250.1.0/24",
    "cpe_mgmt": "10.250.3.0/24",
}


def ensure_pool(session: Session, pool_key: str) -> IPPool:
    pool = session.get(IPPool, pool_key)
    if not pool:
        cidr = POOL_DEFS.get(pool_key)
        if not cidr:
            raise HTTPException(status_code=500, detail=f"Unknown pool {pool_key}")
        pool = IPPool(pool_key=pool_key, cidr=cidr, next_index=1)
        session.add(pool)
    return pool


def _dependency_ok(session: Session, device: Device) -> bool:
    prereq = PROVISION_MATRIX.get(device.type)
    if not prereq:
        return True
    if prereq.requires_upstream_core:
        core_exists = session.exec(
            select(Device).where(Device.type == DeviceType.CORE_ROUTER)
        ).first()
        if not core_exists and not ALLOW_RELAXED_UPSTREAM_CHECK:
            return False
    if prereq.requires_reachable_olt:
        olt_exists = session.exec(select(Device).where(Device.type == DeviceType.OLT)).first()
        if not olt_exists and STRICT_ONT_DEPENDENCY:
            return False
    if prereq.requires_reachable_aon_switch:
        aon_exists = session.exec(
            select(Device).where(Device.type == DeviceType.AON_SWITCH)
        ).first()
        if not aon_exists:
            return False
    return True


def provision_device(session: Session, device: Device) -> Device:
    log = logging.getLogger("unoc.provision")
    if not is_provisionable(device.type):
        raise HTTPException(status_code=400, detail="INVALID_PROVISION_PATH")
    if device.provisioned:
        raise HTTPException(status_code=409, detail="ALREADY_PROVISIONED")
    if not _dependency_ok(session, device):
        raise HTTPException(status_code=400, detail="INVALID_PROVISION_PATH")
    pool_key = classify_pool(device.type)
    ip_addr: str | None = None
    if pool_key:
        pool = ensure_pool(session, pool_key)
        try:
            ip_addr = pool.allocate()
        except RuntimeError as _err:
            # Explicit cause helps distinguish handler errors
            raise HTTPException(status_code=409, detail="POOL_EXHAUSTED") from _err
        # Legacy module: mgmt IP handled in services.provisioning_service now
    # Defaults by device type
    if device.type == DeviceType.OLT and device.tx_power_dbm is None:
        device.tx_power_dbm = 5.0
    if (
        device.type in {DeviceType.ONT, DeviceType.BUSINESS_ONT}
        and device.sensitivity_min_dbm is None
    ):
        device.sensitivity_min_dbm = -30.0
    if device.type == DeviceType.SPLITTER and device.insertion_loss_db is None:
        device.insertion_loss_db = 3.5
    if device.type == DeviceType.NVT and device.insertion_loss_db is None:
        device.insertion_loss_db = 0.1
    if device.type in {DeviceType.ODF, DeviceType.HOP} and device.insertion_loss_db is None:
        device.insertion_loss_db = 0.5
    device.provisioned = True
    session.add(device)
    log.info("Provisioned device id=%s type=%s ip=%s", device.id, device.type, ip_addr)
    return device
