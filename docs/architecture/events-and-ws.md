# Events & WebSocket

This file summarizes the server → client realtime channel and its determinism guarantees. For API shapes and UI consumption see `/docs/llm/05_realtime_and_ui_model.md`.

## Event types (selection)

- link.created / link.deleted
- device.status.changed / device.override.changed
- device.optical.updated
- device.provisioned

All deltas carry a topology_version (monotonic per-process) so clients can reconcile ordering and detect gaps.

## Outbox and dispatcher

- Bounded, coalescing outbox: the server maps internal envelopes into a bounded queue. Duplicate keys within a tick are coalesced to the latest value to avoid redundant fanout.
- Dispatcher preserves queue with zero clients: when no WS clients are connected the queue is not dropped; newly connected clients receive the next deltas normally. Clients must reconcile against a snapshot if they suspect gaps.

## Heartbeat & hello

- Delayed initial heartbeat: the server waits briefly before the first ping to avoid racing client init. Subsequent pings follow a fixed cadence.
- Optional hello on connect: when `WS_SEND_HELLO_ON_CONNECT=1`, the server emits an initial hello payload after the socket opens to provide a deterministic starting point for tests and clients.

## Ping/pong semantics

- The server does not send unsolicited pong in response to a plain ping outside the heartbeat loop. Clients should treat heartbeats as one-way liveness indicators and implement their own timeout/backoff.

## Ordering & reconciliation

- Within a recompute tick, emission order is stable: link/optical updates → deviceSignalUpdated → deviceStatusUpdated → other. This aligns with Determinism (§11) and the recompute coalescer window.
- On version gaps or reconnects, clients perform a snapshot GET to reconcile state. The server’s snapshot endpoint supports ETag/If-None-Match for efficient polling.

Notes:

- The above reflects the current in-process implementation (no external broker). Behavior is deterministic under fixed inputs and timing windows.
