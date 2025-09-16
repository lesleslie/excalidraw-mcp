"""HTTP client management with connection pooling, health caching, and request tracing."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from .config import config
from .retry_utils import RetryConfig, retry_async

logger = logging.getLogger(__name__)


@dataclass
class HealthCacheEntry:
    """Cache entry for health check results."""

    status: bool
    timestamp: float
    failure_count: int = 0


class CanvasHTTPClient:
    """HTTP client for canvas server communication with connection pooling, caching, and tracing."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._health_cache = HealthCacheEntry(status=False, timestamp=0)
        self._lock = asyncio.Lock()

        # Request tracing
        self._request_metrics: dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
        }

    async def __aenter__(self) -> "CanvasHTTPClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            limits = httpx.Limits(
                max_keepalive_connections=config.performance.http_pool_connections,
                max_connections=config.performance.http_pool_maxsize,
                keepalive_expiry=300 if config.performance.http_keep_alive else 0,
            )

            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(config.server.sync_operation_timeout_seconds),
                limits=limits,
                http2=True,
                follow_redirects=True,
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _perform_health_check_request(self, trace_id: str, config: Any) -> bool:
        """Perform a single health check request."""
        try:
            await self._ensure_client()

            # Add tracing headers if enabled
            headers = (
                self._get_tracing_headers(trace_id)
                if config.monitoring.request_tracing_enabled
                else {}
            )

            if self._client is not None:
                response = await self._client.get(
                    f"{config.server.express_url}/health",
                    timeout=config.server.health_check_timeout_seconds,
                    headers=headers,
                )
            else:
                raise RuntimeError("HTTP client not initialized")

            is_healthy: bool = response.status_code == 200
            return is_healthy

        except Exception as e:
            logger.warning(
                f"Canvas server health check failed: {e} (trace: {trace_id})"
            )
            raise  # Re-raise to trigger retry

    async def check_health(
        self, force: bool = False, correlation_id: str | None = None
    ) -> bool:
        """Check canvas server health with caching and tracing."""
        current_time = time.time()
        trace_id = correlation_id or self._generate_correlation_id()

        # Use cached result if recent and not forced
        if (
            not force
            and current_time - self._health_cache.timestamp
            < config.server.health_check_interval_seconds
        ):
            return self._health_cache.status

        async with self._lock:
            # Double-check after acquiring lock
            if (
                not force
                and current_time - self._health_cache.timestamp
                < config.server.health_check_interval_seconds
            ):
                return self._health_cache.status

            start_time = time.time()

            # Configure retry for health checks
            retry_config = RetryConfig(
                base_delay=0.5,  # Quick retries for health checks
                max_delay=5.0,
                exponential_base=config.server.sync_retry_exponential_base,
                jitter=config.server.sync_retry_jitter,
            )

            async def _health_check_request() -> bool:
                return await self._perform_health_check_request(trace_id, config)

            try:
                is_healthy = await retry_async(
                    _health_check_request,
                    retry_config=retry_config,
                    retry_on_exceptions=(Exception,),
                )
            except Exception:
                # On failure, consider server unhealthy
                is_healthy = False

            # Update cache
            self._health_cache = HealthCacheEntry(
                status=is_healthy,
                timestamp=current_time,
                failure_count=0 if is_healthy else self._health_cache.failure_count + 1,
            )

            # Log the result
            response_time = time.time() - start_time
            if is_healthy:
                logger.debug(
                    f"Canvas server health check passed (trace: {trace_id}, time: {response_time:.3f}s)"
                )
                self._update_request_metrics(True, response_time, "GET", "/health")
            else:
                logger.warning(
                    f"Canvas server health check failed: (trace: {trace_id})"
                )
                self._update_request_metrics(False, response_time, "GET", "/health")

            return is_healthy

    async def post_json(
        self,
        endpoint: str,
        data: dict[str, Any],
        retries: int | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any] | None:
        """POST JSON data to canvas server with retries and tracing."""
        retry_count = (
            retries if retries is not None else config.server.sync_retry_attempts
        )

        trace_id = correlation_id or self._generate_correlation_id()
        await self._ensure_client()
        url = f"{config.server.express_url}{endpoint}"

        # Configure retry behavior
        retry_config = RetryConfig(
            max_attempts=retry_count + 1,
            base_delay=config.server.sync_retry_delay_seconds,
            max_delay=config.server.sync_retry_max_delay_seconds,
            exponential_base=config.server.sync_retry_exponential_base,
            jitter=config.server.sync_retry_jitter,
        )

        async def _post_request() -> dict[str, Any] | None:
            start_time = time.time()
            try:
                # Prepare headers with tracing
                headers = {"Content-Type": "application/json"}
                if config.monitoring.request_tracing_enabled:
                    headers.update(self._get_tracing_headers(trace_id))

                if self._client is not None:
                    response = await self._client.post(url, json=data, headers=headers)
                else:
                    raise RuntimeError("HTTP client not initialized")
                response_time = time.time() - start_time

                if response.status_code in (200, 201):
                    self._update_request_metrics(True, response_time, "POST", endpoint)
                    logger.debug(
                        f"POST {endpoint} successful (trace: {trace_id}, time: {response_time:.3f}s)"
                    )
                    result: dict[str, Any] = response.json()
                    return result
                else:
                    self._update_request_metrics(False, response_time, "POST", endpoint)
                    logger.warning(
                        f"Canvas server returned HTTP {response.status_code}: {response.text} (trace: {trace_id})"
                    )
                    # Raise exception to trigger retry
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code}: {response.text}",
                        request=response.request,
                        response=response,
                    )

            except httpx.TimeoutException:
                response_time = time.time() - start_time
                self._update_request_metrics(False, response_time, "POST", endpoint)
                logger.warning(f"Canvas server request timeout (trace: {trace_id})")
                raise

            except Exception as e:
                response_time = time.time() - start_time
                self._update_request_metrics(False, response_time, "POST", endpoint)
                logger.error(f"Canvas server request failed: {e} (trace: {trace_id})")
                raise

        # Use enhanced retry with exponential backoff and jitter
        try:
            return await retry_async(
                _post_request,
                retry_config=retry_config,
                retry_on_exceptions=(
                    httpx.TimeoutException,
                    httpx.HTTPStatusError,
                    Exception,
                ),
            )
        except Exception:
            # Return None on complete failure as per original behavior
            return None

    async def put_json(
        self, endpoint: str, data: dict[str, Any], correlation_id: str | None = None
    ) -> dict[str, Any] | None:
        """PUT JSON data to canvas server with tracing."""
        trace_id = correlation_id or self._generate_correlation_id()
        await self._ensure_client()
        url = f"{config.server.express_url}{endpoint}"

        start_time = time.time()
        try:
            # Prepare headers with tracing
            headers = {"Content-Type": "application/json"}
            if config.monitoring.request_tracing_enabled:
                headers.update(self._get_tracing_headers(trace_id))

            if self._client is not None:
                response = await self._client.put(url, json=data, headers=headers)
            else:
                raise RuntimeError("HTTP client not initialized")
            response_time = time.time() - start_time

            if response.status_code == 200:
                self._update_request_metrics(True, response_time, "PUT", endpoint)
                logger.debug(
                    f"PUT {endpoint} successful (trace: {trace_id}, time: {response_time:.3f}s)"
                )
                result: dict[str, Any] = response.json()
                return result
            else:
                self._update_request_metrics(False, response_time, "PUT", endpoint)
                logger.warning(
                    f"Canvas server PUT returned HTTP {response.status_code}: {response.text} (trace: {trace_id})"
                )
                return None

        except Exception as e:
            response_time = time.time() - start_time
            self._update_request_metrics(False, response_time, "PUT", endpoint)
            logger.error(f"Canvas server PUT request failed: {e} (trace: {trace_id})")
            return None

    async def delete(self, endpoint: str, correlation_id: str | None = None) -> bool:
        """DELETE request to canvas server with tracing."""
        trace_id = correlation_id or self._generate_correlation_id()
        await self._ensure_client()
        url = f"{config.server.express_url}{endpoint}"

        start_time = time.time()
        try:
            # Prepare headers with tracing
            headers = (
                self._get_tracing_headers(trace_id)
                if config.monitoring.request_tracing_enabled
                else {}
            )

            if self._client is not None:
                response = await self._client.delete(url, headers=headers)
            else:
                raise RuntimeError("HTTP client not initialized")
            response_time = time.time() - start_time

            success = response.status_code in (200, 204)
            self._update_request_metrics(success, response_time, "DELETE", endpoint)

            if success:
                logger.debug(
                    f"DELETE {endpoint} successful (trace: {trace_id}, time: {response_time:.3f}s)"
                )
            else:
                logger.warning(
                    f"DELETE {endpoint} failed with HTTP {response.status_code} (trace: {trace_id})"
                )

            return success

        except Exception as e:
            response_time = time.time() - start_time
            self._update_request_metrics(False, response_time, "DELETE", endpoint)
            logger.error(
                f"Canvas server DELETE request failed: {e} (trace: {trace_id})"
            )
            return False

    async def get_json(
        self, endpoint: str, correlation_id: str | None = None
    ) -> dict[str, Any] | None:
        """GET JSON data from canvas server with tracing."""
        trace_id = correlation_id or self._generate_correlation_id()
        await self._ensure_client()
        url = f"{config.server.express_url}{endpoint}"

        start_time = time.time()
        try:
            # Prepare headers with tracing
            headers = (
                self._get_tracing_headers(trace_id)
                if config.monitoring.request_tracing_enabled
                else {}
            )

            if self._client is not None:
                response = await self._client.get(url, headers=headers)
            else:
                raise RuntimeError("HTTP client not initialized")
            response_time = time.time() - start_time

            if response.status_code == 200:
                self._update_request_metrics(True, response_time, "GET", endpoint)
                logger.debug(
                    f"GET {endpoint} successful (trace: {trace_id}, time: {response_time:.3f}s)"
                )
                result: dict[str, Any] = response.json()
                return result
            else:
                self._update_request_metrics(False, response_time, "GET", endpoint)
                logger.warning(
                    f"Canvas server GET returned HTTP {response.status_code}: {response.text} (trace: {trace_id})"
                )
                return None

        except Exception as e:
            response_time = time.time() - start_time
            self._update_request_metrics(False, response_time, "GET", endpoint)
            logger.error(f"Canvas server GET request failed: {e} (trace: {trace_id})")
            return None

    @property
    def health_failure_count(self) -> int:
        """Get the current health check failure count."""
        return self._health_cache.failure_count

    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for request tracing."""
        return str(uuid.uuid4())[:8]

    def _get_tracing_headers(self, correlation_id: str) -> dict[str, str]:
        """Get headers for request tracing."""
        if not config.monitoring.trace_headers_enabled:
            return {}

        return {
            config.logging.correlation_header: correlation_id,
            "X-Request-ID": correlation_id,
            "X-Trace-ID": correlation_id,
        }

    def _update_request_metrics(
        self, success: bool, response_time: float, method: str, endpoint: str
    ) -> None:
        """Update request metrics for monitoring."""
        self._request_metrics["total_requests"] += 1
        self._request_metrics["total_response_time"] += response_time

        if success:
            self._request_metrics["successful_requests"] += 1
        else:
            self._request_metrics["failed_requests"] += 1

        # Log slow requests
        if response_time > 1.0:  # Requests over 1 second
            logger.warning(
                f"Slow request: {method} {endpoint} took {response_time:.3f}s"
            )

    def get_request_metrics(self) -> dict[str, Any]:
        """Get request metrics for monitoring."""
        total_requests = max(self._request_metrics["total_requests"], 1)

        return self._request_metrics | {
            "success_rate": (
                self._request_metrics["successful_requests"] / total_requests
            )
            * 100,
            "average_response_time": self._request_metrics["total_response_time"]
            / total_requests,
            "error_rate": (self._request_metrics["failed_requests"] / total_requests)
            * 100,
        }

    def reset_request_metrics(self) -> None:
        """Reset request metrics."""
        self._request_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
        }

    @property
    def is_healthy(self) -> bool:
        """Get the last known health status."""
        return self._health_cache.status


# Global HTTP client instance
http_client = CanvasHTTPClient()
