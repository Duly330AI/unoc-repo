"""Aggregate live health/fallback state of the optional Go services.

Read-only diagnostics: probes each Go service through the existing clients and
reports whether the backend is currently using Go or its Python fallback, so a
"looks okay but actually fallback" state is always visible.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

TRAFFIC_ENGINE_URL = os.getenv("UNOC_TRAFFIC_GO_URL", "http://localhost:8080")


def _traffic_engine_entry() -> dict[str, Any]:
    entry: dict[str, Any] = {
        "service": "traffic-engine",
        "transport": "http",
        "address": TRAFFIC_ENGINE_URL,
        "reachable": False,
        "backend_mode": "unknown",
        "detail": None,
    }
    try:
        resp = httpx.get(f"{TRAFFIC_ENGINE_URL.rstrip('/')}/health", timeout=2.0)
        resp.raise_for_status()
        body = resp.json()
        entry["reachable"] = True
        entry["backend_mode"] = "go"
        entry["detail"] = {
            "status": body.get("status"),
            "database": body.get("database"),
            "version": body.get("version"),
        }
    except Exception as e:
        entry["backend_mode"] = "unavailable"
        entry["detail"] = f"unreachable: {type(e).__name__}: {e}"
    return entry


def _optical_entry() -> dict[str, Any]:
    entry: dict[str, Any] = {
        "service": "optical-service",
        "transport": "grpc",
        "address": "localhost:50051",
        "reachable": False,
        "backend_mode": "python_fallback",
        "detail": None,
    }
    try:
        from backend.clients.go_services.optical_client import get_optical_client

        client = get_optical_client()
        entry["address"] = getattr(client, "grpc_address", entry["address"])
        health = client.health()
        entry["reachable"] = bool(health.get("available"))
        entry["backend_mode"] = "go" if health.get("backend") == "go" else "python_fallback"
        entry["detail"] = health
    except Exception as e:
        entry["detail"] = f"client error: {type(e).__name__}: {e}"
    return entry


def _status_entry() -> dict[str, Any]:
    entry: dict[str, Any] = {
        "service": "status-service",
        "transport": "grpc",
        "address": "localhost:50053",
        "reachable": False,
        "backend_mode": "python_fallback",
        "detail": None,
    }
    try:
        from backend.clients.go_services.status_client import get_status_client

        client = get_status_client()
        entry["address"] = getattr(client, "grpc_address", entry["address"])
        health = client.health()
        is_go = health.get("backend") == "go" and health.get("status") == "HEALTHY"
        entry["reachable"] = is_go
        entry["backend_mode"] = "go" if is_go else "python_fallback"
        entry["detail"] = health
    except Exception as e:
        entry["detail"] = f"client error: {type(e).__name__}: {e}"
    return entry


def _batch_entry() -> dict[str, Any]:
    entry: dict[str, Any] = {
        "service": "batch-service",
        "transport": "grpc",
        "address": "localhost:50052",
        "reachable": False,
        "backend_mode": "python_fallback",
        "detail": None,
    }
    try:
        from backend.clients.go_services.batch_client import get_batch_client
        from backend.proto import batch_pb2

        client = get_batch_client()
        entry["address"] = getattr(client, "grpc_address", entry["address"])
        stub = getattr(client, "_stub", None)
        if getattr(client, "_go_available", False) and stub is not None:
            # Live re-probe: the singleton flag can be stale if the service died later.
            stub.HealthCheck(batch_pb2.HealthCheckRequest(), timeout=2.0)
            entry["reachable"] = True
            entry["backend_mode"] = "go"
            entry["detail"] = {"status": "HEALTHY"}
        else:
            entry["detail"] = "not connected at startup; Python fallback active"
    except Exception as e:
        entry["detail"] = f"health probe failed: {type(e).__name__}: {e}"
    return entry


def _port_summary_entry() -> dict[str, Any]:
    entry: dict[str, Any] = {
        "service": "port-summary-service",
        "transport": "grpc",
        "address": "localhost:50054",
        "reachable": False,
        "backend_mode": "python_fallback",
        "detail": None,
    }
    try:
        from backend.clients.port_summary_client import get_port_summary_client

        client = get_port_summary_client()
        entry["address"] = getattr(client, "address", entry["address"])
        stub = getattr(client, "_stub", None)
        if client.is_available() and stub is not None:
            from google.protobuf import empty_pb2

            stub.HealthCheck(empty_pb2.Empty(), timeout=2.0)
            entry["reachable"] = True
            entry["backend_mode"] = "go"
            entry["detail"] = {"status": "HEALTHY"}
        else:
            entry["detail"] = "not connected at startup; Python fallback active"
    except Exception as e:
        entry["detail"] = f"health probe failed: {type(e).__name__}: {e}"
    return entry


def build_go_services_health() -> dict[str, Any]:
    services = [
        _traffic_engine_entry(),
        _optical_entry(),
        _batch_entry(),
        _status_entry(),
        _port_summary_entry(),
    ]
    reachable = [s for s in services if s["reachable"]]
    fallbacks = [s["service"] for s in services if not s["reachable"]]
    if len(reachable) == len(services):
        mode = "go_active"
    elif not reachable:
        mode = "degraded_all_fallback"
    else:
        mode = "partial_fallback"
    return {
        "mode": mode,
        "go_services_reachable": len(reachable),
        "go_services_total": len(services),
        "fallback_active_for": fallbacks,
        "services": services,
        "note": (
            "backend_mode=python_fallback means the backend silently computes this "
            "domain in Python; functionality is preserved but slower"
        ),
    }


__all__ = ["build_go_services_health"]
