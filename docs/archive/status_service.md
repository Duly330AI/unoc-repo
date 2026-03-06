# Dynamic Status (Phase 1)

This legacy document described Phase 1 rules for dynamic status. The authoritative, up-to-date specification now lives in `docs/llm/03_ipam_and_status.md` (§5 Status). Use this file only for historical reference.

Legacy content (for archival):

- Admin override wins; always-online devices return UP; passives use propagation snapshot; actives require provisioned=true, etc.
- Hooks on provisioning and link CRUD emit events as appropriate.
