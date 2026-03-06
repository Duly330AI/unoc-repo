"""IPAM seeding helpers.

Contains idempotent utilities for creating base VRFs and management prefixes.
Split from seed_service.py to keep the orchestrator thin while preserving
behavior and public API via re-export in seed_service.py.
"""

from __future__ import annotations

from sqlmodel import Session, select

from backend.models import VRF, Prefix


def ensure_ipam_defaults(session: Session) -> None:
    """Ensure base VRFs and management prefixes exist (idempotent).

    - VRFs: "mgmt", "internet"
    - Management prefixes (in VRF "mgmt"):
        core_mgmt -> 10.250.0.0/24
        olt_mgmt  -> 10.250.4.0/24
        ont_mgmt  -> 10.250.1.0/24
        aon_mgmt  -> 10.250.2.0/24
        cpe_mgmt  -> 10.250.3.0/24
        noc_tools -> 10.250.10.0/24

    Safe to call multiple times; no UNIQUE violations will be raised.
    """
    # Ensure VRF: mgmt
    mgmt_vrf = session.exec(select(VRF).where(VRF.name == "mgmt")).first()
    if not mgmt_vrf:
        mgmt_vrf = VRF(name="mgmt")
        session.add(mgmt_vrf)
        session.flush()  # assign id for FK inserts below
    assert mgmt_vrf.id is not None

    # Ensure VRF: internet (placeholder; no default prefixes yet)
    if not session.exec(select(VRF).where(VRF.name == "internet")).first():
        session.add(VRF(name="internet"))

    desired = {
        "core_mgmt": "10.252.0.0/24",  # Core routers: 254 IPs
        "olt_mgmt": "10.251.0.0/24",  # OLT devices: 254 IPs
        "ont_mgmt": "10.250.0.0/16",  # ONT devices: 65,534 IPs (enterprise scale)
        "aon_mgmt": "10.253.0.0/24",  # AON switches: 254 IPs
        "cpe_mgmt": "10.254.0.0/24",  # CPE devices: 254 IPs
        "noc_tools": "10.250.10.0/24",  # NOC tools: 254 IPs
    }

    # Insert or reconcile prefixes per role label deterministically.
    for desc, cidr in desired.items():
        by_desc_all = session.exec(
            select(Prefix).where((Prefix.vrf_id == mgmt_vrf.id) & (Prefix.description == desc))
        ).all()
        if by_desc_all:
            keep = sorted(by_desc_all, key=lambda p: p.id or 0)[0]
            if keep.description != desc:
                keep.description = desc
            for extra in by_desc_all:
                if extra is not keep:
                    session.delete(extra)
            continue
        exists = session.exec(
            select(Prefix).where((Prefix.vrf_id == mgmt_vrf.id) & (Prefix.prefix == cidr))
        ).first()
        if exists:
            if exists.description in (None, ""):
                exists.description = desc
            continue
        session.add(Prefix(prefix=cidr, vrf_id=mgmt_vrf.id, description=desc))

    session.flush()


__all__ = ["ensure_ipam_defaults"]
