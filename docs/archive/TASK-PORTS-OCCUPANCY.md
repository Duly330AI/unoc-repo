# Job: Correct Port Occupancy Calculation in Backend API

Objective

- Fix GET /ports/summary used-count semantics so they reflect real occupancy, not interface existence.

Scope

- Endpoint: backend/api/endpoints/ports.py → GET /ports/summary/{device_id}
- Models consulted: Device, Interface, Link, PortProfile, PortRole, InterfaceRole
- Services consulted: backend/services/optical_path_resolver.resolve_optical_path

Implementation Notes

- ACCESS & UPLINK: used = number of Interface ids with port_role=ACCESS/UPLINK that appear as endpoints of any Link.
- PON (OLT): used = number of ONT/BUSINESS_ONT devices with provisioned=True that currently resolve an optical path to THIS OLT (aggregated across all PON ports; no per-port assignment required).
- MANAGEMENT: used = 1 if a management interface exists on the device; otherwise 0.
- Response contract unchanged: { device_id, total, by_role: { ROLE: { total, used, [max_subscribers] } } }.

Verification

- Seed a small topology (reset_dev_db.py --seed), create an ONT under olt1, add optical path, provision ONT.
- GET /ports/summary/{olt_id} → PON: { total: 16, used: 1 } (assuming default model with 16 PON ports).
- Create an AON switch with a single access link bound to an access port → ACCESS: { total: 24, used: 1 }.
- MANAGEMENT role shows used: 1 when mgmt interface exists.
- Run full backend tests: pytest -q.

Change Log

- 2025-09-15: Implemented corrected used-count logic and added compatibility for legacy 'MGMT' role key.
