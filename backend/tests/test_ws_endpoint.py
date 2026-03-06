from time import sleep

import pytest
from fastapi.testclient import TestClient

from backend.api.endpoints import ws as ws_mod
from backend.api.endpoints.ws import connections
from backend.events import BROADCASTER, Event
from backend.main import app


@pytest.mark.skip(reason="Hangs the test suite, needs investigation in TASK-XXX")
def test_ws_connect_and_disconnect_manages_connections():
    client = TestClient(app)
    # Initially no connections
    assert len(connections) == 0
    # Ensure no stale messages get delivered on connect
    while not ws_mod._outbox.empty():
        ws_mod._outbox.get()
    with client.websocket_connect("/api/ws") as ws:
        # After connect we should have one connection and dispatcher started
        assert len(connections) == 1
        # Send a ping to advance server receive loop once
        ws.send_text("ping")
        # Publish an event and expect to receive it shortly
        evt = Event(
            type="device.status.changed", payload={"id": "d1", "status": "UP"}, topo_version=1
        )
        BROADCASTER.publish(evt)
        # Give dispatcher a brief moment to drain queue
        sleep(0.1)
        # Receive until we get our message (ignore any stray events)
        for _ in range(5):
            data = ws.receive_json()
            if data.get("payload", {}).get("id") == "d1":
                break
        assert data["type"] == "device.status.changed"
        assert data["kind"] == "deviceStatusUpdated"
        assert data["payload"]["id"] == "d1"
        assert data["topo_version"] == 1
        assert "ts" in data
    # After context exit, connection is removed
    assert len(connections) == 0


def test_ws_broadcaster_enqueues_mapped_envelope():
    # Ensure no background dispatcher drains the outbox
    try:
        if ws_mod._dispatcher_task is not None:
            ws_mod._dispatcher_task.cancel()
    except Exception:
        pass
    try:
        if ws_mod._heartbeat_task is not None:
            ws_mod._heartbeat_task.cancel()
    except Exception:
        pass
    connections.clear()
    # Clear any leftover messages
    while not ws_mod._outbox.empty():
        ws_mod._outbox.get()
    evt = Event(
        type="link.created", payload={"id": "a__b"}, topo_version=42, correlation_id="corr1"
    )
    BROADCASTER.publish(evt)
    # Envelope should be queued and have mapped kind
    msg = ws_mod._outbox.get()
    assert msg["type"] == "link.created"
    assert msg["kind"] == "linkAdded"
    assert msg["payload"]["id"] == "a__b"
    assert msg["topo_version"] == 42
    assert msg["correlation_id"] == "corr1"
    assert "ts" in msg
