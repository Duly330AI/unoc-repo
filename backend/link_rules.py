"""Link classification rules (TASK-052).

Implements subset of L1-L9 from ARCHITECTURE.md §3.12.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from backend.models import Device, DeviceType

ROUTER_CLASS = {
    DeviceType.BACKBONE_GATEWAY,
    DeviceType.CORE_ROUTER,
    DeviceType.EDGE_ROUTER,
}
PASSIVE_INLINE = {DeviceType.SPLITTER, DeviceType.HOP, DeviceType.NVT, DeviceType.ODF}
ONT_CLASS = {DeviceType.ONT, DeviceType.BUSINESS_ONT}


@dataclass(slots=True)
class LinkRuleResult:
    rule_id: str
    allowed: bool
    link_class: str
    special: str | None = None


@dataclass(slots=True)
class RuleDef:
    rule_id: str
    allowed: bool
    link_class: str
    matcher: Callable[[Device, Device], bool]


def _match_router_router(a: Device, b: Device) -> bool:
    return a.type in ROUTER_CLASS and b.type in ROUTER_CLASS


def _match_olt_passive(a: Device, b: Device) -> bool:
    return (a.type == DeviceType.OLT and b.type in PASSIVE_INLINE) or (
        b.type == DeviceType.OLT and a.type in PASSIVE_INLINE
    )


def _match_passive_passive(a: Device, b: Device) -> bool:
    return a.type in PASSIVE_INLINE and b.type in PASSIVE_INLINE


def _match_passive_ont(a: Device, b: Device) -> bool:
    return (a.type in PASSIVE_INLINE and b.type in ONT_CLASS) or (
        b.type in PASSIVE_INLINE and a.type in ONT_CLASS
    )


def _match_olt_ont_direct(a: Device, b: Device) -> bool:
    return (a.type == DeviceType.OLT and b.type in ONT_CLASS) or (
        b.type == DeviceType.OLT and a.type in ONT_CLASS
    )


def _match_aon_switch_cpe(a: Device, b: Device) -> bool:
    return (a.type == DeviceType.AON_SWITCH and b.type == DeviceType.AON_CPE) or (
        b.type == DeviceType.AON_SWITCH and a.type == DeviceType.AON_CPE
    )


def _match_aon_switch_router(a: Device, b: Device) -> bool:
    return (a.type == DeviceType.AON_SWITCH and b.type in ROUTER_CLASS) or (
        b.type == DeviceType.AON_SWITCH and a.type in ROUTER_CLASS
    )


def _match_olt_router(a: Device, b: Device) -> bool:
    return (a.type == DeviceType.OLT and b.type in ROUTER_CLASS) or (
        b.type == DeviceType.OLT and a.type in ROUTER_CLASS
    )


def _match_active_passive_invalid(a: Device, b: Device) -> bool:
    if (
        a.type in PASSIVE_INLINE
        and b.type in ROUTER_CLASS | {DeviceType.AON_SWITCH, DeviceType.AON_CPE}
    ) or (
        b.type in PASSIVE_INLINE
        and a.type in ROUTER_CLASS | {DeviceType.AON_SWITCH, DeviceType.AON_CPE}
    ):
        return True
    return False


def _match_ont_ont_invalid(a: Device, b: Device) -> bool:
    return a.type in ONT_CLASS and b.type in ONT_CLASS


RULES: list[RuleDef] = [
    RuleDef("L1", True, "routed_p2p", _match_router_router),
    RuleDef("L2", True, "optical_segment", _match_olt_passive),
    RuleDef("L3", True, "optical_segment", _match_passive_passive),
    RuleDef("L4", True, "optical_termination", _match_passive_ont),
    RuleDef("L5", True, "optical_segment", _match_olt_ont_direct),
    RuleDef("L6", True, "access_edge", _match_aon_switch_cpe),
    # New explicit uplink classes for infrastructure links
    RuleDef("L6A", True, "access_uplink_aon", _match_aon_switch_router),
    RuleDef("L6B", True, "access_uplink_olt", _match_olt_router),
    RuleDef("L7", False, "mixed_invalid", _match_active_passive_invalid),
    RuleDef("L8", False, "peer_invalid", _match_ont_ont_invalid),
]


def classify_link(a: Device, b: Device) -> LinkRuleResult:
    for r in RULES:
        if r.matcher(a, b):
            return LinkRuleResult(rule_id=r.rule_id, allowed=r.allowed, link_class=r.link_class)
    return LinkRuleResult(rule_id="L9", allowed=False, link_class="reverse_invalid")


LINK_RULES_INDEX = {r.rule_id: r for r in RULES}


def allowed_media_codes_for_class(link_class: str) -> set[str]:
    """Return allowed PhysicalMedium codes for a given link classification.

    - routed_p2p: SMF-only (backbone/distribution) → {SMF_G652D, SMF_G657A1, SMF_G657A2}
    - optical_segment/optical_termination: fiber only (SMF/MMF)
    - access_edge: copper only
    - access_uplink_olt: SMF-only
    - access_uplink_aon: SMF/MMF/Copper
    """
    if link_class == "routed_p2p":
        return {"SMF_G652D", "SMF_G657A1", "SMF_G657A2"}
    if link_class in {"optical_segment", "optical_termination"}:
        return {"SMF_G652D", "SMF_G657A1", "SMF_G657A2", "MMF_OM3", "MMF_OM4"}
    if link_class == "access_edge":
        return {"CAT6A_UTP"}
    if link_class == "access_uplink_olt":
        return {"SMF_G652D", "SMF_G657A1", "SMF_G657A2"}
    if link_class == "access_uplink_aon":
        return {"SMF_G652D", "SMF_G657A1", "SMF_G657A2", "MMF_OM3", "MMF_OM4", "CAT6A_UTP"}
    return set()


__all__ = [
    "LinkRuleResult",
    "RuleDef",
    "classify_link",
    "LINK_RULES_INDEX",
    "allowed_media_codes_for_class",
]
