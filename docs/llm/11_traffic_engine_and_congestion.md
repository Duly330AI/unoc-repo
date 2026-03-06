

## 11. Traffic Engine v2 and Congestion

This document describes the Traffic Engine v2 (TEv2): how traffic is generated, aggregated, and surfaced to the UI, including congestion detection with hysteresis and event emission.

### 11.1 Scope and goals

- Deterministic, tariff-based traffic generation per device/link
- Hierarchical aggregation on devices and links
- GPON-aware segment aggregation (OLT→passives→ONT)
- Congestion detection with hysteresis to avoid flapping
- Delta event emission suitable for the Realtime UI model
- Fallback to minimal L2/L3 forwarding for path synthesis where needed

### 11.2 Generation model (tariff-based)

- Tariff model provides technology-specific baselines.
- Per-tick generation emits ingress/egress bps per device interface; synthesized device/link totals are computed for API.
- Deterministic seeds control PRNG when enabled.

### 11.3 Aggregation

- Device-level: sum ingress/egress across relevant interfaces; normalize to Mbps and Gbps for UI.
- Link-level: sum traffic across endpoints; symmetric unless asymmetric tariff enabled.
- **GPON segments (ODF-as-aggregator)**: 
  - A segment is identified as a pair of OLT PON interface and directly adjacent ODF
  - segment_id is formed as `f"{pon_if_id}::{odf_id}"`
  - The ODF is determined from the optical path resolution via the segment list or through link neighbors
  - Aggregate all ONTs connected to a single ODF; apply the capacity constraints of the single OLT PON port to which that ODF is linked.

### 11.4 Congestion detection and hysteresis

- Device/link thresholds:
  - Enter congestion at utilization >= 100%
  - Clear congestion at utilization <= 95%
- GPON segment thresholds:
  - Enter congestion at utilization >= 95%
  - Clear congestion at utilization <= 85%
- These values are codified in backend/services/traffic/v2_engine.py and v2_congestion.py.

### 11.5 Events

- Emitted per tick (coalesced):
  - deviceMetricsUpdated {device_id, bps_in, bps_out, capacity_bps, tick}
  - linkMetricsUpdated {link_id, bps, capacity_bps, tick}
  - segment.congestion.detected/cleared {segment_id, overload_percentage, tick}
- Emission order integrates with §8 Realtime model and coalescing.

### 11.6 Forwarding fallback

- **Minimal L2/L3 pipeline backs TEv2 when traffic requires path synthesis**:
  - **Trigger**: For each tick, BFS is performed for each generating leaf (ONT/Business ONT/AON CPE) to determine an anchor route
  - **Fallback condition**: If no anchor is reachable, L2/L3 forwarding fallback is attempted
  - L2: MAC learn/forward/flood (backend/services/l2_service.py)
  - L3: VRF-scoped LPM + next-hop MAC resolution (backend/services/l3_service.py)
  - Orchestration: forwarding_service.resolve_flow_path/forward_flow

### 11.7 UI projections

- Router cockpit shows TotCap (Gbps) and actual traffic rounded to integer Gbps.
- GET /devices exposes:
  - parameters.capacity.effective_device_capacity_mbps
  - parameters.effective_capacity_mbps (flattened)
- Links include effective capacities where modeled.

### 11.8 Testing

- Unit tests in backend/tests/test_traffic_engine_v2.py cover:
  - Tariff generation within bounds
  - End-to-end aggregation across devices and links
  - Congestion enter/clear behavior with hysteresis
  - Snapshot endpoint returns v2 data with links

### 11.9 Future work

- Per-tariff burst modeling; traffic classes
- Segment-level shaping/queuing
- Device-specific capacity overrides and dynamic derate

## 11.10 Traffic Generation and Aggregation Details

### 11.10.1 Asymmetric Tariffs and Aggregation

- **Asymmetric traffic generation**:
  - For each leaf, upstream and downstream are generated separately:
    - `up_bps = rand * t.max_up_mbps`
    - `down_bps = rand * t.max_down_mbps`
  - Both values are tracked separately throughout the aggregation process

- **Direction-aware aggregation**:
  - Per-device totals are maintained separately for upstream and downstream:
    - `per_device_totals` tracks upstream traffic
    - `per_device_down_totals` tracks downstream traffic
  - The router's "incoming" load represents the sum of upstream from endpoints
  - The "outgoing" load represents the sum of downstream demand
  - These values are reflected in the device metrics:
    - `bps_in` (upstream received)
    - `bps_out` (downstream transmitted)

### 11.10.2 GPON Segment Capacity Sources

- **Default capacity values**:
  - Standard GPON: `down=2.5e9`, `up=1.25e9` bps
  - XG/XGS-PON variants may have different defaults

- **Hardware-based capacity overrides**:
  - When an OLT has a HardwareModel, the corresponding PortProfiles are loaded
  - Based on interface `profile_name` or PortRole=PON, appropriate profiles are identified
  - Capacities are overridden based on `speed_gbps` and `media/name` detection
  - Implementation: Helper `_pon_caps()` in `v2_engine.py`

### 11.10.3 Congestion Event Details

- **Thresholds and detection**:
  - `segment_detect_threshold=0.95` (enter congestion)
  - `segment_clear_threshold=0.85` (exit congestion)
  - A segment is congested if `max(util_down, util_up) >= detect_threshold`

- **Event payload structure**:
  - `segment.congestion.detected` contains:
    - `id`: segment identifier
    - `olt_id`: OLT device ID
    - `pon_port_id`: PON interface ID
    - `odf_id`: ODF device ID
    - `demand_*_bps`: Current traffic demand
    - `capacity_*_bps`: Available capacity
    - `tick`: Timestamp of measurement
  - No explicit `overload_percentage` field exists in current implementation; consumers can calculate utilization from demand/capacity ratios

- **Event emission**:
  - Events are published during the segment processing loop in `v2_engine.py`
  - Follows the same coalescing and ordering rules as other traffic events