"""Tests for the monitoring supervisor module."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch

from excalidraw_mcp.config import config
from excalidraw_mcp.monitoring.supervisor import MonitoringSupervisor
from excalidraw_mcp.monitoring.health_checker import HealthStatus, HealthCheckResult


class TestMonitoringSupervisor:
    """Test cases for MonitoringSupervisor."""

    @pytest.fixture
    def supervisor(self):
        """Create a fresh monitoring supervisor for testing."""
        return MonitoringSupervisor()

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch.object(config.monitoring, 'enabled', True), \
             patch.object(config.monitoring, 'health_check_interval_seconds', 1), \
             patch.object(config.monitoring, 'consecutive_failure_threshold', 3):
            yield config

    @pytest.mark.asyncio
    async def test_supervisor_start_stop(self, supervisor, mock_config):
        """Test supervisor start and stop functionality."""
        # Mock metrics collector
        supervisor.metrics_collector.start_collection = AsyncMock()
        supervisor.metrics_collector.stop_collection = AsyncMock()
        
        # Test start
        await supervisor.start()
        assert supervisor.is_running
        assert supervisor._monitoring_task is not None
        supervisor.metrics_collector.start_collection.assert_called_once()
        
        # Test stop
        await supervisor.stop()
        assert not supervisor.is_running
        supervisor.metrics_collector.stop_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_supervisor_disabled_monitoring(self, supervisor):
        """Test supervisor behavior when monitoring is disabled."""
        with patch.object(config.monitoring, 'enabled', False):
            await supervisor.start()
            assert not supervisor.is_running
            assert supervisor._monitoring_task is None

    @pytest.mark.asyncio
    async def test_health_check_success(self, supervisor, mock_config):
        """Test successful health check handling."""
        # Mock health checker
        healthy_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            response_time_ms=100.0,
            timestamp=time.time(),
            details={"endpoint": "/health"}
        )
        supervisor.health_checker.check_health = AsyncMock(return_value=healthy_result)
        supervisor.circuit_breaker.call = AsyncMock(return_value=healthy_result)
        
        # Mock metrics collector
        supervisor.metrics_collector.increment_counter = Mock()
        supervisor.metrics_collector.observe_histogram = Mock()
        supervisor.metrics_collector.set_gauge = Mock()
        
        # Perform health check
        result = await supervisor._perform_monitored_health_check()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 100.0
        supervisor.metrics_collector.increment_counter.assert_called()
        supervisor.metrics_collector.observe_histogram.assert_called()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, supervisor, mock_config):
        """Test health check failure handling."""
        # Mock health checker to fail
        supervisor.health_checker.check_health = AsyncMock(
            side_effect=Exception("Health check failed")
        )
        supervisor.circuit_breaker.call = AsyncMock(
            side_effect=Exception("Circuit breaker error")
        )
        
        # Mock metrics
        supervisor.metrics_collector.increment_counter = Mock()
        supervisor.metrics_collector.observe_histogram = Mock()
        
        # Perform health check
        result = await supervisor._perform_monitored_health_check()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "Circuit breaker error"
        supervisor.metrics_collector.increment_counter.assert_called()

    @pytest.mark.asyncio
    async def test_automatic_restart_trigger(self, supervisor, mock_config):
        """Test automatic restart when health checks consistently fail."""
        # Mock health checker to be failing
        supervisor.health_checker.is_failing = Mock(return_value=True)
        supervisor.health_checker.get_failure_count = Mock(return_value=5)
        supervisor._attempt_restart = AsyncMock()
        
        # Mock health result
        unhealthy_result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            response_time_ms=5000.0,
            timestamp=time.time(),
            details={"error": "Connection timeout"}
        )
        
        # Handle health failure
        await supervisor._handle_health_status(unhealthy_result)
        
        # Should trigger restart attempt
        supervisor._attempt_restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_success(self, supervisor, mock_config):
        """Test successful canvas server restart."""
        with patch('excalidraw_mcp.monitoring.supervisor.process_manager') as mock_pm:
            mock_pm.restart = AsyncMock(return_value=True)
            
            # Mock metrics and callbacks
            supervisor.metrics_collector.increment_counter = Mock()
            supervisor.health_checker.reset_failure_count = Mock()
            restart_callback = AsyncMock()
            supervisor.add_restart_callback(restart_callback)
            
            # Attempt restart
            await supervisor._attempt_restart()
            
            # Verify restart was attempted and successful
            mock_pm.restart.assert_called_once()
            supervisor.health_checker.reset_failure_count.assert_called_once()
            supervisor.metrics_collector.increment_counter.assert_called()
            restart_callback.assert_called_with(True, 1)

    @pytest.mark.asyncio
    async def test_restart_failure(self, supervisor, mock_config):
        """Test failed canvas server restart."""
        with patch('excalidraw_mcp.monitoring.supervisor.process_manager') as mock_pm:
            mock_pm.restart = AsyncMock(return_value=False)
            
            # Mock callbacks
            restart_callback = AsyncMock()
            supervisor.add_restart_callback(restart_callback)
            
            # Attempt restart
            await supervisor._attempt_restart()
            
            # Verify restart failure was handled
            mock_pm.restart.assert_called_once()
            restart_callback.assert_called_with(False, 1)

    @pytest.mark.asyncio
    async def test_metrics_collection(self, supervisor, mock_config):
        """Test comprehensive metrics collection."""
        # Mock health result with resources
        health_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            response_time_ms=150.0,
            timestamp=time.time(),
            details={
                "resources": {
                    "cpu_percent": 45.0,
                    "memory_percent": 60.0,
                    "memory_mb": 128.5,
                    "num_threads": 4,
                }
            }
        )
        
        # Mock health checker and circuit breaker
        supervisor.health_checker.get_failure_count = Mock(return_value=0)
        supervisor.health_checker.get_average_response_time = Mock(return_value=120.0)
        supervisor.circuit_breaker.get_stats = Mock(return_value={
            "state": "closed",
            "failure_rate_percent": 2.5,
            "failed_calls": 1,
            "total_calls": 40,
        })
        
        with patch('excalidraw_mcp.monitoring.supervisor.process_manager') as mock_pm:
            mock_pm.process_pid = 1234
            
            # Collect metrics
            metrics = await supervisor._collect_monitoring_metrics(health_result)
            
            # Verify metrics
            assert metrics["consecutive_health_failures"] == 0
            assert metrics["health_status"] == "healthy"
            assert metrics["health_response_time"] == 150.0
            assert metrics["avg_health_response_time"] == 120.0
            assert metrics["circuit_state"] == "closed"
            assert metrics["circuit_failure_rate"] == 2.5
            assert metrics["cpu_percent"] == 45.0
            assert metrics["memory_percent"] == 60.0
            assert metrics["process_status"] == "running"

    @pytest.mark.asyncio
    async def test_force_health_check(self, supervisor, mock_config):
        """Test forcing an immediate health check."""
        # Mock health checker
        health_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            response_time_ms=95.0,
            timestamp=time.time(),
            details={"forced": True},
            error=None
        )
        supervisor.health_checker.check_health = AsyncMock(return_value=health_result)
        
        # Force health check
        result = await supervisor.force_health_check()
        
        # Verify result format
        assert result["status"] == "healthy"
        assert result["response_time_ms"] == 95.0
        assert result["details"]["forced"] is True
        assert result["error"] is None
        supervisor.health_checker.check_health.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_manual_restart_trigger(self, supervisor, mock_config):
        """Test manually triggering a restart."""
        with patch('excalidraw_mcp.monitoring.supervisor.process_manager') as mock_pm:
            mock_pm.restart = AsyncMock(return_value=True)
            mock_pm._is_process_running = Mock(return_value=True)
            
            # Trigger manual restart
            success = await supervisor.trigger_restart()
            
            # Verify restart was triggered
            assert success is True
            mock_pm.restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, supervisor, mock_config):
        """Test circuit breaker reset functionality."""
        supervisor.circuit_breaker.reset = Mock()
        
        # Reset circuit breaker
        supervisor.reset_circuit_breaker()
        
        # Verify reset was called
        supervisor.circuit_breaker.reset.assert_called_once()

    @pytest.mark.asyncio 
    async def test_monitoring_status(self, supervisor, mock_config):
        """Test getting comprehensive monitoring status."""
        # Mock component states
        supervisor._running = True
        supervisor._start_time = time.time() - 3600  # 1 hour ago
        supervisor._restart_count = 2
        
        supervisor.health_checker.get_failure_count = Mock(return_value=1)
        supervisor.health_checker.is_failing = Mock(return_value=False)
        supervisor.health_checker.get_last_healthy_time = Mock(return_value=time.time())
        supervisor.health_checker.get_average_response_time = Mock(return_value=125.0)
        
        supervisor.circuit_breaker.get_stats = Mock(return_value={
            "state": "closed",
            "total_calls": 100,
        })
        
        supervisor.metrics_collector._running = True
        supervisor.alert_manager.get_alert_statistics = Mock(return_value={
            "active_alerts": 0,
            "total_alerts_sent": 5,
        })
        
        # Get status
        status = supervisor.get_monitoring_status()
        
        # Verify status structure
        assert status["enabled"] is True
        assert status["running"] is True
        assert status["restart_count"] == 2
        assert "uptime_seconds" in status
        assert "health_checker" in status
        assert "circuit_breaker" in status
        assert "metrics_collector" in status
        assert "alert_manager" in status

    @pytest.mark.asyncio
    async def test_callback_management(self, supervisor):
        """Test callback registration and triggering."""
        # Create mock callbacks
        health_callback = AsyncMock()
        restart_callback = Mock()
        
        # Register callbacks
        supervisor.add_health_change_callback(health_callback)
        supervisor.add_restart_callback(restart_callback)
        
        # Verify callbacks are registered
        assert health_callback in supervisor._on_health_change_callbacks
        assert restart_callback in supervisor._on_restart_callbacks

    @pytest.mark.asyncio
    async def test_monitoring_loop_exception_handling(self, supervisor, mock_config):
        """Test monitoring loop handles exceptions gracefully."""
        # Mock health check to raise exception first time, succeed second time
        call_count = 0
        
        async def mock_health_check():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time_ms=100.0,
                timestamp=time.time(),
                details={}
            )
        
        supervisor._perform_monitored_health_check = mock_health_check
        supervisor._handle_health_status = AsyncMock()
        supervisor._collect_monitoring_metrics = AsyncMock(return_value={})
        supervisor.alert_manager.check_conditions = AsyncMock()
        
        # Start monitoring
        await supervisor.start()
        
        # Let it run for a short time to trigger the exception handling
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        await supervisor.stop()
        
        # Verify it handled the exception and continued running
        assert call_count >= 1
        supervisor._handle_health_status.assert_called()

    @pytest.mark.asyncio
    async def test_get_metrics_and_alerts(self, supervisor, mock_config):
        """Test getting metrics summary and recent alerts."""
        # Mock metrics collector
        supervisor.metrics_collector.get_all_metrics = Mock(return_value={
            "counters": {"test_counter": {"value": 10}},
            "gauges": {"test_gauge": {"value": 50.5}},
            "histograms": {"test_hist": {"count": 5, "average": 2.5}},
        })
        
        # Mock alert manager
        mock_alerts = [
            Mock(title="Test Alert 1", timestamp=time.time()),
            Mock(title="Test Alert 2", timestamp=time.time() - 3600),
        ]
        supervisor.alert_manager.get_alert_history = Mock(return_value=mock_alerts)
        
        # Get metrics and alerts
        metrics = supervisor.get_metrics_summary()
        alerts = supervisor.get_recent_alerts(limit=5)
        
        # Verify results
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics
        assert len(alerts) == 2
        supervisor.alert_manager.get_alert_history.assert_called_once_with(limit=5)