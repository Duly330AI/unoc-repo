"""Refactor fixtures: ensure non-overlapping prefixes for management roles.

Verifies ensure_ipam_defaults keeps role labels unique and avoids collisions with test-provided prefixes.
"""

from __future__ import annotations

from sqlmodel import select

from backend.db import get_session, init_db
from backend.models import VRF, Prefix
from backend.services.seed_service import ensure_ipam_defaults


def test_ensure_ipam_defaults_non_overlapping():
    init_db()
    with get_session() as s:
        ensure_ipam_defaults(s)
        mgmt = s.exec(select(VRF).where(VRF.name == "mgmt")).first()
        assert mgmt is not None and mgmt.id is not None
        # Insert a custom core_mgmt prefix and re-run seeding; no duplicates should be added
        custom = Prefix(prefix="10.250.123.0/24", vrf_id=mgmt.id, description="core_mgmt")
        s.add(custom)
        s.commit()
        ensure_ipam_defaults(s)
        # Count all core_mgmt prefixes in mgmt VRF -> should be exactly 1
        rows = s.exec(
            select(Prefix).where((Prefix.vrf_id == mgmt.id) & (Prefix.description == "core_mgmt"))
        ).all()
        assert len(rows) == 1
