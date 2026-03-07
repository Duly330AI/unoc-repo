import time
from time import sleep

from fastapi.testclient import TestClient

from backend.api.endpoints import ws as ws_mod
from backend.events import reset_events, set_broadcaster
from backend.main import app


def test_fanout_to_multiple_clients_on_device_create(monkeypatch):
    # Use fast heartbeat to keep messages flowing and avoid blocking receives
    monkeypatch.setattr(ws_mod, "_HEARTBEAT_INTERVAL_SEC", 0.02, raising=False)
    # Generous timeout to avoid pruning during the short test
    monkeypatch.setattr(ws_mod, "_HEARTBEAT_TIMEOUT_SEC", 5.0, raising=False)
    # Reset ws module state to avoid cross-test interference
    try:
        _dt = getattr(ws_mod, "_dispatcher_task", None)
        if _dt is not None and hasattr(_dt, "cancel"):
            _dt.cancel()
    except Exception:
        pass
    try:
        _ht = getattr(ws_mod, "_heartbeat_task", None)
        if _ht is not None and hasattr(_ht, "cancel"):
            _ht.cancel()
    except Exception:
        pass
    # Force restart of background tasks on next connection
    try:
        ws_mod._dispatcher_task = None  # type: ignore[assignment]
        ws_mod._heartbeat_task = None  # type: ignore[assignment]
    except Exception:
        pass
    ws_mod.connections.clear()
    try:
        ws_mod._last_pong.clear()
    except Exception:
        pass
    while not ws_mod._outbox.empty():
        ws_mod._outbox.get()
    client = TestClient(app)
    # Ensure broadcaster is wired to websocket fanout for this test
    set_broadcaster(ws_mod.WsBroadcaster())
    reset_events()
    # Connect two websocket clients
    with client.websocket_connect("/api/ws") as ws1, client.websocket_connect("/api/ws") as ws2:
        # Ensure background loops are active by observing an initial heartbeat ping
        def wait_for_ping(ws, budget_sec: float = 1.5):
            deadline = time.time() + budget_sec
            while time.time() < deadline:
                msg = ws.receive_json()
                if msg.get("type") == "__ping__":
                    return True
            return False

        assert wait_for_ping(ws1)
        assert wait_for_ping(ws2)
        # Create device, then update status to trigger a device.status.changed event
        r = client.post(
            "/api/devices",
            json={"id": "fan1", "name": "fan1", "type": "CORE_ROUTER", "status": "UP"},
        )
        assert r.status_code == 201
        r2 = client.put("/api/devices/fan1", json={"status": "DOWN"})
        assert r2.status_code == 200
        # Give dispatcher a brief moment
        sleep(0.05)

        def recv_until(ws, predicate, budget_sec: float = 2.5):
            deadline = time.time() + budget_sec
            while time.time() < deadline:
                m = ws.receive_json()
                # Skip heartbeat pings
                if m.get("type") == "__ping__":
                    continue
                if predicate(m):
                    return m
            return None

        # Both clients should receive the status change event (skip any heartbeats)
        got1 = recv_until(ws1, lambda m: m.get("type") == "device.status.changed")
        got2 = recv_until(ws2, lambda m: m.get("type") == "device.status.changed")
        assert got1 is not None and got2 is not None
        assert got1["type"] == got2["type"]
        # payload id should match the created device id for status.changed path
        pid1 = got1.get("payload", {}).get("id")
        pid2 = got2.get("payload", {}).get("id")
        assert pid1 == "fan1"
        assert pid2 == "fan1"


def test_correlation_id_passthrough_on_publish(monkeypatch):
    # Fast heartbeat to keep inbound receive non-blocking via periodic pings
    monkeypatch.setattr(ws_mod, "_HEARTBEAT_INTERVAL_SEC", 0.02, raising=False)
    monkeypatch.setattr(ws_mod, "_HEARTBEAT_TIMEOUT_SEC", 5.0, raising=False)
    # Reset ws module state to avoid cross-test interference
    try:
        _dt = getattr(ws_mod, "_dispatcher_task", None)
        if _dt is not None and hasattr(_dt, "cancel"):
            _dt.cancel()
    except Exception:
        pass
    try:
        _ht = getattr(ws_mod, "_heartbeat_task", None)
        if _ht is not None and hasattr(_ht, "cancel"):
            _ht.cancel()
    except Exception:
        pass
    # Force restart of background tasks on next connection
    try:
        ws_mod._dispatcher_task = None  # type: ignore[assignment]
        ws_mod._heartbeat_task = None  # type: ignore[assignment]
    except Exception:
        pass
    ws_mod.connections.clear()
    try:
        ws_mod._last_pong.clear()
    except Exception:
        pass
    while not ws_mod._outbox.empty():
        ws_mod._outbox.get()
    client = TestClient(app)
    # Ensure broadcaster is wired to websocket fanout for this test
    set_broadcaster(ws_mod.WsBroadcaster())
    # Connect one client
    with client.websocket_connect("/api/ws") as ws:
        # Ensure heartbeat is active
        def wait_for_ping(ws, budget_sec: float = 1.5):
            deadline = time.time() + budget_sec
            while time.time() < deadline:
                msg = ws.receive_json()
                if msg.get("type") == "__ping__":
                    return True
            return False

        assert wait_for_ping(ws)
        # Trigger a known event (device.status.changed) so we can inspect the envelope
        r = client.post(
            "/api/devices",
            json={"id": "c1", "name": "c1", "type": "CORE_ROUTER", "status": "UP"},
        )
        assert r.status_code == 201
        r2 = client.put("/api/devices/c1", json={"status": "DOWN"})
        assert r2.status_code == 200
        sleep(0.05)

        deadline = time.time() + 2.5
        seen = None
        while time.time() < deadline:
            msg = ws.receive_json()
            if msg.get("type") == "__ping__":
                continue
            if msg.get("type") == "device.status.changed":
                seen = msg
                break
        assert seen is not None
        assert "correlation_id" in seen
