# Topology/Status Engine

- In-memory adjacency and per-OLT trees
- Dirty-set computation from mutations
- BFS-limited reachability recompute
- Optical path recompute only on affected segments
- Diff persistence and WS fanout

## Update (v2.3 – Collapsed Optical Access Edge)

The legacy BFS-based reachability layer has been augmented with a deterministic logical graph builder that introduces a synthetic "collapsed optical access" edge between each ONT/BUSINESS_ONT and its nearest reachable OLT across any passive inline optical chain (ODF / SPLITTER / NVT / HOP). This enables strict upstream L3 gating without requiring ONTs to appear explicitly adjacent at the logical layer to every intermediate passive component.

Rules:

- Candidate path domain = ONT/BUSINESS_ONT, passive inline nodes, OLTs.
- Selection = shortest hop count (device count); ties broken lexicographically by the tuple of device ids along the path for determinism.
- Synthetic edge attributes:
  - id: `collapsed_optical:<ont_id>-><olt_id>`
  - class: `access_optical_term`
  - synthetic: true
- Added always (not gated by "relaxed" mode); relaxed mode may add additional synthetic convenience edges (e.g. OLT→core) separately.

Failure isolation: Any exception while computing collapse paths is swallowed; graph construction proceeds without synthetic edges (status logic then simply treats ONTs as isolated and they remain DOWN).

Security & Determinism: No randomness; heap/BFS tie-breaks use sorted neighbor order for stable output given identical inputs.

Interaction With Status:

- Upstream L3 evaluation now sees ONTs as directly attached to an OLT node in the logical graph, enabling consistent `upstream_l3_ok` evaluation and avoiding divergent interpretations between traffic gating and status service.
