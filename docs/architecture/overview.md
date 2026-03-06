# HINWEIS (historisch/Planung)

Dieses Dokument skizziert eine Ziel‑/Planungsperspektive (z. B. Redis‑Einsatz). Verbindlich sind die nummerierten Dokumente (01–14), akzeptierte ADRs und der Code. Wo Aussagen abweichen, gilt der Code.

# Architecture Overview

Version: v2.3 (Strict Upstream L3 Status + Collapsed Optical Access Edge)

Changelog (v2.3 summary):

- Enforced strict device UP gating on upstream L3 reachability (routers, OLT/AON, ONT, passives) with removal of legacy leniency for routers and access actives.
- Introduced deterministic synthetic logical edge (Collapsed Optical Access Edge) between every ONT / BUSINESS_ONT and its nearest OLT across passive optical chain (`class=access_optical_term`, id `collapsed_optical:<ont>-><olt>`).
- Trimmed DEGRADED masking scope; passives still may surface DEGRADED only on evaluator exceptions.
- Documentation cross-references updated: `status_service.md`, `topology-engine.md`, `llm/03_ipam_and_status.md` §18.

UNOC targets 1k–10k+ devices with a fast, incremental update model:

- Write path: Minimal synchronous work; mutations are persisted and queued.
- Background engine: Coalesces events (50–200 ms), recomputes only affected subgraphs, persists diffs.
- Read path: Cached snapshots (version/ETag), small responses, WS deltas.
- Storage: PostgreSQL in prod, SQLite in dev; Redis for queue + short-lived caches (Planung).
- Observability: Prometheus metrics, perf logs, optional tracing.

Aktueller Stand (Implementierung):

- Es gibt keinen aktiven Redis‑Client im Codepfad. Stattdessen werden in‑process Kurz‑TTL‑Caches auf Hotpaths verwendet und der WS‑Outbox/Dispatcher trägt die Realtime‑Fanouts.
- Die Vision (Redis für Snapshots/Queues) bleibt bestehen; dieser Abschnitt beschreibt die Zielarchitektur.
