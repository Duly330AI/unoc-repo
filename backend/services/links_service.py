from __future__ import annotations

import hashlib
import logging

from sqlmodel import Session, select

from backend.link_rules import allowed_media_codes_for_class as _allowed_media_codes_for_class
from backend.link_rules import classify_link as _classify_link
from backend.models import Device, PhysicalMedium
from backend.services.link_classification_service import classify
from backend.services.seed_service import ensure_physical_media

log = logging.getLogger("unoc.links.service")


def canonical_link_id(a_iface_id: str, b_iface_id: str) -> tuple[str, str, str, str]:
    def derive_dev(iface_id: str) -> str:
        return iface_id[:-4] if iface_id.endswith("-if0") else iface_id

    a_id, b_id = (a_iface_id, b_iface_id)
    if a_id > b_id:
        a_id, b_id = b_id, a_id
    dev_a_raw = derive_dev(a_iface_id)
    dev_b_raw = derive_dev(b_iface_id)
    if dev_a_raw <= dev_b_raw:
        canonical_id = f"{dev_a_raw}__{dev_b_raw}"
    else:
        canonical_id = f"{dev_b_raw}__{dev_a_raw}"
    user_order_id = f"{dev_a_raw}__{dev_b_raw}"
    return a_id, b_id, canonical_id, user_order_id


def classify_devices_for_link(a_dev: Device, b_dev: Device):
    """Wrapper to allow stable import from endpoints without cycles."""
    return classify(a_dev, b_dev)


def pick_default_physical_medium_id(
    s: Session, link_id: str, a_dev: Device, b_dev: Device
) -> int | None:
    """Deterministically pick a default PhysicalMedium id for a link if unset.

    - Uses link rules to get allowed media codes for the physical class
    - Ensures canonical PhysicalMedium rows exist, then picks based on a hash of link id
    - Falls back to SMF_G652D if nothing else available
    """
    selected_pm_id: int | None = None
    try:
        cls2 = _classify_link(a_dev, b_dev)
        codes = sorted(list(_allowed_media_codes_for_class(cls2.link_class)))
        if codes:
            ensure_physical_media(s)
            h = int(hashlib.md5(link_id.encode("utf-8")).hexdigest(), 16)
            pick = codes[h % len(codes)]
            pm_row = s.exec(select(PhysicalMedium).where(PhysicalMedium.code == pick)).first()
            if pm_row and pm_row.id is not None:
                selected_pm_id = int(pm_row.id)
    except Exception:
        # non-fatal; continue to fallback
        pass
    if selected_pm_id is None:
        try:
            ensure_physical_media(s)
            pm_row = s.exec(
                select(PhysicalMedium).where(PhysicalMedium.code == "SMF_G652D")
            ).first()
            if pm_row and pm_row.id is not None:
                selected_pm_id = int(pm_row.id)
        except Exception:
            pass
    return selected_pm_id


def derive_default_length_km(s: Session, link_id: str, pm_id: int | None) -> float | None:
    """Return a small deterministic default length when physical medium is set.

    For non-optical media with max_range_km: 80% of max range. For optical: 0.11..2.0 km.
    """
    if pm_id is None:
        return None
    try:
        pm_obj = s.get(PhysicalMedium, int(pm_id))
        if not pm_obj:
            return None
        if pm_obj.kind != "optical" and pm_obj.max_range_km is not None:
            return round(float(pm_obj.max_range_km) * 0.8, 3)
        import hashlib as _hl

        hv = int(_hl.md5((link_id + ":len").encode("utf-8")).hexdigest(), 16)
        frac = (hv % 190) / 100.0
        return round(0.11 + frac, 2)
    except Exception:
        return None
