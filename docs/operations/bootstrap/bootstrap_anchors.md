# Bootstrap Guide: POP → Backbone → Core (Green baseline)

This short guide helps you create the minimal anchor topology so active devices evaluate to UP (not DEPRECATED) and traffic paths have a sink. You can run these via the REST API or by using the dev seed script.

## Option A: Use the seed script

PowerShell

```powershell
# Recreate dev DB and seed a minimal topology (POP, Core, OLT)
python scripts/reset_dev_db.py --force --seed
# Backend will pick up the file DB; start it if not running:
python run.py
```

What you get:

- pop1 (POP)
- core1 (CORE_ROUTER, provisioned)
- olt1 (OLT, parented under pop1)

## Option B: Create via API (manual)

PowerShell

```powershell
# 1) Create POP (anchor container)
curl -s -X POST http://127.0.0.1:5001/api/devices \
  -H "Content-Type: application/json" \
  -d '{"id":"popA","name":"POP A","type":"POP","status":"UP"}'

# 2) Create Backbone Gateway (always-online anchor)
curl -s -X POST http://127.0.0.1:5001/api/devices \
  -H "Content-Type: application/json" \
  -d '{"id":"bb1","name":"Backbone","type":"BACKBONE_GATEWAY","status":"UP"}'

# (Optional) Link bb1 to core later; bb1 serves as a global seed anchor.

# 3) Create Core Router (active), then provision it
curl -s -X POST http://127.0.0.1:5001/api/devices \
  -H "Content-Type: application/json" \
  -d '{"id":"coreA","name":"Core A","type":"CORE_ROUTER","status":"UP"}'

curl -s -X POST http://127.0.0.1:5001/api/devices/coreA/provision -H "Content-Type: application/json"

# 4) (Recommended) Create interfaces and connect Backbone↔Core so strict upstream viability is satisfied
curl -s -X POST http://127.0.0.1:5001/api/interfaces \
  -H "Content-Type: application/json" \
  -d '{"id":"bb1-if0","device_id":"bb1","name":"if0","role":"p2p_uplink"}'

curl -s -X POST http://127.0.0.1:5001/api/interfaces \
  -H "Content-Type: application/json" \
  -d '{"id":"coreA-if0","device_id":"coreA","name":"if0","role":"p2p_uplink"}'

curl -s -X POST http://127.0.0.1:5001/api/links \
  -H "Content-Type: application/json" \
  -d '{"id":"l_bb_core","a_interface_id":"bb1-if0","b_interface_id":"coreA-if0","status":"UP","kind":"FIBER"}'

# 5) (Optional) Add OLT under POP; OLT requires a POP parent
curl -s -X POST http://127.0.0.1:5001/api/devices \
  -H "Content-Type: application/json" \
  -d '{"id":"oltA","name":"OLT A","type":"OLT","status":"UP","parent_container_id":"popA"}'

# (Optional) Add interfaces and link OLT↔Core to complete access path
curl -s -X POST http://127.0.0.1:5001/api/interfaces \
  -H "Content-Type: application/json" \
  -d '{"id":"oltA-if0","device_id":"oltA","name":"if0","role":"p2p_uplink"}'

curl -s -X POST http://127.0.0.1:5001/api/links \
  -H "Content-Type: application/json" \
  -d '{"id":"l_core_olt","a_interface_id":"coreA-if0","b_interface_id":"oltA-if0","status":"UP","kind":"FIBER"}'
```

Notes

- Anchors: ALWAYS_ONLINE devices (Backbone, POP) serve as reachability seeds. With strict-by-default status, active devices (Core, Edge, OLT, AON_SWITCH) become UP only when a strict upstream path to an anchor exists.
- OLT requires a POP parent: enforced by validation; set `parent_container_id` accordingly.
- Admin overrides: If an anchor is admin DOWN, dependent active devices degrade (DEGRADED).
- Traffic engine anchors: prefers CORE → BACKBONE → POP as path sinks; this ensures realistic aggregation targets.

Quick sanity check

- GET /api/debug/full-snapshot?sections=devices — look for effective_status of bb/core/olt.
- GET /api/metrics/snapshot — should show a stable structure once tariffs are assigned and leaves are UP.
