from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.tests.helpers_l3 import l3_pair
from backend.tests.utils.async_helpers import wait_for_coalescer_idle


@pytest.mark.asyncio
async def test_status_transitions_down_on_default_route_delete(monkeypatch):
    # Enforce strict L3 gating so device status reflects reachability
    monkeypatch.setenv("UNOC_L3_STATUS_STRICT", "1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a backbone gateway anchor and an edge router (active device)
        r = await client.post(
            "/api/devices",
            json={"id": "coreD", "name": "coreD", "type": "BACKBONE_GATEWAY", "status": "UP"},
        )
        assert r.status_code == 201, r.text

        r = await client.post(
            "/api/devices",
            json={"id": "edgeD", "name": "edgeD", "type": "EDGE_ROUTER", "status": "UP"},
        )
        assert r.status_code == 201, r.text

        # Build L3 adjacency and a default route from edgeD via coreD
        with l3_pair(
            a_device="edgeD",
            b_device="coreD",
            a_iface="edgeD-if0",
            b_iface="coreD-if0",
            vrf_name="mgmt",
            ptp_cidr="172.20.0.0/31",
        ) as (vrf_id, _a_ip, _b_ip):
            # Provision edgeD (active) and verify status becomes UP under strict L3
            r = await client.post("/api/devices/edgeD/provision")
            assert r.status_code == 200, r.text
            await wait_for_coalescer_idle()
            r = await client.get("/api/devices/edgeD")
            assert r.status_code == 200
            assert r.json()["status"] == "UP"

            # Locate the default route id via the list endpoint
            lr = await client.get(f"/api/devices/edgeD/routing/vrfs/{vrf_id}/routes")
            assert lr.status_code == 200, lr.text
            routes = lr.json()
            rid = next((x["id"] for x in routes if x["prefix"] == "0.0.0.0/0"), None)
            assert rid is not None, "Default route not found to delete"

            # Delete the default route and wait for recompute to settle
            dr = await client.delete(f"/api/devices/edgeD/routing/vrfs/{vrf_id}/routes/{rid}")
            assert dr.status_code == 204, dr.text
            await wait_for_coalescer_idle()

            # Strict L3 should now deem the edge router unreachable → DOWN
            r2 = await client.get("/api/devices/edgeD")
            assert r2.status_code == 200
            assert r2.json()["status"] == "DOWN"
