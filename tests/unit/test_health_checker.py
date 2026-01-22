"""Tests for the health checker module."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest

from excalidraw_mcp.config import config
from excalidraw_mcp.monitoring.health_checker import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
)


class TestHealthChecker:
    """Test cases for HealthChecker."""

    @pytest.fixture
    def health_checker(self):
        """Create a fresh health checker for testing."""
        return HealthChecker()

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with (
            patch.object(config.monitoring, "health_check_timeout_seconds", 3.0),
            patch.object(config.monitoring, "consecutive_failure_threshold", 3),
            patch.object(config.monitoring, "resource_monitoring_enabled", True),
            patch.object(config.monitoring, "cpu_threshold_percent", 80.0),
            patch.object(config.monitoring, "memory_threshold_percent", 85.0),
        ):
            yield config

    @pytest.mark.asyncio
    async def test_primary_health_check_success(self, health_checker, mock_config):
        """Test successful primary health check."""
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            mock_client.check_health = AsyncMock(return_value=True)

            result = await health_checker._check_primary_health()

            assert result.status == HealthStatus.HEALTHY
            assert result.details["endpoint"] == "/health"
            assert result.details["http_status"] == 200
            assert result.error is None
            mock_client.check_health.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_primary_health_check_failure(self, health_checker, mock_config):
        """Test failed primary health check."""
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            mock_client.check_health = AsyncMock(return_value=False)

            result = await health_checker._check_primary_health()

            assert result.status == HealthStatus.UNHEALTHY
            assert result.details["endpoint"] == "/health"
            assert result.details["http_status"] == 500
            assert result.error is None

    @pytest.mark.asyncio
    async def test_primary_health_check_exception(self, health_checker, mock_config):
        """Test primary health check with exception."""
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            mock_client.check_health = AsyncMock(
                side_effect=Exception("Connection error")
            )

            result = await health_checker._check_primary_health()

            assert result.status == HealthStatus.UNHEALTHY
            assert result.details["endpoint"] == "/health"
            assert "Connection error" in result.details["error"]
            assert result.error == "Connection error"

    @pytest.mark.asyncio
    async def test_api_health_check_success(self, health_checker, mock_config):
        """Test successful API health check."""
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            mock_client.get_json = AsyncMock(return_value={"elements": [{"id": "1"}, {"id": "2"}]})

            result = await health_checker._check_api_health()

            assert result.status == HealthStatus.HEALTHY
            assert result.details["endpoint"] == "/api/elements"
            assert result.details["has_response"] is True
            assert result.details["element_count"] == 2
            assert result.error is None

    @pytest.mark.asyncio
    async def test_api_health_check_degraded(self, health_checker, mock_config):
        """Test API health check with degraded performance."""
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            # Mock slow response
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(2.5)  # Simulate slow response
                return []

            mock_client.get_json = slow_response

            result = await health_checker._check_api_health()

            assert result.status == HealthStatus.DEGRADED
            assert result.details["endpoint"] == "/api/elements"
            assert result.response_time_ms > 2000  # Should be > 2 seconds

    @pytest.mark.asyncio
    async def test_api_health_check_failure(self, health_checker, mock_config):
        """Test failed API health check."""
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            mock_client.get_json = AsyncMock(return_value=None)

            result = await health_checker._check_api_health()

            assert result.status == HealthStatus.UNHEALTHY
            assert result.details["endpoint"] == "/api/elements"
            assert result.details["has_response"] is False

    @pytest.mark.asyncio
    async def test_combined_health_results(self, health_checker, mock_config):
        """Test combining multiple health check results."""
        primary_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            response_time_ms=100.0,
            timestamp=time.time(),
            details={"endpoint": "/health"},
        )

        api_result = HealthCheckResult(
            status=HealthStatus.DEGRADED,
            response_time_ms=200.0,
            timestamp=time.time(),
            details={"endpoint": "/api/elements"},
        )

        combined = health_checker._combine_health_results(primary_result, api_result)

        # Should take worst status (degraded)
        assert combined.status == HealthStatus.DEGRADED
        assert combined.response_time_ms == 150.0  # Average of 100 and 200
        assert "primary_health" in combined.details
        assert "api_health" in combined.details

    @pytest.mark.asyncio
    async def test_resource_monitoring_success(self, health_checker, mock_config):
        """Test successful resource monitoring."""
        with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
            mock_pm.process_pid = 1234

            with patch("psutil.Process") as mock_process:
                mock_proc = Mock()
                mock_proc.cpu_percent.return_value = 45.0
                mock_proc.memory_info.return_value = Mock(rss=134217728)  # 128 MB
                mock_proc.memory_percent.return_value = 65.0
                mock_proc.status.return_value = "running"
                mock_proc.num_threads.return_value = 8
                mock_process.return_value = mock_proc

                resources = await health_checker._check_resource_usage()

                assert resources["cpu_percent"] == 45.0
                assert resources["memory_mb"] == 128.0
                assert resources["memory_percent"] == 65.0
                assert resources["status"] == "running"
                assert resources["num_threads"] == 8
                assert resources["cpu_threshold_exceeded"] is False
                assert resources["memory_threshold_exceeded"] is False

    @pytest.mark.asyncio
    async def test_resource_monitoring_threshold_exceeded(
        self, health_checker, mock_config
    ):
        """Test resource monitoring with thresholds exceeded."""
        with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
            mock_pm.process_pid = 1234

            with patch("psutil.Process") as mock_process:
                mock_proc = Mock()
                mock_proc.cpu_percent.return_value = 85.0  # Exceeds 80% threshold
                mock_proc.memory_info.return_value = Mock(rss=1073741824)  # 1 GB
                mock_proc.memory_percent.return_value = 90.0  # Exceeds 85% threshold
                mock_proc.status.return_value = "running"
                mock_proc.num_threads.return_value = 12
                mock_process.return_value = mock_proc

                resources = await health_checker._check_resource_usage()

                assert resources["cpu_threshold_exceeded"] is True
                assert resources["memory_threshold_exceeded"] is True

    @pytest.mark.asyncio
    async def test_resource_monitoring_no_process(self, health_checker, mock_config):
        """Test resource monitoring when process is not available."""
        with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
            mock_pm.process_pid = None

            resources = await health_checker._check_resource_usage()

            assert "error" in resources
            assert resources["error"] == "No process PID available"

    @pytest.mark.asyncio
    async def test_resource_monitoring_process_not_found(
        self, health_checker, mock_config
    ):
        """Test resource monitoring when process is not found."""
        with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
            mock_pm.process_pid = 9999

            with patch("psutil.Process") as mock_process:
                mock_process.side_effect = psutil.NoSuchProcess(9999)

                resources = await health_checker._check_resource_usage()

                assert "error" in resources
                assert resources["error"] == "Canvas server process not found"

    @pytest.mark.asyncio
    async def test_comprehensive_health_check(self, health_checker, mock_config):
        """Test comprehensive health check with all components."""
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            # Mock successful health checks
            mock_client.check_health = AsyncMock(return_value=True)
            mock_client.get_json = AsyncMock(return_value=[])

            with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
                mock_pm.process_pid = 1234

                with patch("psutil.Process") as mock_process:
                    mock_proc = Mock()
                    mock_proc.cpu_percent.return_value = 35.0
                    mock_proc.memory_info.return_value = Mock(rss=67108864)
                    mock_proc.memory_percent.return_value = 50.0
                    mock_proc.status.return_value = "running"
                    mock_proc.num_threads.return_value = 4
                    mock_process.return_value = mock_proc

                    result = await health_checker.check_health()

                    assert result.status == HealthStatus.HEALTHY
                    assert "primary_health" in result.details
                    assert "api_health" in result.details
                    assert "resources" in result.details
                    assert result.details["resources"]["cpu_percent"] == 35.0

    @pytest.mark.asyncio
    async def test_health_state_tracking(self, health_checker, mock_config):
        """Test health state tracking and failure counting."""
        # Initially no failures
        assert health_checker.get_failure_count() == 0
        assert not health_checker.is_failing()

        # Create failing health result
        failing_result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=1000.0,
            timestamp=time.time(),
            details={},
            error="Connection failed",
        )

        # Update state with failure
        health_checker._update_health_state(failing_result)

        assert health_checker.get_failure_count() == 1
        assert not health_checker.is_failing()  # Not failing until threshold

        # Add more failures to reach threshold
        for _ in range(2):
            health_checker._update_health_state(failing_result)

        assert health_checker.get_failure_count() == 3
        assert health_checker.is_failing()  # Now failing

        # Recovery
        healthy_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            response_time_ms=150.0,
            timestamp=time.time(),
            details={},
        )

        health_checker._update_health_state(healthy_result)

        assert health_checker.get_failure_count() == 0
        assert not health_checker.is_failing()

    @pytest.mark.asyncio
    async def test_response_time_tracking(self, health_checker, mock_config):
        """Test response time tracking and averaging."""
        response_times = [100.0, 150.0, 200.0, 125.0, 175.0]

        for rt in response_times:
            result = HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time_ms=rt,
                timestamp=time.time(),
                details={},
            )
            health_checker._update_health_state(result)

        avg_time = health_checker.get_average_response_time()
        expected_avg = sum(response_times) / len(response_times)

        assert abs(avg_time - expected_avg) < 0.1

    @pytest.mark.asyncio
    async def test_health_summary(self, health_checker, mock_config):
        """Test getting health summary information."""
        # Create some test state
        failing_result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=500.0,
            timestamp=time.time(),
            details={},
        )

        health_checker._update_health_state(failing_result)
        health_checker._update_health_state(failing_result)

        summary = health_checker.get_health_summary()

        assert summary["consecutive_failures"] == 2
        assert summary["is_failing"] is False  # Below threshold
        assert summary["average_response_time_ms"] == 500.0
        assert len(summary["response_time_history"]) == 2
        assert "last_healthy_time" in summary

    @pytest.mark.asyncio
    async def test_reset_failure_count(self, health_checker, mock_config):
        """Test manually resetting failure count."""
        # Create failures
        failing_result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=1000.0,
            timestamp=time.time(),
            details={},
        )

        for _ in range(5):
            health_checker._update_health_state(failing_result)

        assert health_checker.get_failure_count() == 5
        assert health_checker.is_failing()

        # Reset
        health_checker.reset_failure_count()

        assert health_checker.get_failure_count() == 0
        assert not health_checker.is_failing()
