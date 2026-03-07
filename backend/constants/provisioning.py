"""Provisioning & IPAM constants (extracted).

Derived from ARCHITECTURE.md §§3 & 4.  No side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from backend.models import DeviceType

# Provisionable device set (Backbone Gateway handled separately by bootstrap)
PROVISIONABLE_TYPES: set[DeviceType] = {
    DeviceType.CORE_ROUTER,
    DeviceType.EDGE_ROUTER,
    DeviceType.OLT,
    DeviceType.AON_SWITCH,
    DeviceType.ONT,
    DeviceType.BUSINESS_ONT,
    DeviceType.AON_CPE,
}

# Pool mapping (Section 3.11 / 4.1)
POOL_KEY_MAP: dict[DeviceType, str] = {
    DeviceType.CORE_ROUTER: "core_mgmt",
    DeviceType.EDGE_ROUTER: "core_mgmt",
    DeviceType.OLT: "access_mgmt",
    DeviceType.AON_SWITCH: "access_mgmt",
    DeviceType.ONT: "ont_mgmt",
    DeviceType.BUSINESS_ONT: "ont_mgmt",
    DeviceType.AON_CPE: "cpe_mgmt",
}


class ParentRule(TypedDict, total=False):
    # If True, a parent container is required to provision; if False, parent is optional.
    requires_parent: bool
    # When a parent is provided (or required), it must be of this DeviceType.
    parent_type: DeviceType | None


DEVICE_PARENT_POOL_MAP: dict[DeviceType, ParentRule] = {
    # Parent is OPTIONAL for OLT/AON_SWITCH; if provided, it must be POP.
    DeviceType.OLT: {"requires_parent": False, "parent_type": DeviceType.POP},
    DeviceType.AON_SWITCH: {"requires_parent": False, "parent_type": DeviceType.POP},
}


@dataclass(slots=True)
class ProvisionPrereq:
    requires_upstream_core: bool = False
    requires_reachable_olt: bool = False
    requires_reachable_aon_switch: bool = False


PROVISION_MATRIX: dict[DeviceType, ProvisionPrereq] = {
    DeviceType.CORE_ROUTER: ProvisionPrereq(),
    DeviceType.EDGE_ROUTER: ProvisionPrereq(requires_upstream_core=True),
    DeviceType.OLT: ProvisionPrereq(requires_upstream_core=True),
    DeviceType.AON_SWITCH: ProvisionPrereq(requires_upstream_core=True),
    DeviceType.ONT: ProvisionPrereq(requires_reachable_olt=True),
    DeviceType.BUSINESS_ONT: ProvisionPrereq(requires_reachable_olt=True),
    DeviceType.AON_CPE: ProvisionPrereq(requires_reachable_aon_switch=True),
}

# Feature flags removed – provisioning is strict-by-default (TASK-603 amnesty).

# Ring Protection flags (Phase M4 TASK-200)
ENABLE_RING_PROTECTION = False
RING_PROTECTION_DETERMINISM = "link_id_lexicographically_highest"
RING_PROTECTION_DEBOUNCE_MS = 200
RING_PROTECTION_RECOVERY_DELAY_MS = 800
RING_PROTECTION_MAX_CYCLE_LENGTH = 64  # safeguard
RING_PROTECTION_MAX_RINGS_TRACKED = 512
RING_PROTECTION_OVERLAP_STRATEGY = "PER_CYCLE"  # or MIN_BLOCK_SET (future)
RING_PROTECTION_IGNORE_PASSIVE_NODES = True

# Pool CIDR definitions (Section 4.1)
POOL_DEFS: dict[str, str] = {
    "core_mgmt": "10.250.0.0/24",
    "access_mgmt": "10.250.4.0/24",
    "ont_mgmt": "10.250.1.0/24",
    "cpe_mgmt": "10.250.3.0/24",
}
