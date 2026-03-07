# 08 · Ports and Interface Summaries

This document specifies the Ports and Interface summary model used across the app: backend API contracts, UI consumption (port matrices and details panel), occupancy rules, and performance considerations.

---

## 1. Scope & goals

- Provide an authoritative source for how port and interface information is exposed by the backend and consumed by the frontend.
- Define occupancy semantics per role (PON, ACCESS, UPLINK, MANAGEMENT).
- Establish light-polling guidance and server-side caching to keep the UI responsive.

Non-goal: Full CRUD of interfaces/port profiles (covered by catalog/hardware docs).

---

## 2. Concepts and roles

- Interface (a.k.a. port) belongs to a device; has roles and status dimensions.
- InterfaceRole (secondary, legacy UI grouping): MANAGEMENT | P2P_UPLINK | ACCESS
- PortRole (primary classification used by summaries): PON | ACCESS | UPLINK | TRUNK
- Effective status: derived from device/link health; used for UI color mapping.

---

## 3. API contracts

### 3.1 GET /api/ports/summary/{device_id}

Purpose: return per-interface summaries for a device.

Response (minimal, normative fields): list of InterfaceSummaryOut

- id: string (interface id)
- name: string
- port_role: PortRole (ACCESS | UPLINK | PON | TRUNK)
- effective_status: 'UP' | 'DOWN' | 'DEGRADED' | 'BLOCKING'
- occupancy: number
- capacity: number | null

**Notes:**

- For OLT PON ports, occupancy is the number of provisioned ONTs whose resolved optical path terminates on that specific PON interface (honors passive aggregation, e.g., ODF-as-aggregator).
- For ACCESS/UPLINK/TRUNK, occupancy reflects whether an interface is a link endpoint (count of terminating links capped at 1).
- MANAGEMENT is an InterfaceRole (not a PortRole) and is not included in port-based occupancy semantics here.
- **Capacity origin**:
  - PON: Derived from `PortProfile.max_subscribers` via `Interface.profile_name`
  - UPLINK/TRUNK/other: Comes from `Interface.capacity` field, which is populated from hardware model/port profile during device creation/updates
- Capacity, when applicable, is taken from PortProfile.max_subscribers for PON via Interface.profile_name; for other roles, Interface.capacity if set, otherwise null.
  - For non-PON ports, `Interface.capacity` is prefilled from `PortProfile.speed_gbps` at device creation (and on profile-driven updates) and persisted. A dedicated public API to change this per-interface post-creation is not currently provided.

**Caching & invalidation:**

- Server maintains an in-memory TTL cache keyed by (topology_version, device_id) to avoid recomputation under polling (TTL ≈ 2s).
- Concurrency is guarded with per-key locks to prevent "dogpile" effects.

**Rate limiting:**

- Requests are limited to ~10/minute per client for this endpoint (HTTP 429 when exceeded).

### 3.2 GET /api/ports/ont-list/{device_id}

Purpose: auxiliary listing of ONT/AON_CPE devices contained by a given container (e.g., POP or CORE_SITE) for cockpit roll-ups and debugging.

Shape: flat list of items with at least:

- id: string
- name: string
- type: 'ONT' | 'BUSINESS_ONT' | 'AON_CPE'

**Notes:**

- This endpoint complements the summary endpoint; consumers should prefer the summary for UI rendering and use this list for container drill-downs.

### 3.3 GET /api/ports/summary?ids=dev1&ids=dev2

Purpose: bulk variant returning a mapping of device_id → list[InterfaceSummaryOut]. Same semantics as §3.1; unknown devices are skipped.

**Notes:**

- The `ids` query parameter can be repeated; up to a guarded maximum per request.

---

## 4. Occupancy rules (normative)

- OLT PON: occupancy = count of provisioned ONTs whose optical path resolves specifically to that PON interface (respect ODF-as-aggregator model and passive chain).
- AON ACCESS: occupancy indicates whether an access port is in-use (terminates a link); used/total grouping applies in UI.
- UPLINK/TRUNK: considered used when serving as a link endpoint (binary occupancy via link count > 0).
- MANAGEMENT: excluded here; handled via interface-level details, not port summary occupancy.

**Edge cases:**

- Devices with no applicable role return occupancy=0 and may omit capacity.
- Legacy fields are ignored when port_role is present; fall back only if role is missing.
- **Management ports exclusion**: The port summary focuses on data plane/service ports. Management ports represent control plane connectivity and don't contribute to service capacity/occupancy in this model.

---

## 5. UI consumption

- Device Details Panel → Ports section:

  - Fetches `GET /api/ports/summary/{device_id}` on demand; light polling in runtime; disabled in unit tests.
  - Renders grouped lists by role with used/capacity badges and status color chips.

- Cockpits:
  - OLTCockpit: renders a PON matrix from the per-port list; color per effective_status; grey for occupancy=0.
  - AONSwitchCockpit: renders ACCESS matrix; subscribers computed from ACCESS occupancy.
  - Passive/Splitter: The Splitter "[used/total]" badge is sourced from `DeviceOut.parameters.splitter` (not from the ports summary API). See 07_container_model_and_ui.md and 13_api_reference.md.

**Data sourcing:**

- Frontend uses a composable/store to centralize polling and expose a list[InterfaceSummaryOut].
- All coloring relies on the shared color scale mapping (status/occupancy buckets).

**Non-PON device usage**:

- The RouterCockpit does not directly use port summary data
- Instead, it displays "TotCap (Gbps): <current> / <max>" based on metrics and effective device capacity
- For routers with multiple UPLINK ports, port summary data is primarily used in the Details panel's "Ports" section
- A generalized aggregated view for router ports is not currently implemented in the UI

---

## 6. Performance notes

- **Polling cadence** should be conservative (hundreds of ms to seconds) and suspended when the device is not visible/selected.
- **Server-side TTL cache** for `/api/ports/summary` prevents CPU spikes; key = (topology_version, device_id); auto-invalidates on topology change.
- **Cache consistency**: After topology changes (topology_version bump), the optical path resolver cache is cleared. The first request after version bump will recalculate paths using the updated topology.
- **Asynchronous recalculation**: The optical path resolver uses LRU caching, but after topology changes, it rebuilds paths using the latest topology state before storing results in the ports cache.
- **Avoid client BFS** for subscriber counts—use the authoritative backend summaries for determinism and speed.
- **Hot-mutation phases guidance**: During bulk provisioning or frequent topology changes, expect cache misses. The endpoint uses per-key locks to avoid duplicate recomputation and a short TTL to smooth polling. Prefer the bulk variant (`GET /api/ports/summary?ids=…`) and consider reducing polling cadence temporarily.
- **No stale-new-version window**: Because caches are keyed by `(topology_version, device_id)` and resolver caches are invalidated on version bump, the first request under a new version computes fresh results before caching; stale data from the prior version is not stored under the new key.

---

## 7. Testing guidance

Backend:

- Unit test multiple PON ports with ONTs distributed per-port; verify per-interface occupancy.
- Smoke test non-OLT devices and devices without PON ports.

Frontend:

- Stub summary API and assert matrix colors and grouped counts.
- Ensure polling is disabled in tests to avoid flakiness (explicit awaits for async DOM updates).

---

## 8. Error modes

- Unknown device_id → 404.
- Mixed-role or missing-role data should still render; components default to neutral/grey for unknown status and occupancy=0.

---

## 9. Future enhancements

- Virtualization for very large port counts in matrices.
- Extend summaries with per-port traffic metrics (rx/tx Mbps) when available.
- Add ETag or versioned responses to eliminate polling under stable topology.
