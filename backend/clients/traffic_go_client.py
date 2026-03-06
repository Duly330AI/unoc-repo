"""
TrafficGoClient: Python client for Go Traffic Engine HTTP API.

This client replaces the Python TrafficEngine (v2_engine.py) with HTTP calls
to the Go service for 4-5× performance improvement at scale (1000+ devices).

Usage:
    client = TrafficGoClient(base_url="http://localhost:8080")

    # Trigger traffic generation tick
    result = client.tick()
    print(f"Processed {result['leaves_count']} leaves in {result['duration_ms']}ms")

    # Get current traffic snapshot
    snapshot = client.snapshot()
    for device_id, metrics in snapshot['device_metrics'].items():
        print(f"{device_id}: up={metrics['up_mbps']}, down={metrics['down_mbps']}")
"""

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


class TrafficGoClient:
    """
    HTTP client for Go Traffic Engine.

    Communicates with the Go service via REST API for high-performance
    traffic generation and aggregation at scale.
    """

    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 30.0):
        """
        Initialize Go Traffic Engine client.

        Args:
            base_url: Base URL of Go service (default: http://localhost:8080)
            timeout: HTTP request timeout in seconds (default: 30s)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        log.info(f"TrafficGoClient initialized: {base_url}")

    def health(self) -> dict[str, Any]:
        """
        Check health status of Go service.

        Returns:
            dict: {"status": "healthy", "database": "healthy", "version": "0.1.0"}

        Raises:
            httpx.HTTPError: If service is unreachable
        """
        url = f"{self.base_url}/health"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def tick(self) -> dict[str, Any]:
        """
        Trigger a traffic generation tick.

        This causes the Go service to:
        1. Fetch fresh data from PostgreSQL (devices, links, interfaces, tariffs)
        2. Build adjacency graph
        3. Generate traffic for all provisioned leaf devices
        4. Aggregate traffic along BFS paths to anchor devices
        5. Return aggregated metrics

        Returns:
            dict: {
                "success": bool,
                "tick": int,
                "leaves_count": int,
                "devices_with_traffic": int,
                "links_with_traffic": int,
                "duration_ms": int,
                "message": str
            }

        Raises:
            httpx.HTTPError: If API call fails
        """
        url = f"{self.base_url}/api/v1/tick"
        response = self.client.post(url)
        response.raise_for_status()

        result = response.json()
        log.info(
            f"Traffic tick completed: tick={result.get('tick')}, "
            f"leaves={result.get('leaves_count')}, "
            f"devices={result.get('devices_with_traffic')}, "
            f"links={result.get('links_with_traffic')}, "
            f"duration_ms={result.get('duration_ms')}"
        )
        return result

    def snapshot(self) -> dict[str, Any]:
        """
        Get current traffic snapshot.

        Returns the most recent traffic metrics computed by the Go service.
        Call after tick() to get aggregated traffic data.

        Returns:
            dict: {
                "tick": int,
                "timestamp": str (ISO 8601),
                "leaves_count": int,
                "device_metrics": {
                    "device_id": {
                        "up_mbps": float,
                        "down_mbps": float,
                        "utilization": float (0.0-1.0)
                    }
                },
                "link_metrics": {
                    "link_id": {
                        "traffic_mbps": float,
                        "capacity_mbps": float,
                        "utilization": float (0.0-1.0)
                    }
                }
            }

        Raises:
            httpx.HTTPError: If API call fails
        """
        url = f"{self.base_url}/api/v1/snapshot"
        response = self.client.get(url)
        response.raise_for_status()

        snapshot = response.json()
        log.debug(
            f"Traffic snapshot retrieved: tick={snapshot.get('tick')}, "
            f"devices={len(snapshot.get('device_metrics', {}))}, "
            f"links={len(snapshot.get('link_metrics', {}))}"
        )
        return snapshot

    def close(self):
        """Close HTTP client connection pool."""
        self.client.close()
        log.info("TrafficGoClient closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit (auto-close)."""
        self.close()


# Convenience function for one-off operations
def trigger_traffic_tick(base_url: str = "http://localhost:8080") -> dict[str, Any]:
    """
    Convenience function to trigger a single traffic tick.

    Args:
        base_url: Go service URL

    Returns:
        Tick result dict

    Example:
        result = trigger_traffic_tick()
        print(f"Processed {result['leaves_count']} leaves")
    """
    with TrafficGoClient(base_url=base_url) as client:
        return client.tick()
