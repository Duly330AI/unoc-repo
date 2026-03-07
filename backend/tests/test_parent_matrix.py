from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    "child_type,parent_type,expected",
    [
        # Containers: must not have parent
        ("POP", None, 201),
        ("POP", "POP", 400),
        ("CORE_SITE", None, 201),
        ("CORE_SITE", "POP", 400),
        # Backbone/Core: optional parent CORE_SITE only
        ("BACKBONE_GATEWAY", None, 201),
        ("BACKBONE_GATEWAY", "CORE_SITE", 201),
        ("BACKBONE_GATEWAY", "POP", 400),
        ("CORE_ROUTER", None, 201),
        ("CORE_ROUTER", "CORE_SITE", 201),
        ("CORE_ROUTER", "POP", 400),
        # Edge Router: optional, POP or CORE_SITE allowed
        ("EDGE_ROUTER", None, 201),
        ("EDGE_ROUTER", "POP", 201),
        ("EDGE_ROUTER", "CORE_SITE", 201),
        # OLT/AON: optional; if parent set, must be POP
        ("OLT", None, 201),
        ("OLT", "POP", 201),
        ("OLT", "CORE_SITE", 400),
        ("AON_SWITCH", None, 201),
        ("AON_SWITCH", "POP", 201),
        ("AON_SWITCH", "CORE_SITE", 400),
        # ONT-family/AON_CPE: must not be parented by containers
        ("ONT", None, 201),
        ("ONT", "POP", 400),
        ("BUSINESS_ONT", None, 201),
        ("BUSINESS_ONT", "POP", 400),
        ("AON_CPE", None, 201),
        ("AON_CPE", "POP", 400),
    ],
)
def test_parent_rules_matrix(child_type: str, parent_type: str | None, expected: int):
    # Ensure containers exist when referenced
    if parent_type == "POP":
        client.post(
            "/api/devices",
            json={"id": "popM", "name": "popM", "type": "POP", "status": "UP"},
        )
        parent_id = "popM"
    elif parent_type == "CORE_SITE":
        client.post(
            "/api/devices",
            json={
                "id": "csM",
                "name": "csM",
                "type": "CORE_SITE",
                "status": "UP",
            },
        )
        parent_id = "csM"
    else:
        parent_id = None

    payload = {
        "id": f"{child_type.lower()}_m_{'none' if parent_id is None else parent_id}",
        "name": "x",
        "type": child_type,
        "status": "UP",
    }
    if parent_id:
        payload["parent_container_id"] = parent_id

    r = client.post("/api/devices", json=payload)
    assert r.status_code == expected, r.text
