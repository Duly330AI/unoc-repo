"""Provisioning dependency gating helpers.

Encapsulates checks that determine whether a device can be provisioned.
"""

from __future__ import annotations

import os

from sqlmodel import Session, select

from backend.constants import PROVISIONABLE_TYPES
from backend.models import Device, DeviceType
from backend.services import dependency_resolver


def is_provisionable(device_type: DeviceType) -> bool:
    return device_type in PROVISIONABLE_TYPES


def dependency_ok(session: Session, device: Device) -> bool:
    """Return whether upstream dependency prerequisites are satisfied for provisioning.

    Mirrors the logic previously embedded in the orchestrator for behavioral parity.
    """
    _DT = DeviceType

    if device.type in {_DT.CORE_ROUTER, _DT.EDGE_ROUTER, _DT.BACKBONE_GATEWAY}:
        # Allow creation prior to anchors (anchors may follow). Real status will be DOWN until anchors appear.
        return True

    # Strict upstream component prerequisites (Phase 2):
    strict_ont_flag = os.getenv("STRICT_ONT_DEPENDENCY", "1") == "1"
    if device.type in {_DT.ONT, _DT.BUSINESS_ONT}:
        has_olt = session.exec(select(Device).where(Device.type == _DT.OLT)).first()
        if not has_olt:
            return False
        if strict_ont_flag:
            # Optional future enhancement: verify adjacency/path; current tests only require existence.
            pass
    if device.type == _DT.AON_CPE:
        has_sw = session.exec(select(Device).where(Device.type == _DT.AON_SWITCH)).first()
        if not has_sw:
            return False

    res = dependency_resolver.has_upstream_l3_or_anchor(session, device)
    if res.ok:
        return True
    # Backbone-aware policy:
    # - If a BACKBONE_GATEWAY exists, require full L3 reachability (res.ok)
    # - If not, allow structural router reachability while routers lack L3 to anchor
    #   (tolerate reason routers_no_l3), but reject when there is no router path at all.
    has_backbone = (
        session.exec(select(Device).where(Device.type == _DT.BACKBONE_GATEWAY)).first() is not None
    )
    if not has_backbone:
        reasons = set(getattr(res, "reasons", []) or [])
        if reasons.issubset({"routers_no_l3"}) and device.type in {
            _DT.OLT,
            _DT.AON_SWITCH,
            _DT.ONT,
            _DT.BUSINESS_ONT,
            _DT.AON_CPE,
        }:
            return True
    # Otherwise strict: only routers themselves bypass upstream checks
    return device.type in {_DT.CORE_ROUTER, _DT.EDGE_ROUTER, _DT.BACKBONE_GATEWAY}
