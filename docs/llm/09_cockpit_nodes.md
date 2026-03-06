## 9 · Cockpit Nodes (Components, Props, Rendering Rules)

This document catalogs cockpit node components, their props and data sources, rendering rules, and performance/accessibility notes.

---

## 1. Mapping: device_role → component

- CORE_ROUTER → RouterCockpit
- EDGE_ROUTER → RouterCockpit
- OLT → OLTCockpit
- AON_SWITCH → AONSwitchCockpit
- ONT → ONTCockpit
- AON_CPE → AONCPECockpit
- CONTAINER (site/core/etc.) → ContainerCockpit (aggregated logical view; not a link endpoint)

Notes:

- Containers are not link endpoints; cockpit is purely logical/aggregated.
- Unknown roles fall back to GenericCockpit with minimal summary.

---

## 2. Common props and data contracts

All cockpit components receive an object shaped like:

- device: DeviceOut
  - id, name, role, parameters
  - parameters.capacity.effective_device_capacity_mbps
  - parameters.effective_capacity_mbps (flattened)
- metrics: optional current traffic snapshot for the device
- ports: optional list[InterfaceSummaryOut] from `/api/ports/summary/{device_id}`
- links: optional list of neighboring link endpoints (for path highlights)

Notes on prop usage by cockpit type:

- RouterCockpit does not fetch/consume `ports` by default to minimize payload; it relies on device parameters and metrics only. Link badges (counts) come from the shared link/device stores, not from the ports summary.
- OLT/AON switch cockpits do consume `ports` (PON/ACCESS matrices).

Error handling:

- Missing optional props are tolerated; components should render a neutral/empty state.

---

## 3. Rendering rules by cockpit

### 3.1 RouterCockpit (CORE/EDGE)

- Header shows TotCap (Gbps): actual / maximum (integer-rounded Gbps; no trailing .00). Label text is exactly "TotCap (Gbps)".
- Data source and formula:
  - actual_gbps = round_to_int_gbps(metrics.upstream_traffic_gbps + metrics.downstream_traffic_gbps)
  - maximum_gbps = round_to_int_gbps(device.parameters.effective_capacity_mbps converted to Gbps)
  - No per-port data is required for this view.
- Color scale: device effective status; warn when degraded
- Optional link badges: count of active links (UPLINK/TRUNK)

### 3.2 OLTCockpit

- Renders PON matrix from `ports` list; each tile = one PON interface
- Tile color from effective_status; occupancy shown as count
- Supports click to drill-down:
  - Primary data comes from `usePortSummary` (polling `/api/ports/summary/{olt_id}`) for tile occupancy/capacity.
  - For container-level ONT listings, use the dedicated endpoint `/api/ports/ont-list/{container_id}` (compact list: id, name, type). There is no OLT-specific ONT-list endpoint; fine-grained per-OLT ONT details are fetched on demand via existing device lists and optical path-based UI filters.

### 3.3 AONSwitchCockpit

- ACCESS matrix showing used/total; color by status
- Uplink summary badge

### 3.4 ONTCockpit / AONCPECockpit

- Minimal KPIs: link status, Rx/Tx when available, parent interface reference

### 3.5 ContainerCockpit

- **Client-side aggregation**: The ContainerCockpit performs client-side aggregation by:
  1. Maintaining a list of child device IDs (stored in component state)
  2. Using the `usePortSummary` composable to fetch ports summaries for each child device
  3. Aggregating metrics like PON port occupancy and capacity across all child devices
- Emphasize health distribution and capacity overview

Generic fallback behavior:

- For unknown roles, `GenericCockpit` renders a minimal summary: device name, effective status, and any basic KPIs available from the metrics snapshot. It does not perform role-specific aggregations and ignores `ports` unless explicitly provided for a simple list rendering.

---

## 4. Accessibility (a11y)

- Semantic headings and ARIA labels for matrices and KPIs
- Keyboard navigation between tiles (port matrices) with visible focus
- High-contrast mode support via CSS variables from the theme

---

## 5. Performance and UX

- Render budget: avoid re-rendering when only metrics changed; prefer computed props + shallow reactive state
- Polling: suspend when node is offscreen or not selected; resume on focus
- Virtualize large matrices (future) and batch DOM updates for tile color changes

---

## 6. Testing guidance

- Snapshot tests for layout and labels (especially TotCap formatting)
- Interaction tests: keyboard navigation, drill-downs from tiles
- Contract tests: props optionality and graceful empty states

---

## 7. Integration with realtime

- deviceMetricsUpdated and linkMetricsUpdated deltas update shared stores; cockpits subscribe to store slices. Snapshot recovery via `/api/metrics/snapshot`.
- Congestion thresholds with hysteresis are handled in the backend (see 11_traffic_engine_and_congestion.md); cockpits reflect stabilized states to avoid flicker.

---

## 8. Cross-links

- Ports and Interface Summaries → `08_ports.md`
- Realtime and UI Model → `05_realtime_and_ui_model.md` (see §9.13 Congestion & Hysterese)
- Provisioning and Link Rules → `02_provisioning_model.md`
