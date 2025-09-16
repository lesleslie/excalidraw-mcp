"""Retry utilities with exponential backoff and jitter for robust error handling."""

import asyncio
import functools
import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from .config import config

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.1,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor


def calculate_delay(
    attempt: int, config: RetryConfig, exception: Exception | None = None
) -> float:
    """Calculate delay with exponential backoff and optional jitter."""
    # Exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base**attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter if enabled
    if config.jitter:
        jitter_amount = delay * config.jitter_factor
        delay += random.uniform(-jitter_amount, jitter_amount)
        # Ensure delay doesn't go below base_delay
        delay = max(delay, config.base_delay)

    return delay


async def retry_async[T](
    func: Callable[..., Awaitable[T]],
    retry_config: RetryConfig | None = None,
    retry_on_exceptions: tuple[type[Exception], ...] | None = None,
    on_retry: Callable[[int, Exception], Awaitable[None]] | None = None,
) -> T:
    """Execute an async function with retry logic.

    Args:
        func: The async function to execute
        retry_config: Configuration for retry behavior
        retry_on_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called on each retry

    Returns:
        The result of the function call

    Raises:
        The last exception encountered after all retries are exhausted
    """
    if retry_config is None:
        retry_config = RetryConfig(
            max_attempts=config.server.sync_retry_attempts,
            base_delay=config.server.sync_retry_delay_seconds,
        )

    if retry_on_exceptions is None:
        retry_on_exceptions = (Exception,)

    last_exception: Exception | None = None

    for attempt in range(retry_config.max_attempts):
        try:
            return await func()
        except retry_on_exceptions as e:
            last_exception = e

            # If this is the last attempt, don't retry
            if attempt == retry_config.max_attempts - 1:
                logger.error(
                    f"Function {func.__name__} failed after {retry_config.max_attempts} attempts. "
                    f"Last error: {e}"
                )
                raise

            # Calculate delay
            delay = calculate_delay(attempt, retry_config, e)

            logger.warning(
                f"Attempt {attempt + 1} of {func.__name__} failed: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )

            # Call retry callback if provided
            if on_retry:
                try:
                    await on_retry(attempt + 1, e)
                except Exception as callback_error:
                    logger.warning(f"Error in retry callback: {callback_error}")

            # Wait before retrying
            await asyncio.sleep(delay)

    # This should never be reached due to the raise in the loop,
    # but included for type safety
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop ended without an exception")


def retry_sync[T](
    func: Callable[..., T],
    retry_config: RetryConfig | None = None,
    retry_on_exceptions: tuple[type[Exception], ...] | None = None,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> T:
    """Execute a sync function with retry logic.

    Args:
        func: The sync function to execute
        retry_config: Configuration for retry behavior
        retry_on_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called on each retry

    Returns:
        The result of the function call

    Raises:
        The last exception encountered after all retries are exhausted
    """
    if retry_config is None:
        retry_config = RetryConfig(
            max_attempts=config.server.sync_retry_attempts,
            base_delay=config.server.sync_retry_delay_seconds,
        )

    if retry_on_exceptions is None:
        retry_on_exceptions = (Exception,)

    last_exception: Exception | None = None

    for attempt in range(retry_config.max_attempts):
        try:
            return func()
        except retry_on_exceptions as e:
            last_exception = e

            # If this is the last attempt, don't retry
            if attempt == retry_config.max_attempts - 1:
                logger.error(
                    f"Function {func.__name__} failed after {retry_config.max_attempts} attempts. "
                    f"Last error: {e}"
                )
                raise

            # Calculate delay
            delay = calculate_delay(attempt, retry_config, e)

            logger.warning(
                f"Attempt {attempt + 1} of {func.__name__} failed: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )

            # Call retry callback if provided
            if on_retry:
                try:
                    on_retry(attempt + 1, e)
                except Exception as callback_error:
                    logger.warning(f"Error in retry callback: {callback_error}")

            # Wait before retrying
            time.sleep(delay)

    # This should never be reached due to the raise in the loop,
    # but included for type safety
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop ended without an exception")


def retry_decorator(
    retry_config: RetryConfig | None = None,
    retry_on_exceptions: tuple[type[Exception], ...] | None = None,
    on_retry: Callable[[int, Exception], Any] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for adding retry logic to functions.

    Args:
        retry_config: Configuration for retry behavior
        retry_on_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called on each retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            def sync_func() -> T:
                return func(*args, **kwargs)

            return retry_sync(
                sync_func,
                retry_config=retry_config,
                retry_on_exceptions=retry_on_exceptions,
                on_retry=on_retry,
            )

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            async def async_func() -> T:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    coro_result: T = await result
                    return coro_result
                return result

            return await retry_async(
                async_func,
                retry_config=retry_config,
                retry_on_exceptions=retry_on_exceptions,
                on_retry=on_retry,
            )

        # Check if function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper

    return decorator
