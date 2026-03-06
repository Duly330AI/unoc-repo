"""Link physical viability service (MVP for AON/Ethernet).

Decides if a link is physically viable given its attributes and context.

Rules (MVP):
- Optical ONT paths: defer to optical_service (existing logic elsewhere).
- Ethernet/AON: simple range check using link.length_km against a default threshold.

This service intentionally keeps logic simple; full PhysicalMedium modeling
arrives in TASK-560. Thresholds are configurable via env for flexibility.
"""

from __future__ import annotations

import os

from sqlmodel import Session

from backend.link_rules import allowed_media_codes_for_class, classify_link
from backend.models import Device, DeviceType, Interface, Link, PhysicalMedium


def _get_env_float(name: str, default: float) -> float:
    try:
        raw = os.getenv(name)
        if raw is None:
            return default
        return float(raw)
    except Exception:
        return default


# Defaults for Ethernet ranges (km). Conservative, adjustable.
ETHERNET_MAX_RANGE_KM_DEFAULT = 10.0


def _is_optical_context(session: Session, link: Link) -> bool:
    """Heuristic: treat a link as optical if it directly connects to an ONT/BUSINESS_ONT.

    Later this will be replaced by PhysicalMedium + link kind checks.
    """
    a_if = session.get(Interface, link.a_interface_id)
    b_if = session.get(Interface, link.b_interface_id)
    if not a_if or not b_if:
        return False
    a_dev = session.get(Device, a_if.device_id)
    b_dev = session.get(Device, b_if.device_id)
    if not a_dev or not b_dev:
        return False
    return (a_dev.type in {DeviceType.ONT, DeviceType.BUSINESS_ONT}) or (
        b_dev.type in {DeviceType.ONT, DeviceType.BUSINESS_ONT}
    )


def is_link_physically_viable(session: Session, link: Link) -> bool:
    """Return True if the link is considered physically viable.

    - Optical: for now assume optical viability is handled elsewhere, return True here
      to avoid double decision. (Status propagation may gate ONTs separately.)
    - Ethernet: perform a simple range check using length_km and threshold.
    """
    # If a PhysicalMedium is selected, validate it against link class and range.
    if link.physical_medium_id is not None:
        pm = session.get(PhysicalMedium, link.physical_medium_id)
        if pm is None:
            return False
        # Determine link class from endpoints
        a_if = session.get(Interface, link.a_interface_id)
        b_if = session.get(Interface, link.b_interface_id)
        if not a_if or not b_if:
            return False
        a_dev = session.get(Device, a_if.device_id)
        b_dev = session.get(Device, b_if.device_id)
        if not a_dev or not b_dev:
            return False
        cls = classify_link(a_dev, b_dev)
        allowed = allowed_media_codes_for_class(cls.link_class)
        if pm.code not in allowed:
            return False
        # Range check for non-optical (e.g., copper); optical is informational in this phase
        if pm.kind != "optical" and pm.max_range_km is not None:
            if link.length_km is None:
                return True  # length unknown → do not block
            try:
                return float(link.length_km) <= float(pm.max_range_km)
            except Exception:
                return True
        return True

    # Legacy path (no PhysicalMedium):
    # Optical links: assume viability is managed elsewhere to keep behavior unchanged.
    if _is_optical_context(session, link):
        return True

    # Ethernet/AON generic range check (length_km must not exceed threshold)
    max_km = _get_env_float("AON_ETHERNET_MAX_RANGE_KM", ETHERNET_MAX_RANGE_KM_DEFAULT)
    length = link.length_km
    if length is None:
        # Unknown length → consider viable by default (we don't have enough info)
        return True
    try:
        return float(length) <= float(max_km)
    except Exception:
        return True


__all__ = ["is_link_physically_viable", "ETHERNET_MAX_RANGE_KM_DEFAULT"]
