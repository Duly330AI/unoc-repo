## 1. Overview

UNOC v3 models a fiber / access network topology (FTTH) with active and passive devices, container nodes (POPs & CORE_SITE), links, and optical signal propagation. The backend (FastAPI + SQLModel) is authoritative; the frontend (Vue 3 + TS + D3) renders and incrementally updates a visual topology via WebSocket delta events. Provisioning drives IP allocation (lazy IPAM) and sets the foundation for simulation (status & optical budget). Manual admin overrides exist to force status outcomes for diagnostics.

Guiding Principles:

- API-first & type-synchronized (backend Pydantic/SQLModel → generated TS types).
- Deterministic operations (repeatable IP allocations, interface ordering, status propagation).
- Minimal deltas: never broadcast full topology after initial load.
- Clear separation of concerns (task board isolated from design docs).

### 1.1 Implementation status (r9.4 snapshot)

This snapshot lists what’s implemented now versus planned, with pointers to modules and tests.

- **Packet-level L2/L3 pipeline: implemented (minimal, used as fallback)**
  - Concrete modules exist and are wired: `backend/services/l2_service.py`, `backend/services/l3_service.py`, and `backend/services/forwarding_service.py`.
  - **Fallback Context**: The L2/L3 pipeline is primarily used when no path to an anchor (CORE/BACKBONE/POP) is found via BFS traversal over `is_link_passable` links. TrafficEngine v2 first attempts a simple graph traversal; if no valid path exists, it falls back to the L2/L3 forwarding logic in `backend/services/forwarding_service.py` to synthesize a path. This ensures continuity even in complex routing scenarios.
  - **IPAM /31 p2p Pool**: The `/31` p2p pool for router-to-router links (e.g., Core ↔ Edge) is pending implementation (TASK-027). Currently, these links rely on L2/L3 logic without dedicated IPAM allocation.
  - IPAM (lazy allocation): implemented for management pools.
  - Pools (current roles and defaults): `core_mgmt` (10.250.0.0/24), `olt_mgmt` (10.250.4.0/24), `aon_mgmt` (10.250.2.0/24), `ont_mgmt` (10.250.1.0/24), `cpe_mgmt` (10.250.3.0/24), plus `noc_tools` (10.250.10.0/24 utility space).
  - Deterministic, idempotent allocation at provisioning time; `/31` p2p pool is pending (TASK-027).
- Provisioning model & matrix: implemented (strict‑by‑default)
  - Parent/POP invariants and upstream dependency checks (STRICT only; relaxed mode removed). See `backend/services/provisioning_service.py` and `backend/services/dependency_resolver.py`.
  - Optical recompute hook emits placeholder events on relevant mutations.
- Link type rules: implemented including L6A (AON↔Router) and L6B (OLT↔Router) access uplinks, excluded from optical attenuation and included in logical upstream graph.
- Pathfinding: Baseline logical/optical graph helpers exist; extended optical attenuation math is planned. Cache/metrics hooks are outlined.

- Status service and link passability: centralized, strict‑by‑default
  - Device statuses are computed by `status_service.evaluate_device_status`. ACTIVE devices degrade to `DEGRADED` when upstream dependency validation fails; PASSIVE devices use propagation snapshot for degrade; ONT/Business ONT with `NO_SIGNAL` → `DOWN`. Admin overrides win.
  - Link effective status is exposed via API with normalized strings and computed by `evaluate_link_status`; passability is unified in `is_link_passable` and respected by dependency and traffic engines.

Deferments:

- Smart SVG Cockpits: implemented (Digital Display) – no longer “on hold”. Device-specific cockpits including AON CPE exist.
- Stable Physics Engine: still open. A gentle containment force for containers exists today.

All of the above are green under the current test suite; see `backend/tests` for coverage across provisioning, IPAM edge cases, routing, and pipeline behaviors.

Realtime Transport Notes: WebSocket transport uses a bounded, coalescing outbox queue with a single async dispatcher and heartbeat (ping/pong) to prune stale connections. Message types like `device.status.changed` and `device.optical.updated` coalesce per-device to reduce burstiness under load.

