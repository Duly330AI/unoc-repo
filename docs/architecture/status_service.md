# HINWEIS (historisch/Planung) – Aktualisiert für v2.3

> This document reflects an earlier Phase‑1 planning state and is **superseded** for current semantics. For the authoritative, current device & link status rules (strict upstream L3 semantics, passive structural logic, traffic gating, diagnostics) see **ADR-011 – Upstream L3 Semantics, Passive Status Refactor & BFS Deprecation Path** and `docs/llm/03_ipam_and_status.md` §5. The content below is retained only for historical context.

Diese Datei beschreibt einen früheren Phase‑1‑Stand und dient der historischen/planerischen Einordnung. Für die **aktuellen** v2.3‑Regeln (Strict Upstream L3 + Collapsed Optical Access Edge) gelten als Quelle der Wahrheit:

- die nummerierten Architektur‑ und LLM‑Dokumente (01–14),
- die akzeptierten ADRs (z. B. ADR‑010),
- sowie der Code (z. B. `backend/services/status_service.py`).

Aktuelle, verbindliche Regeln zur Statusberechnung (Strict L3 ohne Toleranzen) plus das synthetische Kollabieren von passiven optischen Segmenten (Collapsed Optical Access Edge) sind in `docs/llm/03_ipam_and_status.md` (§5 & §18 Verweis) dokumentiert. Ankergeräte wie `BACKBONE_GATEWAY` bleiben deterministisch ALWAYS_ONLINE.

Zusatz (v2.3): DEGRADED wird im Strict‑Pfad für Router & Access‑Aktive nicht mehr als Maskierung verwendet; ONT/Business ONT erhalten ihren Upstream‑Anschluss logisch über eine synthetische Kante `access_optical_term` (siehe `topology-engine.md`).

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
