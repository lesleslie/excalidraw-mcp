"""Circuit breaker implementation for preventing cascading failures."""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..config import config

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    state_change_time: float = field(default_factory=time.time)


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """Circuit breaker for canvas server operations."""

    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
        half_open_max_calls: int | None = None,
    ):
        # Use config values or provided overrides
        self._failure_threshold = (
            failure_threshold or config.monitoring.circuit_failure_threshold
        )
        self._recovery_timeout = (
            recovery_timeout or config.monitoring.circuit_recovery_timeout_seconds
        )
        self._half_open_max_calls = (
            half_open_max_calls or config.monitoring.circuit_half_open_max_calls
        )

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            # Check if we should allow the call
            if not self._should_allow_call():
                self._stats.rejected_calls += 1
                raise CircuitBreakerError(
                    f"Circuit breaker is {self._state.value}, blocking call"
                )

            # Track the call
            self._stats.total_calls += 1

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        # Execute the function
        time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Handle success
            await self._on_success()
            return result

        except Exception as e:
            # Handle failure
            await self._on_failure(e)
            raise

    def _should_allow_call(self) -> bool:
        """Determine if a call should be allowed."""
        if self._state == CircuitState.CLOSED:
            return True

        elif self._state == CircuitState.OPEN:
            # Check if enough time has passed to try recovery
            if self._should_attempt_recovery():
                self._transition_to_half_open()
                return True
            return False

        elif self._state == CircuitState.HALF_OPEN:
            # Allow limited calls to test recovery
            return self._half_open_calls < self._half_open_max_calls

        return False  # type: ignore

    def _should_attempt_recovery(self) -> bool:
        """Check if we should attempt recovery from open state."""
        if not self._stats.last_failure_time:
            return False

        return time.time() - self._stats.last_failure_time >= self._recovery_timeout

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self._stats.successful_calls += 1
            self._stats.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # If we've had enough successful calls, close the circuit
                if (
                    self._half_open_calls >= self._half_open_max_calls
                    or self._stats.successful_calls >= self._half_open_max_calls
                ):
                    self._transition_to_closed()

            logger.debug("Circuit breaker: successful call")

    async def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        async with self._lock:
            self._stats.failed_calls += 1
            self._stats.last_failure_time = time.time()

            # Check if we should open the circuit
            if self._state == CircuitState.CLOSED:
                if self._stats.failed_calls >= self._failure_threshold:
                    self._transition_to_open()

            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state should open the circuit
                self._transition_to_open()

            logger.warning(
                f"Circuit breaker: call failed with {type(error).__name__}: {error}"
            )

    def _transition_to_open(self) -> None:
        """Transition circuit to open state."""
        previous_state = self._state
        self._state = CircuitState.OPEN
        self._stats.state_change_time = time.time()
        self._half_open_calls = 0

        logger.warning(
            f"Circuit breaker opened (was {previous_state.value}). "
            f"Failed calls: {self._stats.failed_calls}/{self._stats.total_calls}"
        )

    def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state."""
        previous_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._stats.state_change_time = time.time()
        self._half_open_calls = 0

        logger.info(
            f"Circuit breaker transitioning to half-open (was {previous_state.value})"
        )

    def _transition_to_closed(self) -> None:
        """Transition circuit to closed state."""
        previous_state = self._state
        self._state = CircuitState.CLOSED
        self._stats.state_change_time = time.time()
        self._half_open_calls = 0

        # Reset failure count on successful recovery
        self._stats.failed_calls = 0

        logger.info(
            f"Circuit breaker closed (was {previous_state.value}). Recovery successful."
        )

    async def force_open(self) -> None:
        """Manually force circuit to open state."""
        async with self._lock:
            self._transition_to_open()
            logger.warning("Circuit breaker manually forced open")

    async def force_close(self) -> None:
        """Manually force circuit to closed state."""
        async with self._lock:
            self._transition_to_closed()
            logger.info("Circuit breaker manually forced closed")

    async def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._stats = CircuitStats()
            self._half_open_calls = 0
            logger.info("Circuit breaker reset to initial state")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self._state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self._state == CircuitState.HALF_OPEN

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        failure_rate = (
            self._stats.failed_calls / max(self._stats.total_calls, 1) * 100
            if self._stats.total_calls > 0
            else 0
        )

        return {
            "state": self._state.value,
            "total_calls": self._stats.total_calls,
            "successful_calls": self._stats.successful_calls,
            "failed_calls": self._stats.failed_calls,
            "rejected_calls": self._stats.rejected_calls,
            "failure_rate_percent": round(failure_rate, 2),
            "last_failure_time": self._stats.last_failure_time,
            "last_success_time": self._stats.last_success_time,
            "state_change_time": self._stats.state_change_time,
            "half_open_calls": self._half_open_calls,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout_seconds": self._recovery_timeout,
        }

    def is_healthy(self) -> bool:
        """Check if circuit breaker indicates healthy state."""
        return self._state == CircuitState.CLOSED

    def get_time_until_recovery(self) -> float | None:
        """Get time in seconds until recovery attempt (if in open state)."""
        if self._state != CircuitState.OPEN or not self._stats.last_failure_time:
            return None

        elapsed = time.time() - self._stats.last_failure_time
        remaining = self._recovery_timeout - elapsed

        return max(0, remaining)
