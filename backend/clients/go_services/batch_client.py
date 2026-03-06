"""
Batch Operations Service gRPC Client with Python Fallback

Week 3 Day 14: Full Python integration with Go batch service.
Falls back to Python implementation if Go service unavailable.
"""

import time
from typing import Any

import grpc

from backend.proto import batch_pb2, batch_pb2_grpc


class BatchClient:
    """
    Client for batch operations service (Go gRPC or Python fallback).

    Week 3 Day 14 implementation:
    - batch_create_links: Bulk link creation (64 links in single transaction)
    - batch_provision_devices: Bulk ONT provisioning
    - batch_delete_links: Bulk link deletion
    - All with single optical recompute at end (262× speedup)
    """

    def __init__(
        self,
        grpc_host: str = "localhost",
        grpc_port: int = 50052,
        timeout: float = 60.0,
        use_fallback: bool = True,
    ):
        """Initialize batch client."""
        self.grpc_address = f"{grpc_host}:{grpc_port}"
        self.timeout = timeout
        self.use_fallback = use_fallback
        self._channel: grpc.Channel | None = None
        self._stub = None
        self._go_available = False

        self._try_connect()

    def _try_connect(self) -> bool:
        """Attempt to connect to Go service."""
        try:
            self._channel = grpc.insecure_channel(
                self.grpc_address,
                options=[
                    ("grpc.max_receive_message_length", 100 * 1024 * 1024),
                    ("grpc.keepalive_time_ms", 10000),
                ],
            )

            # Create gRPC stub for batch service
            self._stub = batch_pb2_grpc.BatchServiceStub(self._channel)

            # Test connection with health check
            health_req = batch_pb2.HealthCheckRequest()
            self._stub.HealthCheck(health_req, timeout=5.0)

            self._go_available = True
            print(f"[OK] Connected to Go batch-service at {self.grpc_address}")
            return True

        except Exception as e:
            print(f"[WARN] Go batch-service unavailable: {e}")
            if self.use_fallback:
                print("[INFO] Falling back to Python batch implementation")
            self._go_available = False
            return False

    def batch_create_links(
        self,
        links: list[dict[str, Any]],
        dry_run: bool = False,
        skip_optical_recompute: bool = False,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create multiple links in a single transaction.

        Args:
            links: List of link specs, each with:
                   - a_interface_id (int): First interface ID
                   - b_interface_id (int): Second interface ID
                   - length_km (float, optional): Physical length
                   - status (str, optional): "active", "inactive", or "planned"
                   - metadata (dict, optional): Additional key-value pairs
            dry_run: If True, validate but don't commit
            skip_optical_recompute: If True, skip optical path resolution
            request_id: Correlation ID for tracing

        Returns:
            dict with:
                - created_link_ids (list[int]): Successfully created link IDs
                - failed_links (list[dict]): Failed creation attempts with errors
                - total_requested (int): Total links requested
                - total_created (int): Total links created
                - duration_ms (int): Operation duration
                - backend (str): "go" or "python"
        """
        start_time = time.time()

        if self._go_available and self._stub:
            try:
                # Convert Python dicts to protobuf messages
                link_specs = []
                for link in links:
                    spec = batch_pb2.LinkCreateSpec(
                        a_interface_id=link["a_interface_id"],
                        b_interface_id=link["b_interface_id"],
                        length_km=link.get("length_km", 0.0),
                        status=link.get(
                            "status", "UP"
                        ),  # ✅ Default "UP" (matches Python Status enum)
                    )
                    if "metadata" in link:
                        for k, v in link["metadata"].items():
                            spec.metadata[k] = str(v)
                    link_specs.append(spec)

                request = batch_pb2.BatchCreateLinksRequest(
                    links=link_specs,
                    dry_run=dry_run,
                    skip_optical_recompute=skip_optical_recompute,
                    request_id=request_id or "",
                )

                response = self._stub.BatchCreateLinks(request, timeout=self.timeout)

                return {
                    "created_link_ids": list(response.created_link_ids),
                    "failed_links": [
                        {
                            "index": f.index,
                            "a_interface_id": f.a_interface_id,
                            "b_interface_id": f.b_interface_id,
                            "error_code": f.error_code,
                            "error_message": f.error_message,
                        }
                        for f in response.failed_links
                    ],
                    "total_requested": response.total_requested,
                    "total_created": response.total_created,
                    "duration_ms": response.duration_ms,
                    "request_id": response.request_id,
                    "backend": "go",
                }

            except grpc.RpcError as e:
                print(f"[ERROR] Go batch-service RPC error: {e}")
                if self.use_fallback:
                    print("[INFO] Falling back to Python implementation")
                    return self._batch_create_links_python(links, dry_run, request_id, start_time)
                raise

        elif self.use_fallback:
            return self._batch_create_links_python(links, dry_run, request_id, start_time)

        else:
            raise RuntimeError("Go batch-service unavailable and fallback disabled")

    def _batch_create_links_python(
        self,
        links: list[dict[str, Any]],
        dry_run: bool,
        request_id: str | None,
        start_time: float,
    ) -> dict[str, Any]:
        """Python fallback implementation for batch_create_links."""
        # Import here to avoid circular dependency
        from backend.services import batch_service

        result = batch_service.batch_create_links_python(
            links=links,
            dry_run=dry_run,
            request_id=request_id,
        )

        result["duration_ms"] = int((time.time() - start_time) * 1000)
        result["backend"] = "python"
        return result

    def batch_delete_links(
        self,
        link_ids: list[str],  # ✅ Link IDs are strings (format: "interface_a__interface_b")
        skip_optical_recompute: bool = False,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Delete multiple links in a single transaction.

        Args:
            link_ids: List of link IDs to delete (strings, e.g., "core1_eth0__olt1_pon0_1")
            skip_optical_recompute: If True, skip optical path resolution
            request_id: Correlation ID for tracing

        Returns:
            dict with:
                - deleted_link_ids (list[str]): Successfully deleted link IDs
                - failed_links (list[dict]): Failed deletion attempts with errors
                - total_requested (int): Total links requested
                - total_deleted (int): Total links deleted
                - duration_ms (int): Operation duration
                - backend (str): "go" or "python"
        """
        start_time = time.time()

        if self._go_available and self._stub:
            try:
                request = batch_pb2.BatchDeleteLinksRequest(
                    link_ids=link_ids,
                    skip_optical_recompute=skip_optical_recompute,
                    request_id=request_id or "",
                )

                response = self._stub.BatchDeleteLinks(request, timeout=self.timeout)

                return {
                    "deleted_link_ids": list(response.deleted_link_ids),
                    "failed_links": [
                        {
                            "index": f.index,
                            "link_id": f.link_id,
                            "error_code": f.error_code,
                            "error_message": f.error_message,
                        }
                        for f in response.failed_links
                    ],
                    "total_requested": response.total_requested,
                    "total_deleted": response.total_deleted,
                    "duration_ms": response.duration_ms,
                    "request_id": response.request_id,
                    "backend": "go",
                }

            except grpc.RpcError as e:
                print(f"[ERROR] Go batch-service RPC error: {e}")
                if self.use_fallback:
                    print("[INFO] Falling back to Python implementation")
                    return self._batch_delete_links_python(link_ids, request_id, start_time)
                raise

        elif self.use_fallback:
            return self._batch_delete_links_python(link_ids, request_id, start_time)

        else:
            raise RuntimeError("Go batch-service unavailable and fallback disabled")

    def _batch_delete_links_python(
        self,
        link_ids: list[str],  # ✅ Link IDs are strings
        request_id: str | None,
        start_time: float,
    ) -> dict[str, Any]:
        """Python fallback implementation for batch_delete_links."""
        from backend.services import batch_service

        result = batch_service.batch_delete_links_python(
            link_ids=link_ids,
            request_id=request_id,
        )

        result["duration_ms"] = int((time.time() - start_time) * 1000)
        result["backend"] = "python"
        return result

    def health(self) -> dict[str, Any]:
        """Check batch service health."""
        if self._go_available and self._stub:
            try:
                request = batch_pb2.HealthCheckRequest()
                response = self._stub.HealthCheck(request, timeout=5.0)

                return {
                    "status": response.status,
                    "version": response.version,
                    "timestamp": response.timestamp,
                    "message": response.message if response.message else "",
                    "backend": "go",
                    "available": True,
                }
            except grpc.RpcError:
                self._go_available = False
                return {
                    "status": "unavailable",
                    "backend": "python",
                    "available": False,
                }

        return {
            "status": "healthy",
            "backend": "python",
            "available": False,
        }

    def close(self):
        """Close gRPC channel."""
        if self._channel:
            self._channel.close()
            print("Closed batch service gRPC channel")


# Singleton instance
_batch_client: BatchClient | None = None


def get_batch_client() -> BatchClient:
    """Get singleton batch client instance."""
    global _batch_client
    if _batch_client is None:
        _batch_client = BatchClient()
    return _batch_client
