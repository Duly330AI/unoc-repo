"""Unit tests for legacy link_rules.classify_link.

Covers L1, L5 positive and L7, L8 negative cases to lift coverage.
"""

from backend.link_rules import classify_link
from backend.models import Device, DeviceType


def _dev(id_: str, t: DeviceType) -> Device:
    return Device(id=id_, name=id_, type=t)


def test_L1_router_router_allowed():
    a = _dev("core1", DeviceType.CORE_ROUTER)
    b = _dev("edge1", DeviceType.EDGE_ROUTER)
    rr = classify_link(a, b)
    assert rr.allowed is True
    assert rr.rule_id == "L1"
    assert rr.link_class == "routed_p2p"


def test_L5_olt_ont_allowed():
    a = _dev("olt1", DeviceType.OLT)
    b = _dev("ont1", DeviceType.ONT)
    rr = classify_link(a, b)
    assert rr.allowed is True
    assert rr.rule_id == "L5"
    assert rr.link_class == "optical_segment"


def test_L7_active_passive_invalid():
    a = _dev("core1", DeviceType.CORE_ROUTER)
    b = _dev("spl1", DeviceType.SPLITTER)
    rr = classify_link(a, b)
    assert rr.allowed is False
    assert rr.rule_id == "L7"
    assert rr.link_class == "mixed_invalid"


def test_L8_ont_ont_invalid():
    a = _dev("ont1", DeviceType.ONT)
    b = _dev("ont2", DeviceType.ONT)
    rr = classify_link(a, b)
    assert rr.allowed is False
    assert rr.rule_id == "L8"
    assert rr.link_class == "peer_invalid"
