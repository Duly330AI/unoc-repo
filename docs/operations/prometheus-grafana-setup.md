# Prometheus & Grafana integration

The backend exposes two endpoints under `/metrics`:

- `/metrics/runtime` — JSON snapshot of in-process counters/gauges (debug/tests)
- `/metrics/prometheus` — Prometheus text exposition format (scrape here)

Custom metrics currently exported:

- `db_query_seconds` (Histogram) — SQL query durations
- `optical_cache_hits_total` / `optical_cache_misses_total` (Counters)
- `optical_cache_hitrate` (Gauge 0..1)

### L3 resolver metrics (Phase 4)

These metrics provide visibility into the deterministic L3 reachability resolver used for status decisions and debugging:

- `l3_resolver_calls_total{outcome,reason}` (Counter)
  - outcome: `ok` | `fail`
  - reason: categorized failure reason (e.g., `no_default_route`, `egress_admin_down`, `no_eligible_route`), or `none` on success
- `l3_resolver_duration_seconds` (Histogram)
  - Resolution time per call
- `l3_resolver_hops` (Histogram)
  - Number of hops traversed during path resolution (integer buckets)

Example Grafana queries:

- Success rate (5m):
  - `sum(rate(l3_resolver_calls_total{outcome="ok"}[5m])) / sum(rate(l3_resolver_calls_total[5m]))`
- Top failure reasons (5m):
  - `topk(5, sum by (reason) (rate(l3_resolver_calls_total{outcome="fail"}[5m])))`
- P95 resolver latency (5m):
  - `histogram_quantile(0.95, sum(rate(l3_resolver_duration_seconds_bucket[5m])) by (le))`
- Average hops (5m):
  - `sum(rate(l3_resolver_hops_sum[5m])) / sum(rate(l3_resolver_hops_count[5m]))`

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
