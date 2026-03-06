# 13. REST API Reference (Authoritative)

See the quick map in ARCHITECTURE.md → “What’s where?” for topic overviews, and cross-links in each section below to the relevant LLM chapters.

This document is the single source of truth for the REST API. All paths are relative to `/api`.

Conventions

- Status values are strings: "UP" | "DOWN" | "DEGRADED" | "BLOCKING".
- Enum fields are serialized as plain strings in responses.
- IDs are case-sensitive.

## Devices · see also: 01 Overview & Domain Model, 02 Provisioning Model

- POST /devices

  - Purpose: Create a new device. Auto-assigns default hardware model if enabled; seeds default tariffs for ONT/AON CPE when available.
  - Body (DeviceCreate): { id, name, type, status, parent_container_id?, hardware_model_id? }
  - 201 Response: DeviceOut
  - Errors: 409 Device ID already exists; 422 INVALID_HARDWARE_MODEL; 422 HARDWARE_TYPE_MISMATCH; 400 parent/child invalid

- GET /devices

  - Purpose: List devices; optionally include interfaces
  - Query: include_interfaces=false|true
  - 200: list[DeviceOut]; when include_interfaces=true, each device has interfaces: [{ id, name, mac_address, role, port_role, admin_status }]

- GET /devices/{device_id}

  - 200: DeviceOut (includes fields like parameters.capacity.effective_device_capacity_mbps and parameters.effective_capacity_mbps)
  - 404 Not found

  - Splitter fields (when type == SPLITTER):
    - DeviceOut.parameters.splitter: { ports_total: int, ports_used: int, downstream_onts: int }
    - Semantics:
      - ports_total = OUT port count (default 32)
      - ports_used = number of OUT ports that currently serve ≥1 ONT
      - downstream_onts = unique ONTs reachable downstream of the splitter

- PUT /devices/{device_id}

  - Purpose: Update device fields (hardware model, tariff, optical params, overrides)
  - 200: DeviceOut
  - Errors: 404 Not found; 422 INVALID_HARDWARE_MODEL; 422 HARDWARE_TYPE_MISMATCH; 422 TARIFF_NOT_FOUND; 422 TARIFF_TECH_MISMATCH

- PATCH /devices/{device_id}/override

  - Body: { admin_override_status: "DOWN" | null }
  - 200: DeviceOut; emits device.status.changed where applicable
  - Errors: 404 Not found; 400 Invalid override status

- DELETE /devices/{device_id}

  - 204 No Content
  - Cascades: deletes interfaces, addresses, MAC entries, neighbors, routes, provisioning records, bridge domains; emits link.deleted for each removed link

- GET /devices/{device_id}/mac-table
  - 200: list[{ mac_address, interface_id, bridge_domain_id, type }]

## Interfaces (scoped under device) · see also: 10 Interfaces & Addresses

- GET /devices/{device_id}/interfaces

  - 200: list of interfaces for device

- POST /devices/{device_id}/interfaces
  - 201: create interface (name, optional role/port_role will map from PortProfiles when using catalog)

## Links · see also: 02 Provisioning Model, 04 Signal Budget & Overrides

Note on asynchronous writes (authoritative): Link write operations are asynchronous by default, except for creation. POST /links is synchronous and returns the created resource (201). PATCH /links/{id}/override and DELETE /links/{id} enqueue work and return 202 Accepted with a job identifier. Effects (status recompute, optical updates, deletion) are applied by a deterministic background worker and observable via subsequent GETs or realtime WS events.

- POST /links

  - Body (LinkCreate): { id, a_interface_id, b_interface_id, status, admin_override_status?, physical_medium_id?, length_km? }
  - 201: LinkResolvedOut { id, a_interface_id, b_interface_id, a_device_id, b_device_id, status, effective_status, kind, admin_override_status, length_km, physical_medium_id, rule_id }
  - Errors (selected):
    - 409 Link already exists
    - 400 Interface not found (and auto-create failed)
    - 400 length_km must be >= 0
    - 400 Invalid physical_medium_id
    - 400 Link id not canonical; expected '{canonical_id}'
    - 422 INVALID_LINK_TYPE (rule_id), LINK_INVALID_PAIRING, LINK_INVALID_UPSTREAM, LINK_MULTIPLE_UPSTREAMS
    - POP_LINK_DISALLOWED (via standardized error envelope)
    - Splitter-specific validation errors (LINK_INVALID_UPSTREAM envelope):
      - "Splitter OUT '{out_if.name}' already serves an ONT; over-subscription is not allowed" (attempt to attach a second ONT to the same OUT)
      - "Splitter capacity exhausted: {downstream_onts}/{ports_total} ONTs already connected" (total ONTs would exceed available OUT ports)

- GET /links

  - 200: list[LinkResolvedOut] (rule_id omitted for performance)

