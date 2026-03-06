# HINWEIS (historisch/Planung)

Diese Notizen beschreiben eine Zielarchitektur (z. B. Snapshot‑Cache in Redis). Verbindlich sind die nummerierten Dokumente (01–14), akzeptierte ADRs und der Code. Der aktuelle Code verwendet in‑process Kurz‑TTL‑Caches für Hotpaths.

# Caching & Snapshots

- Snapshot cache keyed by topology_version (Redis)
- TTL 250–500 ms or strictly versioned
- ETag/If-None-Match on GET /snapshot
- Port summaries and metrics short-cache
