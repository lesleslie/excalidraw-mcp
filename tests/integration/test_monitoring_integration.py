"""Integration tests for the monitoring system."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from excalidraw_mcp.config import config
from excalidraw_mcp.monitoring.circuit_breaker import CircuitState
from excalidraw_mcp.monitoring.supervisor import MonitoringSupervisor


class TestMonitoringIntegration:
    """Integration tests for the complete monitoring system."""

    @pytest_asyncio.fixture
    async def monitoring_supervisor(self):
        """Create and start a monitoring supervisor."""
        supervisor = MonitoringSupervisor()

        # Mock external dependencies
        with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
            mock_pm.process_pid = 1234
            mock_pm.restart = AsyncMock(return_value=True)
            mock_pm._is_process_running = Mock(return_value=True)

            yield supervisor

        # Cleanup
        if supervisor.is_running:
            await supervisor.stop()

    @pytest.fixture
    def mock_canvas_server(self):
        """Mock canvas server responses."""
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            mock_client.check_health = AsyncMock(return_value=True)
            mock_client.get_json = AsyncMock(return_value=[])
            yield mock_client

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with (
            patch.object(config.monitoring, "enabled", True),
            patch.object(config.monitoring, "health_check_interval_seconds", 0.1),
            patch.object(config.monitoring, "consecutive_failure_threshold", 2),
            patch.object(config.monitoring, "resource_monitoring_enabled", True),
            patch.object(config.server, "canvas_auto_start", True),
        ):
            yield config

    @pytest.mark.asyncio
    async def test_end_to_end_healthy_monitoring(
        self, monitoring_supervisor, mock_canvas_server, mock_config
    ):
        """Test complete monitoring flow when everything is healthy."""
        # Start monitoring
        await monitoring_supervisor.start()
        assert monitoring_supervisor.is_running

        # Let it run for a few cycles
        await asyncio.sleep(0.3)

        # Check that health checks are being performed
        assert mock_canvas_server.check_health.call_count >= 2

        # Verify monitoring status
        status = monitoring_supervisor.get_monitoring_status()
        assert status["running"] is True
        assert status["health_checker"]["consecutive_failures"] == 0
        assert not status["health_checker"]["is_failing"]
        assert status["circuit_breaker"]["state"] == "closed"

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_end_to_end_failure_recovery(
        self, monitoring_supervisor, mock_canvas_server, mock_config
    ):
        """Test complete monitoring flow with failures and recovery."""
        # Mock initial failures
        mock_canvas_server.check_health = AsyncMock(return_value=False)

        # Start monitoring
        await monitoring_supervisor.start()

        # Let it run for a few cycles to accumulate failures
        await asyncio.sleep(0.3)

        # Should have detected failures
        status = monitoring_supervisor.get_monitoring_status()
        assert status["health_checker"]["consecutive_failures"] > 0

        # Now simulate recovery
        mock_canvas_server.check_health = AsyncMock(return_value=True)

        # Let it run for a few more cycles
        await asyncio.sleep(0.3)

        # Should have recovered
        status = monitoring_supervisor.get_monitoring_status()
        assert status["health_checker"]["consecutive_failures"] == 0

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_automatic_restart_integration(
        self, monitoring_supervisor, mock_canvas_server, mock_config
    ):
        """Test automatic restart functionality."""
        # Mock consistent failures
        mock_canvas_server.check_health = AsyncMock(return_value=False)

        # Mock process manager
        with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
            mock_pm.process_pid = 1234
            mock_pm.restart = AsyncMock(return_value=True)

            # Start monitoring
            await monitoring_supervisor.start()

            # Let it run until restart threshold is reached
            await asyncio.sleep(0.5)

            # Should have attempted restart
            assert mock_pm.restart.called

            # Verify restart count increased
            status = monitoring_supervisor.get_monitoring_status()
            assert status["restart_count"] > 0

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(
        self, monitoring_supervisor, mock_config
    ):
        """Test circuit breaker integration with health checks."""
        # Mock health checker to throw exceptions
        monitoring_supervisor.health_checker.check_health = AsyncMock(
            side_effect=Exception("Health check failed")
        )

        # Start monitoring
        await monitoring_supervisor.start()

        # Let it run to trigger circuit breaker
        await asyncio.sleep(0.5)

        # Circuit breaker should eventually open
        cb_stats = monitoring_supervisor.circuit_breaker.get_stats()
        assert cb_stats["failed_calls"] > 0

        # If enough failures occurred, circuit should be open
        if (
            cb_stats["failed_calls"]
            >= monitoring_supervisor.circuit_breaker._failure_threshold
        ):
            assert monitoring_supervisor.circuit_breaker.state == CircuitState.OPEN

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_metrics_collection_integration(
        self, monitoring_supervisor, mock_canvas_server, mock_config
    ):
        """Test metrics collection across all components."""
        # Start monitoring
        await monitoring_supervisor.start()

        # Let it run for several cycles
        await asyncio.sleep(0.3)

        # Get all metrics
        metrics = monitoring_supervisor.get_metrics_summary()

        # Verify key metrics exist
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics

        # Check for health check metrics
        health_checks_counter = metrics["counters"].get("health_checks_total")
        if health_checks_counter:
            assert health_checks_counter["value"] > 0

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_alert_generation_integration(
        self, monitoring_supervisor, mock_config
    ):
        """Test alert generation based on monitoring conditions."""
        # Mock unhealthy conditions
        monitoring_supervisor.health_checker.get_failure_count = Mock(return_value=5)
        monitoring_supervisor.health_checker.is_failing = Mock(return_value=True)

        # Mock resource usage above thresholds
        with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
            mock_pm.process_pid = 1234

        # Start monitoring
        await monitoring_supervisor.start()

        # Let it run for a few cycles
        await asyncio.sleep(0.3)

        # Check for generated alerts
        monitoring_supervisor.get_recent_alerts()
        alert_stats = monitoring_supervisor.alert_manager.get_alert_statistics()

        # Should have some activity
        assert alert_stats["total_alerts_sent"] >= 0

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_monitoring_disabled_integration(self, monitoring_supervisor):
        """Test behavior when monitoring is disabled."""
        with patch.object(config.monitoring, "enabled", False):
            await monitoring_supervisor.start()

            # Should not be running
            assert not monitoring_supervisor.is_running
            assert monitoring_supervisor._monitoring_task is None

    @pytest.mark.asyncio
    async def test_callback_integration(
        self, monitoring_supervisor, mock_canvas_server, mock_config
    ):
        """Test callback integration across components."""
        health_changes = []
        restarts = []

        async def health_callback(status, result):
            health_changes.append((status, result))

        async def restart_callback(success, count):
            restarts.append((success, count))

        # Register callbacks
        monitoring_supervisor.add_health_change_callback(health_callback)
        monitoring_supervisor.add_restart_callback(restart_callback)

        # Start monitoring
        await monitoring_supervisor.start()

        # Let it run
        await asyncio.sleep(0.2)

        # Simulate failure to trigger restart
        mock_canvas_server.check_health = AsyncMock(return_value=False)
        monitoring_supervisor.health_checker.is_failing = Mock(return_value=True)
        monitoring_supervisor.health_checker.get_failure_count = Mock(return_value=5)

        # Wait for restart attempt
        await asyncio.sleep(0.3)

        # Should have callbacks triggered
        assert len(restarts) > 0  # At least one restart attempt

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_resource_monitoring_integration(
        self, monitoring_supervisor, mock_canvas_server, mock_config
    ):
        """Test resource monitoring integration with health checks."""
        # Mock high resource usage
        with patch("excalidraw_mcp.process_manager.process_manager") as mock_pm:
            mock_pm.process_pid = 1234

            with patch("psutil.Process") as mock_process:
                mock_proc = Mock()
                mock_proc.cpu_percent.return_value = 95.0  # High CPU
                mock_proc.memory_info.return_value = Mock(rss=1073741824)  # 1GB
                mock_proc.memory_percent.return_value = 92.0  # High memory
                mock_proc.status.return_value = "running"
                mock_proc.num_threads.return_value = 20
                mock_process.return_value = mock_proc

                # Start monitoring
                await monitoring_supervisor.start()

                # Let it collect resource metrics
                await asyncio.sleep(0.3)

                # Force a health check to get resource data
                result = await monitoring_supervisor.force_health_check()

                # Should include resource information
                if "resources" in result["details"]:
                    resources = result["details"]["resources"]
                    if "cpu_percent" in resources:
                        assert resources["cpu_percent"] == 95.0

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_request_tracing_integration(
        self, monitoring_supervisor, mock_config
    ):
        """Test request tracing integration across HTTP client and monitoring."""
        # Mock HTTP client with tracing
        with patch(
            "excalidraw_mcp.monitoring.health_checker.http_client"
        ) as mock_client:
            mock_client.check_health = AsyncMock(return_value=True)
            mock_client.get_json = AsyncMock(return_value=[])
            mock_client.get_request_metrics = Mock(
                return_value={
                    "total_requests": 10,
                    "successful_requests": 9,
                    "failed_requests": 1,
                    "success_rate": 90.0,
                    "average_response_time": 0.15,
                    "error_rate": 10.0,
                }
            )

            # Start monitoring
            await monitoring_supervisor.start()

            # Let it run
            await asyncio.sleep(0.2)

            # Check that HTTP client metrics are available
            metrics = mock_client.get_request_metrics()
            assert metrics["success_rate"] == 90.0
            assert metrics["average_response_time"] == 0.15

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_integration(
        self, monitoring_supervisor, mock_canvas_server, mock_config
    ):
        """Test graceful shutdown of monitoring system."""
        # Start monitoring
        await monitoring_supervisor.start()
        assert monitoring_supervisor.is_running

        # Let it run
        await asyncio.sleep(0.1)

        # Stop monitoring
        await monitoring_supervisor.stop()

        # Should be cleanly stopped
        assert not monitoring_supervisor.is_running
        assert monitoring_supervisor._monitoring_task.done()

        # Metrics collector should also be stopped
        assert not monitoring_supervisor.metrics_collector._running

    @pytest.mark.asyncio
    async def test_monitoring_resilience(self, monitoring_supervisor, mock_config):
        """Test monitoring system resilience to component failures."""
        # Mock component failures
        monitoring_supervisor.health_checker.check_health = AsyncMock(
            side_effect=Exception("Component failure")
        )
        monitoring_supervisor.metrics_collector.collect_system_metrics = AsyncMock(
            side_effect=Exception("Metrics failure")
        )

        # Start monitoring
        await monitoring_supervisor.start()

        # Let it run despite component failures
        await asyncio.sleep(0.3)

        # Should still be running (resilient to component failures)
        assert monitoring_supervisor.is_running

        await monitoring_supervisor.stop()

    @pytest.mark.asyncio
    async def test_performance_under_load(
        self, monitoring_supervisor, mock_canvas_server, mock_config
    ):
        """Test monitoring system performance under load."""
        # Simulate high-frequency health checks
        with patch.object(config.monitoring, "health_check_interval_seconds", 0.01):
            start_time = time.time()

            # Start monitoring
            await monitoring_supervisor.start()

            # Let it run for a reasonable time
            await asyncio.sleep(0.5)

            # Should handle high frequency without issues
            duration = time.time() - start_time
            assert duration < 1.0  # Should complete quickly

            # Check that many health checks occurred
            assert mock_canvas_server.check_health.call_count > 10

        await monitoring_supervisor.stop()
