from time import sleep

from fastapi.testclient import TestClient

from backend.api.endpoints import ws as ws_mod
from backend.events import BROADCASTER, Event
from backend.main import app


def drain_outbox():
    while not ws_mod._outbox.empty():
        ws_mod._outbox.get()


def test_outbox_backpressure_coalesces_and_drops_oldest():
    # Use a tiny queue to make behavior deterministic
    ws_mod._outbox = ws_mod.BoundedCoalescingQueue(3)
    drain_outbox()

    # Fill queue with: dev a status, link created (non-coalescing), dev b status
    BROADCASTER.publish(Event(type="device.status.changed", payload={"id": "a", "status": "DOWN"}))
    BROADCASTER.publish(Event(type="link.created", payload={"id": "l1"}))
    BROADCASTER.publish(Event(type="device.status.changed", payload={"id": "b", "status": "UP"}))

    assert ws_mod._outbox.qsize() == 3

    # Push another update for dev a -> should coalesce (replace prior 'a' message), size stays 3
    BROADCASTER.publish(Event(type="device.status.changed", payload={"id": "a", "status": "UP"}))
    assert ws_mod._outbox.qsize() == 3

    # Push a new dev c status -> no coalesce key present, drop oldest and append 'c'
    BROADCASTER.publish(Event(type="device.status.changed", payload={"id": "c", "status": "UP"}))
    assert ws_mod._outbox.qsize() == 3

    drained = []
    while not ws_mod._outbox.empty():
        m = ws_mod._outbox.get()
        if not m:
            continue
        payload = m.get("payload") or {}
        drained.append((m.get("type"), payload.get("id")))

    # After coalescing and drop-oldest, only link, b, c remain; 'a' got dropped when c arrived
    ids = [i for (_, i) in drained]
    assert "a" not in ids
    assert "b" in ids
    assert "c" in ids
    assert ("link.created", "l1") in drained


def test_heartbeat_sends_ping_and_prunes_without_pong(monkeypatch):
    client = TestClient(app)
    drain_outbox()

    # Speed up heartbeat for the test
    monkeypatch.setattr(ws_mod, "_HEARTBEAT_INTERVAL_SEC", 0.05, raising=False)
    monkeypatch.setattr(ws_mod, "_HEARTBEAT_TIMEOUT_SEC", 0.1, raising=False)

    with client.websocket_connect("/api/ws") as ws:
        # Give heartbeat loop time to emit a ping
        sleep(0.08)
        data = ws.receive_json()
        assert data["type"] == "__ping__"
        # Don't respond with pong; allow timeout to elapse and connection to be closed
        sleep(0.12)
        # Server should prune connection; verify by checking server-side set becomes empty
        from backend.api.endpoints.ws import connections

        assert len(connections) == 0


def test_heartbeat_keeps_connection_alive_with_pong(monkeypatch):
    client = TestClient(app)
    drain_outbox()

    monkeypatch.setattr(ws_mod, "_HEARTBEAT_INTERVAL_SEC", 0.05, raising=False)
    monkeypatch.setattr(ws_mod, "_HEARTBEAT_TIMEOUT_SEC", 0.1, raising=False)

    with client.websocket_connect("/api/ws") as ws:
        sleep(0.08)
        # Expect a ping, then reply with legacy text ping (server treats as pong)
        data = ws.receive_json()
        assert data["type"] == "__ping__"
        ws.send_text("ping")
        # Wait past timeout and ensure we're still connected by receiving another ping
        sleep(0.12)
        data2 = ws.receive_json()
        assert data2["type"] == "__ping__"


def test_heartbeat_keeps_connection_alive_with_json_pong(monkeypatch):
    import json

    client = TestClient(app)
    drain_outbox()

    monkeypatch.setattr(ws_mod, "_HEARTBEAT_INTERVAL_SEC", 0.05, raising=False)
    monkeypatch.setattr(ws_mod, "_HEARTBEAT_TIMEOUT_SEC", 0.1, raising=False)

    with client.websocket_connect("/api/ws") as ws:
        # receive a ping
        sleep(0.08)
        _ = ws.receive_json()
        # Send JSON pong
        ws.send_text(json.dumps({"type": "__pong__"}))
        # Past timeout we should still be alive, receiving another ping
        sleep(0.12)
        nxt = ws.receive_json()
        assert nxt["type"] == "__ping__"


def test_broadcast_json_prunes_dead_connections():
    class DeadConn:
        def __init__(self):
            self.closed = False

        def __hash__(self):
            return id(self)

        def __eq__(self, other):
            return self is other

        async def send_json(self, message):  # noqa: ARG002
            raise RuntimeError("boom")

    # Add a dead connection and broadcast -> should be removed
    ws_mod.connections.clear()
    dc = DeadConn()
    ws_mod.connections.add(dc)  # type: ignore[arg-type]
    assert len(ws_mod.connections) == 1
    # Run broadcast_json
    import asyncio

    asyncio.get_event_loop().run_until_complete(ws_mod.broadcast_json({"type": "x"}))
    assert len(ws_mod.connections) == 0


def test_optical_updates_coalesce_when_queue_full():
    # Small queue to observe coalescing behavior for optical updates
    ws_mod._outbox = ws_mod.BoundedCoalescingQueue(2)
    drain_outbox()
    # Two different devices optical updated fill the queue
    BROADCASTER.publish(Event(type="device.optical.updated", payload={"id": "d1"}))
    BROADCASTER.publish(Event(type="device.optical.updated", payload={"id": "d2"}))
    # Another update for d1 should coalesce (replace prior d1), size stays 2
    BROADCASTER.publish(Event(type="device.optical.updated", payload={"id": "d1", "sig": -10}))
    assert ws_mod._outbox.qsize() == 2
    # A non-coalescing message forces drop-oldest, but we just drain and validate contents
    drained = []
    while not ws_mod._outbox.empty():
        m = ws_mod._outbox.get()
        if not m:
            continue
        drained.append(m["payload"]["id"])
    # Both d1 and d2 present; the d1 one should be the latest version (with potential extra keys)
    assert set(drained) == {"d1", "d2"}
