from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_prometheus_metrics_endpoint_ok_and_contains_core_metrics():
    # Hit runtime first to ensure gauges are computed at least once
    r0 = client.get("/api/metrics/runtime")
    assert r0.status_code == 200

    r = client.get("/api/metrics/prometheus")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")

    body = r.text
    # Prometheus text exposition format should include HELP/TYPE lines and metric samples
    assert "# HELP" in body
    assert "# TYPE" in body

    # Check a few of our custom metrics labels/names exist
    assert "db_query_seconds_bucket" in body or "db_query_seconds_sum" in body
    assert "optical_cache_hits_total" in body
    assert "optical_cache_misses_total" in body
    assert "optical_cache_hitrate" in body
