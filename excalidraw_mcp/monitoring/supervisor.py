"""Main monitoring supervisor that orchestrates all monitoring components."""

import asyncio
import logging
import time
from typing import Any

from ..config import config
from .alerts import AlertManager
from .circuit_breaker import CircuitBreaker
from .health_checker import HealthChecker, HealthCheckResult, HealthStatus
from .metrics import MetricsCollector

logger = logging.getLogger(__name__)


class MonitoringSupervisor:
    """Orchestrates all monitoring components for canvas server oversight."""

    def __init__(self) -> None:
        # Core monitoring components
        self.health_checker = HealthChecker()
        self.circuit_breaker = CircuitBreaker()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()

        # Supervisor state
        self._running = False
        self._monitoring_task: asyncio.Task | None = None
        self._restart_count = 0
        self._start_time = time.time()

        # Event hooks for external integration
        self._on_health_change_callbacks: list = []
        self._on_restart_callbacks: list = []

    async def start(self) -> None:
        """Start monitoring supervision."""
        if self._running:
            logger.warning("Monitoring supervisor is already running")
            return

        if not config.monitoring.enabled:
            logger.info("Monitoring is disabled in configuration")
            return

        logger.info("Starting monitoring supervisor...")
        self._running = True
        self._start_time = time.time()

        # Start metrics collection
        await self.metrics_collector.start_collection()

        # Start main monitoring loop
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Monitoring supervisor started successfully")

    async def stop(self) -> None:
        """Stop monitoring supervision."""
        if not self._running:
            return

        logger.info("Stopping monitoring supervisor...")
        self._running = False

        # Stop monitoring loop
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        # Stop metrics collection
        await self.metrics_collector.stop_collection()

        logger.info("Monitoring supervisor stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop that coordinates health checks, metrics, and alerts."""
        while self._running:
            try:
                loop_start_time = time.time()

                # Perform health check
                health_result = await self._perform_monitored_health_check()

                # Handle health status changes
                await self._handle_health_status(health_result)

                # Collect and analyze metrics
                metrics = await self._collect_monitoring_metrics(health_result)

                # Check alert conditions
                await self.alert_manager.check_conditions(metrics)

                # Log monitoring cycle completion
                cycle_duration = time.time() - loop_start_time
                logger.debug(f"Monitoring cycle completed in {cycle_duration:.2f}s")

                # Wait for next cycle
                await asyncio.sleep(config.monitoring.health_check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _perform_monitored_health_check(self) -> HealthCheckResult:
        """Perform health check with metrics tracking."""
        start_time = time.time()

        try:
            # Use circuit breaker for health check
            health_result = await self.circuit_breaker.call(
                self.health_checker.check_health
            )

            # Record metrics
            duration = time.time() - start_time
            self.metrics_collector.increment_counter("health_checks_total")
            self.metrics_collector.observe_histogram(
                "health_check_duration_seconds", duration
            )

            if health_result.status != HealthStatus.HEALTHY:
                self.metrics_collector.increment_counter("health_check_failures_total")

            return health_result  # type: ignore

        except Exception as e:
            # Handle circuit breaker or health check errors
            duration = time.time() - start_time
            self.metrics_collector.increment_counter("health_checks_total")
            self.metrics_collector.increment_counter("health_check_failures_total")
            self.metrics_collector.observe_histogram(
                "health_check_duration_seconds", duration
            )

            logger.error(f"Health check failed: {e}")

            # Return unhealthy result
            from .health_checker import HealthCheckResult

            result = HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=duration * 1000,
                timestamp=time.time(),
                details={"error": str(e)},
                error=str(e),
            )
            return result

    async def _handle_health_status(self, health_result: HealthCheckResult) -> None:
        """Handle health status changes and trigger recovery actions."""
        current_status = health_result.status

        # Update metrics
        self.metrics_collector.set_gauge(
            "health_check_consecutive_failures", self.health_checker.get_failure_count()
        )

        # Handle consecutive failures
        if self.health_checker.is_failing():
            await self._handle_health_failure()

        # Trigger callbacks for status changes
        for callback in self._on_health_change_callbacks:
            try:
                await callback(current_status, health_result)
            except Exception as e:
                logger.error(f"Error in health change callback: {e}")

    async def _handle_health_failure(self) -> None:
        """Handle consistent health check failures with automatic recovery."""
        failure_count = self.health_checker.get_failure_count()

        logger.warning(
            f"Canvas server failing health checks ({failure_count} consecutive failures)"
        )

        # Attempt automatic restart if configured
        if (
            failure_count >= config.monitoring.consecutive_failure_threshold
            and config.server.canvas_auto_start
        ):
            await self._attempt_restart()

    async def _attempt_restart(self) -> None:
        """Attempt to restart the canvas server."""
        try:
            logger.info(
                "Attempting to restart canvas server due to health check failures..."
            )

            from ..process_manager import process_manager

            # Record restart attempt
            self._restart_count += 1
            self.metrics_collector.increment_counter("canvas_restarts_total")

            # Attempt restart
            restart_success = await process_manager.restart()

            if restart_success:
                logger.info("Canvas server restart successful")

                # Reset health checker failure count
                self.health_checker.reset_failure_count()

                # Trigger restart callbacks
                for callback in self._on_restart_callbacks:
                    try:
                        await callback(True, self._restart_count)
                    except Exception as e:
                        logger.error(f"Error in restart callback: {e}")
            else:
                logger.error("Canvas server restart failed")

                # Trigger failure callbacks
                for callback in self._on_restart_callbacks:
                    try:
                        await callback(False, self._restart_count)
                    except Exception as e:
                        logger.error(f"Error in restart callback: {e}")

        except Exception as e:
            logger.error(f"Error during restart attempt: {e}")

    async def _collect_monitoring_metrics(
        self, health_result: HealthCheckResult
    ) -> dict[str, Any]:
        """Collect comprehensive metrics for alerting and analysis."""
        metrics = {}

        try:
            # Health metrics
            metrics.update(
                {
                    "consecutive_health_failures": self.health_checker.get_failure_count(),
                    "health_status": health_result.status.value,
                    "health_response_time": health_result.response_time_ms,
                    "avg_health_response_time": self.health_checker.get_average_response_time(),
                }
            )

            # Circuit breaker metrics
            circuit_stats = self.circuit_breaker.get_stats()
            metrics.update(
                {
                    "circuit_state": circuit_stats["state"],
                    "circuit_failure_rate": circuit_stats["failure_rate_percent"],
                    "circuit_failures": circuit_stats["failed_calls"],
                    "circuit_total_calls": circuit_stats["total_calls"],
                }
            )

            # Resource metrics (if available in health result)
            if "resources" in health_result.details:
                resources = health_result.details["resources"]
                if isinstance(resources, dict) and "error" not in resources:
                    metrics.update(
                        {
                            "cpu_percent": resources.get("cpu_percent", 0),
                            "memory_percent": resources.get("memory_percent", 0),
                            "memory_mb": resources.get("memory_mb", 0),
                            "num_threads": resources.get("num_threads", 0),
                        }
                    )

            # Process status
            from ..process_manager import process_manager

            if process_manager.process_pid:
                metrics["process_status"] = "running"
                metrics["uptime_seconds"] = time.time() - self._start_time
            else:
                metrics["process_status"] = "dead"
                metrics["uptime_seconds"] = 0

            # Monitoring supervisor metrics
            metrics.update(
                {
                    "restart_count": self._restart_count,
                    "supervisor_uptime": time.time() - self._start_time,
                }
            )

        except Exception as e:
            logger.error(f"Error collecting monitoring metrics: {e}")

        return metrics

    def add_health_change_callback(self, callback: Any) -> None:
        """Add callback for health status changes."""
        self._on_health_change_callbacks.append(callback)

    def add_restart_callback(self, callback: Any) -> None:
        """Add callback for restart events."""
        self._on_restart_callbacks.append(callback)

    def get_monitoring_status(self) -> dict[str, Any]:
        """Get comprehensive monitoring status."""
        return {
            "enabled": config.monitoring.enabled,
            "running": self._running,
            "uptime_seconds": time.time() - self._start_time,
            "restart_count": self._restart_count,
            # Component status
            "health_checker": {
                "consecutive_failures": self.health_checker.get_failure_count(),
                "is_failing": self.health_checker.is_failing(),
                "last_healthy_time": self.health_checker.get_last_healthy_time(),
                "avg_response_time": self.health_checker.get_average_response_time(),
            },
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "metrics_collector": {
                "collection_running": self.metrics_collector._running,
                "total_metrics": len(self.metrics_collector._counters)
                + len(self.metrics_collector._gauges)
                + len(self.metrics_collector._histograms),
            },
            "alert_manager": self.alert_manager.get_alert_statistics(),
        }

    async def force_health_check(self) -> dict[str, Any]:
        """Force an immediate health check and return results."""
        health_result = await self.health_checker.check_health(force=True)

        return {
            "status": health_result.status.value,
            "response_time_ms": health_result.response_time_ms,
            "timestamp": health_result.timestamp,
            "details": health_result.details,
            "error": health_result.error,
        }

    async def trigger_restart(self) -> bool:
        """Manually trigger a canvas server restart."""
        logger.info("Manual restart triggered via monitoring supervisor")
        await self._attempt_restart()

        # Return success status
        from ..process_manager import process_manager

        return process_manager._is_process_running()

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker to closed state."""
        asyncio.create_task(self.circuit_breaker.reset())
        logger.info("Circuit breaker reset via monitoring supervisor")

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all collected metrics."""
        return self.metrics_collector.get_all_metrics()

    def get_recent_alerts(self, limit: int = 10) -> list:
        """Get recent alert history."""
        return self.alert_manager.get_alert_history(limit=limit)

    @property
    def is_running(self) -> bool:
        """Check if monitoring supervisor is running."""
        return self._running
