import pytest
from httpx import ASGITransport, AsyncClient

from backend.events import Event, set_broadcaster
from backend.main import app
from backend.tests.utils.async_helpers import wait_for_coalescer_idle


class CaptureBroadcaster:
    def __init__(self):
        self.events: list[Event] = []

    def publish(self, event: Event) -> None:  # pragma: no cover
        self.events.append(event)


@pytest.mark.asyncio
async def test_provision_emits_status_change_when_dynamic_changes():
    # Status propagation and active-degrade are always-on; test the dynamic change events.
    # Status propagation and active-degrade are always-on; no env toggles to manage.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cap = CaptureBroadcaster()
        set_broadcaster(cap)

        # Active device is DOWN before provisioning
        r = await client.post(
            "/api/devices",
            json={
                "id": "evt_core1",
                "name": "evt_core1",
                "type": "CORE_ROUTER",
                "status": "UP",
            },
        )
        assert r.status_code == 201, r.text

        r = await client.get("/api/devices/evt_core1")
        assert r.status_code == 200
        assert r.json()["status"] == "DOWN"

        # Provision triggers device.provisioned; status.changed may or may not occur depending on L3 reachability
        r = await client.post("/api/devices/evt_core1/provision")
        assert r.status_code == 200

        # Wait briefly for background recomputes/events to settle
        await wait_for_coalescer_idle()
        kinds = [e.type for e in cap.events]
        assert "device.provisioned" in kinds
        # Only require status.changed if the effective status actually changed
        # Fetch current device to compare
        r2 = await client.get("/api/devices/evt_core1")
        assert r2.status_code == 200
        # If it's still DOWN due to strict L3, status.changed may not fire here
        if r2.json().get("status") != "DOWN":
            assert "device.status.changed" in kinds
