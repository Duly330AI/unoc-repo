from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def create(dev_id: str, dev_type: str, parent: str | None = None, status: str = "UP"):
    payload = {"id": dev_id, "name": dev_id, "type": dev_type, "status": status}
    if parent is not None:
        payload["parent_container_id"] = parent
    return client.post("/api/devices", json=payload)


def test_pop_no_parent_allowed():
    r = create("pop1", "POP")
    assert r.status_code == 201, r.text
    r2 = create("pop2", "POP", parent="pop1")
    assert r2.status_code == 400
    assert "must not have a parent" in r2.text


def test_backbone_gateway_no_parent():
    r = create("bb1", "BACKBONE_GATEWAY")
    assert r.status_code == 201
    r2 = create("bb2", "BACKBONE_GATEWAY", parent="bb1")
    assert r2.status_code == 400


def test_olt_requires_pop_parent():
    create("pop1", "POP")
    # Standalone OLT creation is allowed
    r_ok = create("olt1", "OLT")
    assert r_ok.status_code == 201, r_ok.text
    # With POP parent it is allowed
    r = create("olt2", "OLT", parent="pop1")
    assert r.status_code == 201, r.text


def test_aon_switch_requires_pop_parent():
    create("popX", "POP")
    # Standalone AON switch creation is allowed
    r_ok = create("aonagg1", "AON_SWITCH")
    assert r_ok.status_code == 201, r_ok.text
    r = create("aonagg2", "AON_SWITCH", parent="popX")
    assert r.status_code == 201


def test_edge_router_no_parent_required_and_parent_disallowed():
    # Should allow creation without parent
    r_ok = create("edge01", "EDGE_ROUTER")
    assert r_ok.status_code == 201, r_ok.text
    # Supplying a parent (POP) is now allowed
    create("pop1", "POP")
    r_with_parent = create("edge02", "EDGE_ROUTER", parent="pop1")
    assert r_with_parent.status_code == 201


def test_core_router_no_parent():
    r = create("core1", "CORE_ROUTER")
    assert r.status_code == 201
    r2 = create("core2", "CORE_ROUTER", parent="core1")
    assert r2.status_code == 400


def test_passive_inline_optional_parent():
    r1 = create("split1", "SPLITTER")
    assert r1.status_code == 201
    r2 = create("hop1", "HOP")
    assert r2.status_code == 201
    r3 = create("odf1", "ODF")
    assert r3.status_code == 201
    r4 = create("nvt1", "NVT")
    assert r4.status_code == 201


def test_ont_must_not_parent_pop():
    create("pop1", "POP")
    r_bad = create("ont1", "ONT", parent="pop1")
    assert r_bad.status_code == 400
    # ONT without parent ok
    r_ok = create("ont2", "ONT")
    assert r_ok.status_code == 201


def test_aon_cpe_parent_rules():
    create("pop1b", "POP")
    r_bad = create("aoncpe1", "AON_CPE", parent="pop1b")
    assert r_bad.status_code == 400
    r_ok = create("aoncpe2", "AON_CPE")
    assert r_ok.status_code == 201


def test_business_ont_parent_rules():
    create("pop1", "POP")
    r_bad = create("bont1", "BUSINESS_ONT", parent="pop1")
    assert r_bad.status_code == 400
    r_ok = create("bont2", "BUSINESS_ONT")
    assert r_ok.status_code == 201