- DELETE /links/{link_id}

  - 202 Accepted; returns { accepted: true, job_id: string }; enqueues deletion; completion emits link.deleted and device.optical.updated

- PUT /links/{link_id}

  - 200: LinkResolvedOut (updated)
  - Validates optical fields; emits device.optical.updated and device.status.changed when applicable

- PATCH /links/{link_id}/override
  - Body: { admin_override_status: "DOWN" | null }
  - 202 Accepted; returns { accepted: true, job_id: string }; enqueues override update and schedules recompute

## Ports · see also: 08 Ports

- GET /ports/summary/{device_id}

  - Purpose: Per-interface summaries for a device. TTL-cached, rate-limited.
  - 200: list[InterfaceSummaryOut] with fields: id, name, port_role, effective_status, occupancy, capacity

- GET /ports/summary?ids=dev1&ids=dev2

  - Purpose: Bulk variant; map device_id -> list[InterfaceSummaryOut]
  - Rate limited and capped at MAX_BULK_IDS (100)

- GET /ports/ont-list/{device_id}
  - Purpose: ONT/AON_CPE contained by a container device (e.g., POP, CORE_SITE)
  - 200: list[{ id, name, type }]

## Optical · see also: 04 Signal Budget & Overrides

- GET /optical/fiber-types

  - 200: list[{ id, code, mode, standard, attenuation_db_per_km, ... }]

- GET /physical/allowed-media/by-link/{link_id}
  - Purpose: Suggest allowed physical media given link class and catalog
  - 200: list[{ id, code, description }]

## Metrics & Realtime · see also: 11 Traffic Engine & Congestion, 05 Realtime & UI Model

- GET /metrics/snapshot

  - 200: Traffic Engine v2 snapshot with device/link metrics and congestion flags
  - Related docs: 11. Traffic Engine & Congestion (aggregation, hysteresis); 09. Cockpit Nodes (rendering); 05. Realtime & UI Model (event semantics)

- GET /metrics/runtime

  - 200: runtime stats (tick, pending recomputes)
  - Related docs: 11. Traffic Engine & Congestion (tick cadence)

- GET /metrics/prometheus

  - 200: plaintext Prometheus exposition (dev only)
  - Related docs: 11. Traffic Engine & Congestion (metrics), 12. Testing & Performance Harness (profiling guidance)

- WS /ws
  - Purpose: Real-time deltas; event types include deviceMetricsUpdated, linkMetricsUpdated, segment.congestion.detected/cleared, device.status.changed, link.created/deleted, device.optical.updated
  - Related docs: 05. Realtime & UI Model (delta payloads, ordering), 11. Traffic Engine & Congestion (events)

## IPAM & VRF/Prefix · see also: 03 IPAM & Status

- GET /ipam/pools
- GET /ipam/vrfs
- POST /ipam/vrfs
- DELETE /ipam/vrfs/{vrf_id}
- GET /ipam/prefixes
- POST /ipam/prefixes
- DELETE /ipam/prefixes/{prefix_id}

## Provisioning · see also: 02 Provisioning Model

- POST /devices/{device_id}/provision
  - 200: ProvisionResponse; updates audit records; may seed tariffs for customer devices

## Routing · see also: 03 IPAM & Status (VRF/Prefix), future: 06 Future Extensions

- POST /devices/{device_id}/routing/vrfs/{vrf_id}/routes
- GET /devices/{device_id}/routing/vrfs/{vrf_id}/routes

### Default Route Validations (authoritative)

The API enforces additional validations for default routes (IPv4 0.0.0.0/0 or IPv6 ::/0):

- Required fields: next_hop and interface_id must be provided for default routes.
- Ownership: interface_id must belong to the same device identified by {device_id}.
- Shape: prefix must be a valid default route (0.0.0.0/0 or ::/0); other prefixes are treated as regular static routes.

Error semantics (HTTP 400 with plain detail message):

- "Default route requires next_hop"
- "Default route requires interface_id"
- "Interface does not belong to device"

Examples

- Happy path (create default route)

  Request

  POST /devices/edge1/routing/vrfs/VRF-DEFAULT/routes
  { "prefix": "0.0.0.0/0", "next_hop": "192.0.2.1", "interface_id": "edge1-if0" }

  Response 201 Created
  { "id": "edge1-VRF-DEFAULT-rt0", "device_id": "edge1", "vrf_id": "VRF-DEFAULT", "prefix": "0.0.0.0/0", "next_hop": "192.0.2.1", "interface_id": "edge1-if0" }

- Error: missing next_hop

  Request

  POST /devices/edge1/routing/vrfs/VRF-DEFAULT/routes
  { "prefix": "0.0.0.0/0", "interface_id": "edge1-if0" }

  Response 400 Bad Request
  { "detail": "Default route requires next_hop" }

