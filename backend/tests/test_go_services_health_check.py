"""Tests for Go services health check integration.

Tests verify that:
- All 5 Go services are properly registered in health check
- Health check handles both HTTP and gRPC services correctly
- Service availability detection works (via mocking)
- Port Summary service is included in health check list

Note: These tests mock at the module level to avoid Traffic Engine connection issues.
"""

import socket
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_traffic_engine():
    """Mock Traffic Engine to prevent connection during import."""
    with patch("backend.services.traffic_engine.ENGINE_SINGLETON"):
        yield


def test_health_check_includes_all_five_services(mock_traffic_engine):
    """Verify all 5 Go services are registered in health check."""
    # Import after mocking
    from backend.main import _check_go_services_health

    # Mock logging to capture service names
    with patch("logging.getLogger") as mock_get_logger:
        mock_log = MagicMock()
        mock_get_logger.return_value = mock_log

        # Mock urllib and socket to prevent actual connections
        with (
            patch("urllib.request.urlopen"),
            patch.object(socket.socket, "connect_ex", return_value=1),
        ):
            _check_go_services_health()

        # Verify all 5 services were checked
        info_calls = [str(call) for call in mock_log.info.call_args_list]
        all_info = "\n".join(info_calls)

        assert "Traffic Engine" in all_info
        assert "Optical PathFinder" in all_info
        assert "Status Propagation" in all_info
        assert "Batch Operations" in all_info
        assert "Port Summary" in all_info, "Port Summary service missing from health check!"


def test_health_check_detects_http_service(mock_traffic_engine):
    """Verify HTTP service health check (Traffic Engine)."""
    from backend.main import _check_go_services_health

    with patch("logging.getLogger") as mock_get_logger:
        mock_log = MagicMock()
        mock_get_logger.return_value = mock_log

        # Mock urllib to simulate successful HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda self: self
        mock_response.__exit__ = lambda self, *args: None

        with (
            patch("urllib.request.urlopen", return_value=mock_response),
            patch.object(socket.socket, "connect_ex", return_value=1),
        ):
            _check_go_services_health()

        # Verify Traffic Engine was detected as healthy
        info_calls = [str(call) for call in mock_log.info.call_args_list]
        all_info = "\n".join(info_calls)
        assert "Traffic Engine" in all_info
        assert "http://localhost:8080" in all_info


def test_health_check_detects_grpc_services(mock_traffic_engine):
    """Verify gRPC service health check (all 4 gRPC services)."""
    from backend.main import _check_go_services_health

    with patch("logging.getLogger") as mock_get_logger:
        mock_log = MagicMock()
        mock_get_logger.return_value = mock_log

        # Mock urllib to fail (HTTP service unavailable)
        with (
            patch("urllib.request.urlopen", side_effect=Exception("Connection refused")),
            patch.object(socket.socket, "connect_ex", return_value=0),
        ):  # gRPC services available
            _check_go_services_health()

        # Verify all gRPC services were checked
        info_calls = [str(call) for call in mock_log.info.call_args_list]
        all_info = "\n".join(info_calls)

        assert "grpc://localhost:50051" in all_info  # Optical PathFinder
        assert "grpc://localhost:50053" in all_info  # Status Propagation
        assert "grpc://localhost:50052" in all_info  # Batch Operations
        assert "grpc://localhost:50054" in all_info  # Port Summary


def test_health_check_detects_port_summary_on_correct_port(mock_traffic_engine):
    """Verify Port Summary service is on port 50054."""
    from backend.main import _check_go_services_health

    with patch("logging.getLogger") as mock_get_logger:
        mock_log = MagicMock()
        mock_get_logger.return_value = mock_log

        # Track which ports were checked
        checked_ports = []

        def mock_connect_ex(address):
            checked_ports.append(address[1])
            return 0  # All ports available

        with (
            patch("urllib.request.urlopen", side_effect=Exception()),
            patch.object(socket.socket, "connect_ex", side_effect=mock_connect_ex),
        ):
            _check_go_services_health()

        # Verify Port Summary is on port 50054
        assert 50054 in checked_ports, "Port Summary service not checked on port 50054!"

        # Verify info log contains Port Summary with correct port
        info_calls = [str(call) for call in mock_log.info.call_args_list]
        all_info = "\n".join(info_calls)
        assert "Port Summary" in all_info
        assert "50054" in all_info


def test_health_check_handles_unavailable_services(mock_traffic_engine):
    """Verify health check logs warnings for unavailable services."""
    from backend.main import _check_go_services_health

    with patch("logging.getLogger") as mock_get_logger:
        mock_log = MagicMock()
        mock_get_logger.return_value = mock_log

        # Mock all services as unavailable
        with (
            patch("urllib.request.urlopen", side_effect=Exception("Connection refused")),
            patch.object(socket.socket, "connect_ex", return_value=1),
        ):  # gRPC connection refused
            _check_go_services_health()

        # Verify warning was logged
        warning_calls = [str(call) for call in mock_log.warning.call_args_list]
        all_warnings = "\n".join(warning_calls)

        assert "unavailable" in all_warnings.lower() or "degraded" in all_warnings.lower()
        assert "start_all_services.ps1" in all_warnings  # Helpful tip message


def test_health_check_reports_all_healthy_when_all_available(mock_traffic_engine):
    """Verify success message when all 5 services are available."""
    from backend.main import _check_go_services_health

    with patch("logging.getLogger") as mock_get_logger:
        mock_log = MagicMock()
        mock_get_logger.return_value = mock_log

        # Mock all services as available
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda self: self
        mock_response.__exit__ = lambda self, *args: None

        with (
            patch("urllib.request.urlopen", return_value=mock_response),
            patch.object(socket.socket, "connect_ex", return_value=0),
        ):
            _check_go_services_health()

        # Verify success message
        info_calls = [str(call) for call in mock_log.info.call_args_list]
        all_info = "\n".join(info_calls)

        assert "All Go services are available" in all_info or "available!" in all_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
