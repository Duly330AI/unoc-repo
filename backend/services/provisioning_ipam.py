"""Provisioning IPAM helpers.

Contains small, deterministic helpers used by the provisioning orchestrator.

Notes:
- Determinism: scans hosts in stable order from the CIDR; no randomization.
- No implicit commits: all DB writes remain the caller's responsibility.
"""

from __future__ import annotations

import ipaddress

from sqlmodel import Session, select

from backend.models import DeviceType, InterfaceAddress, Prefix


def classify_prefix_role(device_type: DeviceType) -> str | None:
    """Map device type to management prefix role label.

    Mirrors legacy POOL_KEY_MAP semantics using explicit labels.
    """
    return {
        DeviceType.CORE_ROUTER: "core_mgmt",
        DeviceType.EDGE_ROUTER: "core_mgmt",
        DeviceType.OLT: "olt_mgmt",
        DeviceType.AON_SWITCH: "aon_mgmt",
        DeviceType.ONT: "ont_mgmt",
        DeviceType.BUSINESS_ONT: "ont_mgmt",
        DeviceType.AON_CPE: "cpe_mgmt",
    }.get(device_type)


def next_free_ip_in_prefix(session: Session, prefix: Prefix) -> tuple[str, int] | None:
    """Return (ip, prefix_len) for the first free host in the Prefix, else None.

    - Checks uniqueness within the given prefix scope (prefix_id + ip).
    - Does not consider VRF-level uniqueness; caller enforces VRF policy.
    """
    net = ipaddress.ip_network(prefix.prefix)
    for host in net.hosts():
        taken = session.exec(
            select(InterfaceAddress).where(
                (InterfaceAddress.prefix_id == prefix.id) & (InterfaceAddress.ip == str(host))
            )
        ).first()
        if not taken:
            return str(host), net.prefixlen
    return None
