# Dynamic Status (Phase 1)

This document describes how device.status is computed dynamically in API responses.

Rules:

- Admin override wins: if `admin_override_status` is set on a device, that value is returned.
- Always online: `BACKBONE_GATEWAY` and `POP` return `UP` regardless of provisioning.
- Passive devices (SPLITTER, HOP, NVT, ODF) return `UP` in Phase 1.
- Active devices (CORE_ROUTER, EDGE_ROUTER, AON_SWITCH, OLT, ONT, AON_CPE, BUSINESS_ONT):
  - `UP` only if `provisioned == true`, otherwise `DOWN`.

Notes:

- Phase 1 does not consider link state in dynamic status.
- Hooks exist on provisioning and link CRUD to recompute and emit `device.status.changed` if a transition occurs (none expected in Phase 1 for link changes).

API examples:

- Create active device (unprovisioned):
  - POST /api/devices { id:"core1", type:"CORE_ROUTER", status:"UP" }
  - GET /api/devices/core1 -> { status:"DOWN", provisioned:false }
- Provision:
  - POST /api/devices/core1/provision -> emits `device.provisioned` and `device.status.changed` to `UP`.
  - GET /api/devices/core1 -> { status:"UP", provisioned:true }
- Admin override:
  - PUT /api/devices/core1 { admin_override_status:"DOWN" }
  - GET /api/devices/core1 -> { status:"DOWN", admin_override_status:"DOWN" }