- Error: interface not owned by device

  Request

  POST /devices/edge1/routing/vrfs/VRF-DEFAULT/routes
  { "prefix": "0.0.0.0/0", "next_hop": "192.0.2.1", "interface_id": "otherdev-if0" }

  Response 400 Bad Request
  { "detail": "Interface does not belong to device" }

## Layout & Topology · see also: 07 Container Model & UI

- GET /layout/positions
- GET /topology/version

## Health & Debug · see also: 12 Testing & Performance Harness

- GET /health
- GET /metadata
- GET /metrics/events
- GET /debug/full-snapshot
- GET /debug/l3-path/{device_id}
  - Purpose: Trace the deterministic L3 next-hop chain from a device to the upstream backbone anchor (for diagnostics and explainability).
  - Requires: UNOC_DEV_FEATURES=1 (dev-only endpoint)
  - 200: { ok: boolean, reason: string|null, chain: string[] }
    - ok: true if a path to the anchor was found; false otherwise
    - reason: categorized failure reason (e.g., "no_default_route", "no_eligible_route", "egress_admin_down"); null when ok=true
    - chain: ordered list of device IDs visited during resolution; on success, first is the queried device and last is a BACKBONE_GATEWAY
  - 404: Not Found (when dev features are disabled or device_id does not exist)
  - Notes:
    - Resolution honors: default-route selection (deterministic tie-breakers), egress interface admin-UP, Neighbor/peer IP mapping, and loop guard.
    - See also: Observability metrics l3*resolver*\* under /metrics/prometheus.
- GET /config

## Tools (feature-flagged) · see also: 06 Future Extensions, 03 IPAM & Status

These endpoints are part of the Terminal Viewer groundwork and are disabled by default. They are exposed only when the environment variable `UNOC_TERMINAL_TOOLS=1` is set for the backend process. When disabled, requests return 404 Not Found.

- POST /tools/ping

  - Purpose: Simulate a basic ICMP ping between two devices using the current logical graph for a plausible path.
  - Requires: `UNOC_TERMINAL_TOOLS=1`
  - Body (PingRequest):
    - { "source_device_id": string, "target_device_id"?: string, "target_ip"?: string }
    - Note: In this scaffold, only `target_device_id` is used to resolve a path. `target_ip` is accepted but not yet resolved.
  - 200 Response (PingResponse): { outcome: "success" | "unreachable", hops: string[], rtt_ms: number|null }
    - outcome: "success" when a path exists between source and target device in the logical graph; otherwise "unreachable".
    - hops: ordered list of device IDs along the path (includes source; includes target on success).
    - rtt_ms: always null in the current scaffold.
  - Errors:
    - 404 Not Found: when feature flag is off; when source or target device does not exist
    - 422 INVALID_REQUEST: missing source or target parameters
  - Example

    Request

    POST /tools/ping
    { "source_device_id": "edge1", "target_device_id": "core1" }

    Response 200 OK
    { "outcome": "success", "hops": ["edge1", "agg1", "core1"], "rtt_ms": null }

- POST /tools/traceroute

  - Purpose: Return the hop-by-hop sequence from source to destination with an upper bound on hops (TTL-like behavior).
  - Requires: `UNOC_TERMINAL_TOOLS=1`
  - Body (TracerouteRequest):
    - { "source_device_id": string, "target_device_id"?: string, "target_ip"?: string, "max_hops"?: number }
    - Defaults: max_hops = 8. In this scaffold, only `target_device_id` is used.
  - 200 Response (TracerouteResponse): { outcome: "reached" | "unreachable" | "ttl_exceeded", hops: TracerouteHop[], final_device_id?: string }
    - TracerouteHop: { hop: number, device_id: string, rtt_ms: number|null, success: boolean }
    - outcome semantics:
      - "reached": final hop equals target_device_id
      - "ttl_exceeded": a path exists but was truncated by max_hops (last hop != target)
      - "unreachable": no path was found
    - rtt_ms: always null in the current scaffold.
  - Errors:
    - 404 Not Found: when feature flag is off; when source or target device does not exist
    - 422 INVALID_REQUEST: missing source or target parameters
  - Example

    Request

    POST /tools/traceroute
    { "source_device_id": "edge1", "target_device_id": "core1", "max_hops": 2 }

    Response 200 OK
    {
    "outcome": "ttl_exceeded",
    "hops": [
    { "hop": 1, "device_id": "edge1", "rtt_ms": null, "success": true },
    { "hop": 2, "device_id": "agg1", "rtt_ms": null, "success": true }
    ],
    "final_device_id": "agg1"
    }

## Error semantics · see also: 05 Realtime & UI Model (error codes)

- Standard FastAPI responses (422 validation errors) plus domain errors from `backend/errors.py` (e.g., POP_LINK_DISALLOWED, INVALID_LINK_TYPE).
- Error shapes are either { detail: string } or structured envelopes for standardized errors (see 05 Realtime & UI Model for examples).
