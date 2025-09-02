"""HTTP client management with connection pooling and health caching."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class HealthCacheEntry:
    """Cache entry for health check results."""

    status: bool
    timestamp: float
    failure_count: int = 0


class CanvasHTTPClient:
    """HTTP client for canvas server communication with connection pooling and caching."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._health_cache = HealthCacheEntry(status=False, timestamp=0)
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_client(self):
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

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_health(self, force: bool = False) -> bool:
        """Check canvas server health with caching."""
        current_time = time.time()

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

            try:
                await self._ensure_client()
                response = await self._client.get(
                    f"{config.server.express_url}/health",
                    timeout=config.server.health_check_timeout_seconds,
                )

                is_healthy = response.status_code == 200

                # Update cache
                self._health_cache = HealthCacheEntry(
                    status=is_healthy,
                    timestamp=current_time,
                    failure_count=0
                    if is_healthy
                    else self._health_cache.failure_count + 1,
                )

                if is_healthy:
                    logger.debug("Canvas server health check passed")
                else:
                    logger.warning(
                        f"Canvas server health check failed: HTTP {response.status_code}"
                    )

                return is_healthy

            except Exception as e:
                logger.warning(f"Canvas server health check failed: {e}")

                # Update cache with failure
                self._health_cache = HealthCacheEntry(
                    status=False,
                    timestamp=current_time,
                    failure_count=self._health_cache.failure_count + 1,
                )

                return False

    async def post_json(
        self, endpoint: str, data: dict[str, Any], retries: int = None
    ) -> dict[str, Any] | None:
        """POST JSON data to canvas server with retries."""
        if retries is None:
            retries = config.server.sync_retry_attempts

        await self._ensure_client()
        url = f"{config.server.express_url}{endpoint}"

        for attempt in range(retries + 1):
            try:
                response = await self._client.post(
                    url, json=data, headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 201:
                    return response.json()
                else:
                    logger.warning(
                        f"Canvas server returned HTTP {response.status_code}: {response.text}"
                    )
                    if attempt < retries:
                        await asyncio.sleep(config.server.sync_retry_delay_seconds)
                        continue
                    return None

            except httpx.TimeoutException:
                logger.warning(
                    f"Canvas server request timeout (attempt {attempt + 1}/{retries + 1})"
                )
                if attempt < retries:
                    await asyncio.sleep(config.server.sync_retry_delay_seconds)
                    continue
                return None

            except Exception as e:
                logger.error(f"Canvas server request failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(config.server.sync_retry_delay_seconds)
                    continue
                return None

        return None

    async def put_json(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """PUT JSON data to canvas server."""
        await self._ensure_client()
        url = f"{config.server.express_url}{endpoint}"

        try:
            response = await self._client.put(
                url, json=data, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Canvas server PUT returned HTTP {response.status_code}: {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Canvas server PUT request failed: {e}")
            return None

    async def delete(self, endpoint: str) -> bool:
        """DELETE request to canvas server."""
        await self._ensure_client()
        url = f"{config.server.express_url}{endpoint}"

        try:
            response = await self._client.delete(url)
            return response.status_code in (200, 204)

        except Exception as e:
            logger.error(f"Canvas server DELETE request failed: {e}")
            return False

    async def get_json(self, endpoint: str) -> dict[str, Any] | None:
        """GET JSON data from canvas server."""
        await self._ensure_client()
        url = f"{config.server.express_url}{endpoint}"

        try:
            response = await self._client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Canvas server GET returned HTTP {response.status_code}: {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Canvas server GET request failed: {e}")
            return None

    @property
    def health_failure_count(self) -> int:
        """Get the current health check failure count."""
        return self._health_cache.failure_count

    @property
    def is_healthy(self) -> bool:
        """Get the last known health status."""
        return self._health_cache.status


# Global HTTP client instance
http_client = CanvasHTTPClient()
