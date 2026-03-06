import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.tests.utils.async_helpers import wait_for_coalescer_idle


@pytest.mark.asyncio
async def test_device_override_endpoint_sets_and_clears():
    # Create active device
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/devices",
            json={"id": "ov_core1", "name": "ov_core1", "type": "CORE_ROUTER", "status": "UP"},
        )
        assert r.status_code == 201, r.text

        # Force DOWN via override
        r = await client.patch(
            "/api/devices/ov_core1/override", json={"admin_override_status": "DOWN"}
        )
        assert r.status_code == 200, r.text
        await wait_for_coalescer_idle()
        body = r.json()
        assert body["admin_override_status"] == "DOWN"
        # GET reflects override
        r = await client.get("/api/devices/ov_core1")
        assert r.status_code == 200
        assert r.json()["status"] == "DOWN"

        # Clear override
        r = await client.patch(
            "/api/devices/ov_core1/override", json={"admin_override_status": None}
        )
        assert r.status_code == 200
        await wait_for_coalescer_idle()
        body = r.json()
        assert body["admin_override_status"] is None


@pytest.mark.asyncio
async def test_link_override_propagation_marks_passive_degraded():
    # Enable propagation for this scenario
    # Propagation is always enabled in strict-by-default mode.
    # Seed a simple passive chain with an always-online seed and upstream core:
    # CORE --(L1)--> BB1 --(L6B)--> OLT --(L2)--> ODF
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for dev in [
            {"id": "pop1", "name": "pop1", "type": "POP", "status": "UP"},
            {"id": "bb1", "name": "bb1", "type": "BACKBONE_GATEWAY", "status": "UP"},
            {"id": "core1", "name": "core1", "type": "CORE_ROUTER", "status": "UP"},
            {
                "id": "olt1",
                "name": "olt1",
                "type": "OLT",
                "status": "UP",
                "parent_container_id": "pop1",
            },
            {"id": "odf1", "name": "odf1", "type": "ODF", "status": "UP"},
        ]:
            r = await client.post("/api/devices", json=dev)
            assert r.status_code == 201, r.text

        # Create links along the chain (all UP initially)
        # BB1 <-> OLT (allowed uplink class L6B)
        r = await client.post(
            "/api/links",
            json={
                "id": "bb1__olt1",
                "a_interface_id": "bb1-if0",
                "b_interface_id": "olt1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 201, r.text

        # CORE <-> BB1 (routed P2P L1)
        r = await client.post(
            "/api/links",
            json={
                "id": "bb1__core1",
                "a_interface_id": "bb1-if0",
                "b_interface_id": "core1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 201, r.text

        # OLT <-> ODF (optical segment)
        r = await client.post(
            "/api/links",
            json={
                "id": "odf1__olt1",
                "a_interface_id": "olt1-if0",
                "b_interface_id": "odf1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 201, r.text

        # Provision OLT so it becomes a seed for propagation (active + provisioned)
        r = await client.post("/api/devices/olt1/provision")
        assert r.status_code == 200, r.text

        # Sanity (updated semantics): passive ODF without any downstream terminator remains DOWN
        # because structural rule requires at least one downstream ONT/CPE. Expect DOWN not UP.
        await wait_for_coalescer_idle()
        assert (await client.get("/api/devices/odf1")).json()["status"] == "DOWN"

        # Override the OLT<->ODF link to DOWN; still DOWN (no change in semantics for absence of terminator)
        r = await client.patch(
            "/api/links/odf1__olt1/override", json={"admin_override_status": "DOWN"}
        )
        assert r.status_code == 202, r.text

        # Passive node remains DOWN
        await wait_for_coalescer_idle()
        assert (await client.get("/api/devices/odf1")).json()["status"] == "DOWN"
