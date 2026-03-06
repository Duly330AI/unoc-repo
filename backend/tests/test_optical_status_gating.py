"""
Integration test for optical status gating.

Tests that ONT/AON_CPE devices only become ACTIVE after parent OLT/AON_SWITCH
achieves optical lock. Validates status transitions through UP → PENDING → ACTIVE
based on optical path resolution.

REQUIRES: Optical PathFinder Go service (port 50051) + PostgreSQL
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend import events
from backend.main import app
from backend.tests.helpers_l3 import l3_pair  # upstream L3 adjacency for core/backbone
from backend.tests.utils.async_helpers import wait_for_coalescer_idle

pytestmark = pytest.mark.integration  # Mark entire module as integration test


async def _create_and_provision(
    client: AsyncClient,
    dev_id: str,
    dev_type: str,
    parent: str | None = None,
    provision: bool = True,
) -> None:
    payload: dict = {"id": dev_id, "name": dev_id, "type": dev_type, "status": "DOWN"}
    if parent:
        payload["parent_container_id"] = parent
    r = await client.post("/api/devices", json=payload)
    assert r.status_code == 201, r.text
    # Provision supported device types
    if provision and dev_type in {
        "CORE_ROUTER",
        "EDGE_ROUTER",
        "OLT",
        "AON_SWITCH",
        "ONT",
        "BUSINESS_ONT",
        "AON_CPE",
    }:
        pr = await client.post(f"/api/devices/{dev_id}/provision")
        assert pr.status_code == 200, pr.text


async def _get_device_status(client: AsyncClient, dev_id: str) -> str:
    r = await client.get(f"/api/devices/{dev_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    return body["status"]


@pytest.mark.asyncio
async def test_ont_status_gating_happy_loss_recovery():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Topology setup (strict L3 gating): core1 <-> bb1 (L3) then POP -> OLT -> ODF -> ONT (optical passive chain)
        await _create_and_provision(client, "core1", "CORE_ROUTER")
        await _create_and_provision(client, "bb1", "BACKBONE_GATEWAY")
        # Establish L3 adjacency core1 <-> bb1 (uses dedicated L3 interfaces so core1-if0 remains free for logical access link)
        with l3_pair("core1", "bb1", "core1-ifl3", "bb1-ifl3"):
            pass
        await _create_and_provision(client, "pop1", "POP")
        # Create OLT (defer provision), insert passive ODF (container under POP), ONT (defer provision)
        await _create_and_provision(client, "olt1", "OLT", parent="pop1", provision=False)
        await _create_and_provision(client, "odf1", "ODF", parent="pop1", provision=False)
        await _create_and_provision(client, "ont1", "ONT", provision=False)
        # Logical (fiber) adjacency core1 <-> olt1 (separate from L3 router interfaces) enabling upstream anchor path
        lr_core_olt = await client.post(
            "/api/links",
            json={
                "id": "core1__olt1",
                "a_interface_id": "core1-if0",
                "b_interface_id": "olt1-if0",
                "status": "UP",
                "kind": "FIBER",
            },
        )
        assert lr_core_olt.status_code == 201, lr_core_olt.text
        pr = await client.post("/api/devices/olt1/provision")
        assert pr.status_code == 200, pr.text
        # Create optical passive chain using only auto-created -if0 interfaces:
        # OLT(if0) -> ODF(if0) and ODF(if0) -> ONT(if0) would reuse same ODF iface; instead we introduce a second ODF (odf2)
        # to keep simple without manual interface creation logic.
        await _create_and_provision(client, "odf2", "ODF", parent="pop1", provision=False)
        link_olt_odf1 = "odf1__olt1" if "odf1" < "olt1" else "olt1__odf1"
        r1 = await client.post(
            "/api/links",
            json={
                "id": link_olt_odf1,
                "a_interface_id": "olt1-if0",  # already used in core1 link but permissible multi-link? if not, use odf2 for chain start
                "b_interface_id": "odf1-if0",
                "status": "UP",
                "kind": "FIBER",
                "length_km": 5.0,
                "fiber_type": "SMF_G652D",
            },
        )
        if r1.status_code != 201:
            # Fallback: use second ODF if reuse of olt1-if0 disallowed
            link_olt_odf2 = "odf2__olt1" if "odf2" < "olt1" else "olt1__odf2"
            r1b = await client.post(
                "/api/links",
                json={
                    "id": link_olt_odf2,
                    "a_interface_id": "olt1-if0",
                    "b_interface_id": "odf2-if0",
                    "status": "UP",
                    "kind": "FIBER",
                    "length_km": 5.0,
                    "fiber_type": "SMF_G652D",
                },
            )
            assert r1b.status_code == 201, r1b.text
            chain_mid = "odf2"
        else:
            chain_mid = "odf1"
        link_mid_ont = f"{chain_mid}__ont1" if chain_mid < "ont1" else f"ont1__{chain_mid}"
        r2 = await client.post(
            "/api/links",
            json={
                "id": link_mid_ont,
                "a_interface_id": f"{chain_mid}-if0",
                "b_interface_id": "ont1-if0",
                "status": "UP",
                "kind": "FIBER",
                "length_km": 5.0,
                "fiber_type": "SMF_G652D",
            },
        )
        assert r2.status_code == 201, r2.text
        # Provision ONT now that optical path exists; collapsed optical edge should form ONT<->OLT logical
        pr2 = await client.post("/api/devices/ont1/provision")
        assert pr2.status_code == 200, pr2.text
        await wait_for_coalescer_idle()

        # Case 1: Happy Path -> ONT evaluated status should be UP
        assert await _get_device_status(client, "ont1") == "UP"

        # Case 2: Signal Loss -> force NO_SIGNAL by increasing ODF<->ONT fiber length to very high value
        events.reset_events()
        ur = await client.put(
            f"/api/links/{link_mid_ont}",
            json={
                "length_km": 120.0,  # 120km * 0.35dB/km => 42dB loss => margin < 0
            },
        )
        assert ur.status_code == 200, ur.text
        await wait_for_coalescer_idle()
        # Expect a device.status.changed event for ONT DOWN
        hist = events.get_event_history()
        assert any(
            e.type == "device.status.changed" and e.payload.get("id") == "ont1" for e in hist
        )
        assert await _get_device_status(client, "ont1") == "DOWN"

        # Case 3: Signal Recovery -> restore original length
        events.reset_events()
        ur2 = await client.put(
            f"/api/links/{link_mid_ont}",
            json={
                # Restore to the original per-edge length used at setup (5.0 km)
                # The initial path comprised two 5 km segments (OLT<->ODF, ODF<->ONT).
                # Restoring this ensures the margin returns positive and ONT recovers to UP.
                "length_km": 5.0,
            },
        )
        assert ur2.status_code == 200, ur2.text
        await wait_for_coalescer_idle()
        hist2 = events.get_event_history()
        assert any(
            e.type == "device.status.changed" and e.payload.get("id") == "ont1" for e in hist2
        )
        assert await _get_device_status(client, "ont1") == "UP"