### 1.2 Recent additions (r9.4 UI & containers)

- Port management and Interfaces UI
  - Backend exposes live summaries via `GET /api/ports/summary/{device_id}` (role-grouped occupancy and effective_status) and `GET /api/ports/ont-list/{device_id}`.
  - Frontend Details panel tabs: Overview | Interfaces | Optical.
    - Overview shows Ports section with live occupancy for OLT and AON_SWITCH (light polling).
    - Interfaces tab lists interfaces with role/admin badges and per-interface addresses (fetched on demand).
- Hardware-catalog selection on device creation
  - Drag-and-drop now opens a hardware model selector; selection drives default interface layout and capacities.
  - A safe default exists for tests/headless flows (auto-confirm with no specific model).
- Admin overrides and DEGRADED propagation
  - Device and Link PATCH override endpoints set/clear `admin_override_status` with override precedence centralized in status service.
  - Passive nodes are marked `DEGRADED` when upstream is unreachable; frontend maps `DEGRADED` to distinct badges/colors.
- Tariffs technology and defaults
  - AON_CPE Cockpit zeigt Tarif im Digital‑Display an; ONT/Business ONT Cockpits nutzen zusätzlich RX POWER.
  - Tariff model includes `technology` (GPON/AON); defaults are seeded idempotently and assigned deterministically to leaf types.
  - UI filters tariff dropdown by inferred device technology.
- **Effective capacity fields for devices (API contract)**
  - Backend `GET /api/devices` now exposes effective capacity in two places for forward/backward compatibility:
    - Nested: `parameters.capacity.effective_device_capacity_mbps`
    - Flattened: `parameters.effective_capacity_mbps`
  - **RouterCockpit displays a compact line `TotCap (Gbps): <current> / <max>`**
    - current: by default uses server-side `bps` (upstream) to stay consistent with the backend `utilization` calculation; optionally the UI may show the combined throughput (`upstream_bps + downstream_bps`) rounded to integer Gbps, but then `utilization` must be treated separately as it remains upstream-based.
    - max: capacity rendered as integer Gbps (or integer Mbps if < 1 Gbps) to avoid cockpit text overlap.

## 2. Domain Model & Classification

### 2.1 Core Entities

- Device: Active, passive, container, or always_online logical node.
- Interface: Network attachment point (role: management | p2p_uplink | access | optical).
- Link: Connection between devices (logical or optical segment).
- IPPool / Allocation (implicit via IPAM module).
- ProvisioningRecord (future optional auditing).

### 2.2 Device Classification Table

| Device Type      | Role Class        | Provisioning Allowed | Container? | Always Online? | Hosts Children | Notes                                                       |
| ---------------- | ----------------- | -------------------- | ---------- | -------------- | -------------- | ----------------------------------------------------------- |
| Backbone Gateway | special           | (implicit root)      | no         | yes            | no             | Root anchor; status baseline; emits upstream availability   |
| Core Router      | active            | yes                  | no         | no             | limited        | Requires existing Backbone Gateway association              |
| Edge Router      | active            | yes                  | no         | no             | no             | Standard routed node; participates in p2p links             |
| OLT              | active            | yes                  | no         | no             | no             | Optical line terminal; signal origin for ONTs               |
| AON Switch       | active            | yes                  | no         | no             | no             | Active aggregation switch                                   |
| POP              | passive_container | no                   | yes        | yes            | yes            | Physical aggregation enclosure; parent for OLT / AON Switch |
| CORE_SITE        | passive_container | no                   | yes        | yes            | yes            | Larger site container; hosts multiple children; no parent   |
| ODF              | passive_inline    | no                   | no         | no             | no             | Optical distribution frame (loss element)                   |
| NVT              | passive_inline    | no                   | no         | no             | no             | Network termination (passive)                               |
| Splitter         | passive_inline    | no                   | no         | no             | no             | Optical splitter (adds attenuation)                         |
| HOP              | passive_inline    | no                   | no         | no             | no             | Passive path element (generic)                              |
| ONT              | active (edge)     | yes                  | no         | no             | no             | Customer termination; signal path endpoint                  |
| Business ONT     | active (edge)     | yes                  | no         | no             | no             | Variant with same optical semantics                         |
| AON CPE          | active (edge)     | yes                  | no         | no             | no             | CPE management pool distinct                                |

