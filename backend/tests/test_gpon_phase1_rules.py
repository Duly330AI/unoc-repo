import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.tests.utils.async_helpers import wait_for_coalescer_idle


@pytest.mark.asyncio
async def test_reject_direct_olt_ont_pairing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create POP and parent OLT inside it
        r = await client.post(
            "/api/devices",
            json={"id": "pop1", "name": "pop1", "type": "POP", "status": "UP"},
        )
        assert r.status_code == 201, r.text
        r = await client.post(
            "/api/devices",
            json={
                "id": "olt1",
                "name": "olt1",
                "type": "OLT",
                "status": "UP",
                "parent_container_id": "pop1",
            },
        )
        assert r.status_code == 201, r.text
        r = await client.post(
            "/api/devices",
            json={"id": "ont1", "name": "ont1", "type": "ONT", "status": "UP"},
        )
        assert r.status_code == 201, r.text
        # Attempt to create OLT<->ONT should fail with LINK_INVALID_PAIRING
        r = await client.post(
            "/api/links",
            json={
                "id": "olt1__ont1",
                "a_interface_id": "olt1-if0",
                "b_interface_id": "ont1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 400
        assert "LINK_INVALID_PAIRING" in (r.json().get("detail") or "")


@pytest.mark.asyncio
async def test_require_odf_for_olt_and_ont_upstream():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Seed POP, OLT (inside POP), ONT, and a non-ODF passive (SPLITTER) and ODF
        r = await client.post(
            "/api/devices",
            json={"id": "pop1", "name": "pop1", "type": "POP", "status": "UP"},
        )
        assert r.status_code == 201, r.text
        r = await client.post(
            "/api/devices",
            json={
                "id": "olt1",
                "name": "olt1",
                "type": "OLT",
                "status": "UP",
                "parent_container_id": "pop1",
            },
        )
        assert r.status_code == 201, r.text
        for dev in [
            {"id": "ont1", "name": "ont1", "type": "ONT", "status": "UP"},
            {"id": "sp1", "name": "sp1", "type": "SPLITTER", "status": "UP"},
            {"id": "odf1", "name": "odf1", "type": "ODF", "status": "UP"},
        ]:
            r = await client.post("/api/devices", json=dev)
            assert r.status_code == 201, r.text
        # OLT to SPLITTER should be rejected (must be ODF)
        r = await client.post(
            "/api/links",
            json={
                "id": "olt1__sp1",
                "a_interface_id": "olt1-if0",
                "b_interface_id": "sp1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 400
        msg = r.json().get("detail") or ""
        assert "LINK_INVALID_UPSTREAM" in msg and "not SPLITTER" in msg
        # ONT to SPLITTER should be rejected (must be ODF)
        r = await client.post(
            "/api/links",
            json={
                "id": "ont1__sp1",
                "a_interface_id": "ont1-if0",
                "b_interface_id": "sp1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 400
        msg = r.json().get("detail") or ""
        assert "LINK_INVALID_UPSTREAM" in msg and "not SPLITTER" in msg
        # OLT to ODF accepted
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
        # ONT to ODF accepted
        r = await client.post(
            "/api/links",
            json={
                "id": "odf1__ont1",
                "a_interface_id": "ont1-if0",
                "b_interface_id": "odf1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 201, r.text
        await wait_for_coalescer_idle()


@pytest.mark.asyncio
async def test_single_upstream_enforced_for_odf_and_ont():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Seed POP, two OLTs (inside POP), one ODF, two ONTs
        r = await client.post(
            "/api/devices",
            json={"id": "pop1", "name": "pop1", "type": "POP", "status": "UP"},
        )
        assert r.status_code == 201, r.text
        for dev in [
            {
                "id": "olt1",
                "name": "olt1",
                "type": "OLT",
                "status": "UP",
                "parent_container_id": "pop1",
            },
            {
                "id": "olt2",
                "name": "olt2",
                "type": "OLT",
                "status": "UP",
                "parent_container_id": "pop1",
            },
            {"id": "odf1", "name": "odf1", "type": "ODF", "status": "UP"},
            {"id": "ont1", "name": "ont1", "type": "ONT", "status": "UP"},
            {"id": "ont2", "name": "ont2", "type": "ONT", "status": "UP"},
        ]:
            r = await client.post("/api/devices", json=dev)
            assert r.status_code == 201, r.text
        # First, connect olt1<->odf1 and odf1<->ont1
        for link in [
            {
                "id": "odf1__olt1",
                "a_interface_id": "olt1-if0",
                "b_interface_id": "odf1-if0",
                "status": "UP",
            },
            {
                "id": "odf1__ont1",
                "a_interface_id": "ont1-if0",
                "b_interface_id": "odf1-if0",
                "status": "UP",
            },
        ]:
            r = await client.post("/api/links", json=link)
            assert r.status_code == 201, r.text
        # Try adding a second upstream for ODF (olt2<->odf1) -> reject
        r = await client.post(
            "/api/links",
            json={
                "id": "odf1__olt2",
                "a_interface_id": "olt2-if0",
                "b_interface_id": "odf1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 400
        assert "LINK_MULTIPLE_UPSTREAMS" in (r.json().get("detail") or "")
        # Try adding a second upstream for ONT (odf1<->ont2 then ont2 another odf) -> reject on second
        # First attach ont2 to odf1
        r = await client.post(
            "/api/links",
            json={
                "id": "odf1__ont2",
                "a_interface_id": "ont2-if0",
                "b_interface_id": "odf1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 201, r.text
        # Create a second ODF and attempt to attach ont2 to it as well
        r = await client.post(
            "/api/devices", json={"id": "odf2", "name": "odf2", "type": "ODF", "status": "UP"}
        )
        assert r.status_code == 201, r.text
        r = await client.post(
            "/api/links",
            json={
                "id": "odf2__ont2",
                "a_interface_id": "ont2-if0",
                "b_interface_id": "odf2-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 400
        assert "LINK_MULTIPLE_UPSTREAMS" in (r.json().get("detail") or "")


@pytest.mark.asyncio
async def test_pon_port_required_when_olt_declares_pon():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Seed POP, OLT (inside POP) and ODF
        r = await client.post(
            "/api/devices",
            json={"id": "pop1", "name": "pop1", "type": "POP", "status": "UP"},
        )
        assert r.status_code == 201, r.text
        r = await client.post(
            "/api/devices",
            json={
                "id": "olt1",
                "name": "olt1",
                "type": "OLT",
                "status": "UP",
                "parent_container_id": "pop1",
            },
        )
        assert r.status_code == 201, r.text
        r = await client.post(
            "/api/devices",
            json={"id": "odf1", "name": "odf1", "type": "ODF", "status": "UP"},
        )
        assert r.status_code == 201, r.text
        # Add an extra interface on OLT and mark it as PON, so that rule activates
        r = await client.post(
            "/api/devices/olt1/interfaces", json={"name": "pon0", "port_role": "PON"}
        )
        assert r.status_code == 201, r.text
        # There is no endpoint to set port_role; simulate via device update setting hardware creates PON? If not, directly PATCH is unavailable.
        # Instead, create another interface and rely on default if0 (non-PON) chosen; since olt has a PON port, linking via non-PON should be rejected.
        # Create link via non-PON (olt1-if0) -> expect INVALID_LINK_TYPE PON_PORT_REQUIRED
        r = await client.post(
            "/api/links",
            json={
                "id": "odf1__olt1",
                "a_interface_id": "olt1-if0",
                "b_interface_id": "odf1-if0",
                "status": "UP",
            },
        )
        assert r.status_code == 400
        assert "INVALID_LINK_TYPE PON_PORT_REQUIRED" in (r.json().get("detail") or "")
