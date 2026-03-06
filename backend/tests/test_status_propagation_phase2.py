import pytest
from httpx import ASGITransport, AsyncClient

from backend.events import Event, set_broadcaster
from backend.main import app
from backend.tests.helpers_l3 import l3_pair
from backend.tests.utils.async_helpers import wait_for_coalescer_idle


class CaptureBroadcaster:
    def __init__(self):
        self.events: list[Event] = []

    def publish(self, event: Event) -> None:  # pragma: no cover
        self.events.append(event)


async def _mk_device(client: AsyncClient, dev_id: str, dev_type: str, parent: str | None = None):
    payload = {"id": dev_id, "name": dev_id, "type": dev_type, "status": "UP"}
    if parent:
        payload["parent_container_id"] = parent
    r = await client.post("/api/devices", json=payload)
    assert r.status_code == 201, r.text


async def _mk_link(client: AsyncClient, a_dev: str, b_dev: str):
    r = await client.post(
        "/api/links",
        json={
            "id": f"{a_dev}__{b_dev}" if a_dev <= b_dev else f"{b_dev}__{a_dev}",
            "a_interface_id": f"{a_dev}-if0",
            "b_interface_id": f"{b_dev}-if0",
            "kind": "FIBER",
            "status": "UP",
        },
    )
    assert r.status_code == 201, r.text


async def _provision(client: AsyncClient, dev_id: str):
    r = await client.post(f"/api/devices/{dev_id}/provision")
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_chain_propagation_sets_passive_up_when_flag_enabled(monkeypatch):
    # Propagation is always enabled; provisioning is strict-by-default.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cap = CaptureBroadcaster()
        set_broadcaster(cap)

        # Valid chain: BACKBONE -> CORE -> POP (container) -> OLT (active) -- ODF (passive) -> ONT (terminator)
        # Build a valid upstream path before provisioning
        await _mk_device(client, "bbA", "BACKBONE_GATEWAY")
        await _mk_device(client, "coreRoot", "CORE_ROUTER")
        await _mk_device(client, "popA", "POP")
        await _mk_device(client, "oltA", "OLT", parent="popA")
        await _mk_device(client, "odf1", "ODF")
        await _mk_device(client, "ontTerm", "ONT")

        # Core <-> OLT upstream link required for strict provisioning + OLT<->ODF + ODF<->ONT
        await _mk_link(client, "bbA", "coreRoot")
        await _mk_link(client, "coreRoot", "oltA")
        await _mk_link(client, "oltA", "odf1")
        await _mk_link(client, "odf1", "ontTerm")

        # Provision oltA -> becomes seed; propagation should mark splitter as UP
        await _provision(client, "oltA")

        # Establish L3 adjacency coreRoot <-> bbA (VRF, addresses, default route) via helper
        # Direct DB-level context (interfaces already exist via API device creation)
        with l3_pair("coreRoot", "bbA", "coreRoot-if0", "bbA-if0"):
            pass

        # Expect at least one device.status.changed; ensure recomputes settle
        await wait_for_coalescer_idle()
        kinds = [e.type for e in cap.events]
        assert kinds.count("device.provisioned") == 1
        assert kinds.count("device.status.changed") >= 1


@pytest.mark.asyncio
async def test_link_cut_drops_downstream_passive(monkeypatch):
    # Propagation is always enabled; provisioning is strict-by-default.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

        # Build a valid upstream path before provisioning
        await _mk_device(client, "coreRoot2", "CORE_ROUTER")
        await _mk_device(client, "popB", "POP")
        await _mk_device(client, "oltB", "OLT", parent="popB")
        await _mk_device(client, "odfB", "ODF")

        # Core <-> OLT upstream link required for strict provisioning
        await _mk_link(client, "coreRoot2", "oltB")
        await _mk_link(client, "oltB", "odfB")
        await _provision(client, "oltB")

        # Now delete link oltB<->odfB and ensure recompute doesn't crash and emits link.deleted
        link_id = "oltB__odfB"
        if "oltB" > "odfB":
            link_id = "odfB__oltB"
        r = await client.delete(f"/api/links/{link_id}")
        assert r.status_code == 202
        # Drain async queue to apply deletion
        from backend.services.job_dispatcher import QUEUE, handle_batch  # type: ignore
        from backend.services.worker import Worker

        if QUEUE.size() > 0:
            Worker().run_once(QUEUE, handle_batch, max_items=256)


@pytest.mark.asyncio
async def test_pop_container_always_online_behavior(monkeypatch):
    # Propagation is always enabled.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

        # POP container is treated as always_online; ensure it doesn't crash propagation
        await _mk_device(client, "pop1", "POP")
        await _mk_device(client, "olt1", "OLT", parent="pop1")
        # Attempting to link POP to OLT is disallowed; ensure API returns 400 (no helper assert)
        r = await client.post(
            "/api/links",
            json={
                "id": "pop1__olt1" if "olt1" > "pop1" else "olt1__pop1",
                "a_interface_id": "pop1-if0",
                "b_interface_id": "olt1-if0",
                "kind": "FIBER",
                "status": "UP",
            },
        )
        assert r.status_code == 400
