"""Link type classification constants.

Wraps essential sets & keeps RULES for external classification service.
Extraction from existing `backend/link_rules.py` (which will be slimmed later).
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
class LinkRule:
    rule_id: str
    allowed: bool
    link_class: str
    matcher: Callable[[Device, Device], bool]


# Matcher functions (pure)
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


LINK_TYPE_RULES: list[LinkRule] = [
    LinkRule("L1", True, "routed_p2p", _match_router_router),
    LinkRule("L2", True, "optical_segment", _match_olt_passive),
    LinkRule("L3", True, "optical_segment", _match_passive_passive),
    LinkRule("L4", True, "optical_termination", _match_passive_ont),
    LinkRule("L5", True, "optical_segment", _match_olt_ont_direct),
    LinkRule("L6A", True, "access_uplink", _match_aon_switch_router),
    # New in r7: OLT uplink to routed layer (visual/logical representation; non-optical)
    LinkRule("L6B", True, "access_uplink", _match_olt_router),
    LinkRule("L6", True, "access_edge", _match_aon_switch_cpe),
    LinkRule("L7", False, "mixed_invalid", _match_active_passive_invalid),
    LinkRule("L8", False, "peer_invalid", _match_ont_ont_invalid),
]