### 2.3 Key Relationships

- **Container Roles**: POP and CORE_SITE act as physical grouping boundaries and parent anchors but are not part of logical/optical paths. They:
  - Cannot be link endpoints (enforced via `backend/api/endpoints/links.py`).
  - Host active devices (OLT/AON_SWITCH) via `parent_container_id`.
  - Serve as aggregation sinks in TrafficEngine v2 but do not participate in path construction.
- parent_container_id: set for active devices hosted in a POP or CORE_SITE container (containers have no parent).
- Links may connect active ↔ passive ↔ active chains forming complete signal paths.
- Provisioning constraints defined via `backend/constants/provisioning.py` (strict matrix).

### 2.4 Optical & Signal Attributes (Light Feature)

The following domain attributes enable the signal ("Licht") simulation layer:

| Entity                  | Field               | Type                      | Required | Default                   | Description                                                               |
| ----------------------- | ------------------- | ------------------------- | -------- | ------------------------- | ------------------------------------------------------------------------- |
| OLT                     | tx_power_dbm        | float                     | yes      | +5.0                      | Transmit optical power launched downstream.                               |
| ONT                     | sensitivity_min_dbm | float                     | yes      | -30.0                     | Minimum receive power for valid signal (below → NO_SIGNAL).               |
| Passive (ODF, NVT, HOP) | insertion_loss_db   | float                     | yes      | 0.5 (ODF/HOP), 0.1 (NVT)  | Attenuation added by passive element. Editable.                           |
| Splitter                | insertion_loss_db   | float                     | yes      | 3.5                       | High attenuation element (could vary by split ratio later).               |
| Link                    | length_km           | float                     | yes      | (auto/default if missing) | Physical fiber length used for fiber loss computation.                    |
| Link                    | physical_medium_id  | int (FK → PhysicalMedium) | yes      | (auto‑select by context)  | Selected medium (e.g., SMF G.652D). Attenuation derived from constants.   |
| Link (derived)          | link_loss_db        | float (computed)          | n/a      | n/a                       | length_km \* fiber_type.attenuation_per_km (not persisted unless cached). |

Constraints:

- tx_power_dbm range sanity: (-10 … +10) configurable.
- sensitivity_min_dbm typically [-33 … -26].
- attenuation_loss_db must be >= 0.
- length_km ≥ 0; attenuation_per_km > 0.
- Physical medium must exist (validated); fiber constants exposed via `/api/optical/fiber-types`.

Patch Endpoints (added later) expose updates for these fields; changes trigger recalculation for affected ONTs.

Implementation status:

- Device-level optics (OLT tx_power_dbm, ONT sensitivity_min_dbm, passive attenuation_loss_db, splitter attenuation_loss_db) exist.
- Link-level attenuation fields exist: `Link.length_km` and `Link.physical_medium_id` (FK to `PhysicalMedium`). Fiber types with `attenuation_db_per_km` are provided via constants and API; optical recompute uses these to calculate path loss.

## 2.5 Status Implications on Traffic Generation

- **DEGRADED vs. DOWN**:
  - **ONT/Business ONT**:
    - `DEGRADED` or `DOWN` status blocks upstream traffic generation (ref: `backend/services/traffic/v2_engine.py`).
    - Exception: AON_CPE generates traffic in `DEGRADED` if no backbone exists (`has_backbone` flag check).
  - **Infrastructure Devices**:
    - `DEGRADED` devices continue aggregation if not admin-overridden to `DOWN` (ref: `backend/services/traffic/v2_aggregation.py`).
