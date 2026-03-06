"""
Integration test for backbone gateway seeding.

Tests ensure_backbone_gateway() creates BACKBONE_GATEWAY device when enabled.
Validates idempotence (no duplicates on multiple calls) and flag control.

REQUIRES: PostgreSQL (uses session fixture from conftest)
"""

import pytest
from sqlmodel import select

from backend.models import Device, DeviceType
from backend.services.seed_service import BACKBONE_GATEWAY_ID, ensure_backbone_gateway

pytestmark = pytest.mark.integration  # Mark entire module as integration test


def test_seed_creates_backbone_gateway_when_absent(monkeypatch, session):
    monkeypatch.setenv("ENSURE_SINGLE_BACKBONE_GATEWAY", "true")
    created = ensure_backbone_gateway(session)
    assert created is not None
    fetched = session.get(Device, BACKBONE_GATEWAY_ID)
    assert fetched is not None
    assert fetched.type == DeviceType.BACKBONE_GATEWAY


def test_seed_idempotent(monkeypatch, session):
    monkeypatch.setenv("ENSURE_SINGLE_BACKBONE_GATEWAY", "true")
    pre = session.exec(select(Device).where(Device.type == DeviceType.BACKBONE_GATEWAY)).all()
    ensure_backbone_gateway(session)
    ensure_backbone_gateway(session)
    post = session.exec(select(Device).where(Device.type == DeviceType.BACKBONE_GATEWAY)).all()
    assert len(post) - len(pre) == 1
    # Second invocation MUST NOT create an additional device
    assert len({d.id for d in post}) == 1


def test_seed_skipped_when_flag_disabled(monkeypatch, session):
    monkeypatch.setenv("ENSURE_SINGLE_BACKBONE_GATEWAY", "false")
    created = ensure_backbone_gateway(session)
    assert created is None
    existing = session.exec(select(Device).where(Device.type == DeviceType.BACKBONE_GATEWAY)).all()
    assert existing == []
