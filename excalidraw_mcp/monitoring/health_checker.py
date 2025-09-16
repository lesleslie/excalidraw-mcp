"""Advanced health checking with multi-level status and degradation detection."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import psutil

from ..config import config
from ..http_client import http_client

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    status: HealthStatus
    response_time_ms: float
    timestamp: float
    details: dict[str, Any]
    error: str | None = None


class HealthChecker:
    """Advanced health checker with multi-endpoint validation and degradation detection."""

    def __init__(self) -> None:
        self._consecutive_failures = 0
        self._last_healthy_time = time.time()
        self._response_times: list[float] = []
        self._max_response_history = 10

        # Health check endpoints to validate
        self._endpoints = [
            {
                "path": "/health",
                "timeout": config.monitoring.health_check_timeout_seconds,
            },
            {
                "path": "/api/elements",
                "timeout": config.monitoring.health_check_timeout_seconds * 1.5,
                "method": "GET",
            },
        ]

    async def check_health(self, force: bool = False) -> HealthCheckResult:
        """Perform comprehensive health check with multiple endpoints."""
        start_time = time.time()

        try:
            # Check basic health endpoint
            primary_result = await self._check_primary_health()

            # Check API functionality if primary is healthy
            if primary_result.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED):
                api_result = await self._check_api_health()

                # Combine results
                combined_result = self._combine_health_results(
                    primary_result, api_result
                )
            else:
                combined_result = primary_result

            # Update internal state
            self._update_health_state(combined_result)

            # Add resource monitoring if enabled
            if config.monitoring.resource_monitoring_enabled:
                combined_result.details[
                    "resources"
                ] = await self._check_resource_usage()

            return combined_result

        except Exception as e:
            error_result = HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={"error": str(e)},
                error=str(e),
            )
            self._update_health_state(error_result)
            return error_result

    async def _check_primary_health(self) -> HealthCheckResult:
        """Check primary health endpoint."""
        start_time = time.time()

        try:
            # Use existing http_client health check but with detailed timing
            is_healthy = await http_client.check_health(force=True)
            response_time_ms = (time.time() - start_time) * 1000

            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY

            return HealthCheckResult(
                status=status,
                response_time_ms=response_time_ms,
                timestamp=time.time(),
                details={
                    "endpoint": "/health",
                    "http_status": 200 if is_healthy else 500,
                    "response_time_ms": response_time_ms,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={"endpoint": "/health", "error": str(e)},
                error=str(e),
            )

    async def _check_api_health(self) -> HealthCheckResult:
        """Check API functionality with elements endpoint."""
        start_time = time.time()

        try:
            result = await http_client.get_json("/api/elements")
            response_time_ms = (time.time() - start_time) * 1000

            # Determine status based on response and timing
            if result is not None:
                # Check if response time indicates degradation
                if (
                    response_time_ms
                    > config.monitoring.health_check_timeout_seconds * 800
                ):  # 80% of timeout
                    status = HealthStatus.DEGRADED
                else:
                    status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.UNHEALTHY

            return HealthCheckResult(
                status=status,
                response_time_ms=response_time_ms,
                timestamp=time.time(),
                details={
                    "endpoint": "/api/elements",
                    "response_time_ms": response_time_ms,
                    "has_response": result is not None,
                    "element_count": len(result.get("elements", []))
                    if isinstance(result, dict) and result is not None
                    else 0,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={"endpoint": "/api/elements", "error": str(e)},
                error=str(e),
            )

    def _combine_health_results(
        self, primary: HealthCheckResult, api: HealthCheckResult
    ) -> HealthCheckResult:
        """Combine multiple health check results into a single result."""
        # Determine overall status (worst case wins)
        status_priority = {
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.RECOVERING: 1,
            HealthStatus.DEGRADED: 2,
            HealthStatus.HEALTHY: 3,
        }

        overall_status = min(
            primary.status, api.status, key=lambda s: status_priority[s]
        )

        # Combine response times (average)
        avg_response_time = (primary.response_time_ms + api.response_time_ms) / 2

        # Combine details
        combined_details = {
            "primary_health": primary.details,
            "api_health": api.details,
            "overall_response_time_ms": avg_response_time,
        }

        return HealthCheckResult(
            status=overall_status,
            response_time_ms=avg_response_time,
            timestamp=max(primary.timestamp, api.timestamp),
            details=combined_details,
        )

    async def _check_resource_usage(self) -> dict[str, Any]:
        """Check resource usage of canvas server process."""
        try:
            from ..process_manager import process_manager

            if not process_manager.process_pid:
                return {"error": "No process PID available"}

            # Get process info
            try:
                process = psutil.Process(process_manager.process_pid)

                # Get CPU and memory usage
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_info = process.memory_info()
                memory_percent = process.memory_percent()

                # Get process status
                status = process.status()
                num_threads = process.num_threads()

                return {
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_info.rss / (1024 * 1024),
                    "memory_percent": memory_percent,
                    "status": status,
                    "num_threads": num_threads,
                    "cpu_threshold_exceeded": cpu_percent
                    > config.monitoring.cpu_threshold_percent,
                    "memory_threshold_exceeded": memory_percent
                    > config.monitoring.memory_threshold_percent,
                }

            except psutil.NoSuchProcess:
                return {"error": "Canvas server process not found"}
            except psutil.AccessDenied:
                return {"error": "Access denied to process information"}

        except Exception as e:
            logger.warning(f"Failed to check resource usage: {e}")
            return {"error": str(e)}

    def _update_health_state(self, result: HealthCheckResult) -> None:
        """Update internal health state based on check result."""
        # Track response times for performance monitoring
        self._response_times.append(result.response_time_ms)
        if len(self._response_times) > self._max_response_history:
            self._response_times.pop(0)

        # Update failure tracking
        if result.status == HealthStatus.HEALTHY:
            self._consecutive_failures = 0
            self._last_healthy_time = result.timestamp
        else:
            self._consecutive_failures += 1

    def is_failing(self) -> bool:
        """Check if health checks are consistently failing."""
        return (
            self._consecutive_failures
            >= config.monitoring.consecutive_failure_threshold
        )

    def get_failure_count(self) -> int:
        """Get current consecutive failure count."""
        return self._consecutive_failures

    def get_average_response_time(self) -> float:
        """Get average response time from recent checks."""
        if not self._response_times:
            return 0.0
        return sum(self._response_times) / len(self._response_times)

    def get_last_healthy_time(self) -> float:
        """Get timestamp of last healthy check."""
        return self._last_healthy_time

    def reset_failure_count(self) -> None:
        """Reset failure count (useful after recovery)."""
        self._consecutive_failures = 0

    def get_health_summary(self) -> dict[str, Any]:
        """Get summary of health checker state."""
        return {
            "consecutive_failures": self._consecutive_failures,
            "last_healthy_time": self._last_healthy_time,
            "average_response_time_ms": self.get_average_response_time(),
            "is_failing": self.is_failing(),
            "response_time_history": self._response_times.copy(),
        }
