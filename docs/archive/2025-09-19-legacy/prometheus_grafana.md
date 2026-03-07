# Prometheus & Grafana integration

The backend exposes two endpoints under `/metrics`:

- `/metrics/runtime` — JSON snapshot of in-process counters/gauges (debug/tests)
- `/metrics/prometheus` — Prometheus text exposition format (scrape here)

Custom metrics currently exported:

- `db_query_seconds` (Histogram) — SQL query durations
- `optical_cache_hits_total` / `optical_cache_misses_total` (Counters)
- `optical_cache_hitrate` (Gauge 0..1)

## Prometheus scrape config

Example `prometheus.yml` snippet:

```yaml
scrape_configs:
  - job_name: 'unoc-backend'
    scrape_interval: 5s
    static_configs:
      - targets: ['host.docker.internal:5001'] # or 'localhost:5001'
    metrics_path: /metrics/prometheus
```

Notes:

- Default backend port is 5001 (VS Code task "backend: run").
- When running Prometheus in Docker on Windows/Mac, prefer `host.docker.internal` to access the host.

## Grafana

- Add Prometheus as a data source.
- Example panels/queries:
  - Query latency (avg): `rate(db_query_seconds_sum[5m]) / rate(db_query_seconds_count[5m])`
  - Cache hit rate: `optical_cache_hitrate`
  - Cache hits/misses per second: `rate(optical_cache_hits_total[5m])` and `rate(optical_cache_misses_total[5m])`

You can export/import dashboards as JSON for sharing in `docs/dashboards/` (optional).
