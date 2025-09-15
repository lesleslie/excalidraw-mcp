"""Tests for the circuit breaker module."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch

from excalidraw_mcp.monitoring.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError
)
from excalidraw_mcp.config import config


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a fresh circuit breaker for testing."""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,
            half_open_max_calls=2
        )

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch.object(config.monitoring, 'circuit_failure_threshold', 3), \
             patch.object(config.monitoring, 'circuit_recovery_timeout_seconds', 5), \
             patch.object(config.monitoring, 'circuit_half_open_max_calls', 2):
            yield config

    @pytest.mark.asyncio
    async def test_circuit_closed_success(self, circuit_breaker):
        """Test successful calls when circuit is closed."""
        async def success_func():
            return "success"
        
        # Circuit should start closed
        assert circuit_breaker.state == CircuitState.CLOSED
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        
        stats = circuit_breaker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0
        assert stats["state"] == "closed"

    @pytest.mark.asyncio
    async def test_circuit_closed_failure(self, circuit_breaker):
        """Test failed calls when circuit is closed."""
        async def fail_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception, match="Test failure"):
            await circuit_breaker.call(fail_func)
        
        stats = circuit_breaker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 1
        assert stats["state"] == "closed"

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failure_threshold(self, circuit_breaker):
        """Test circuit opens when failure threshold is reached."""
        async def fail_func():
            raise Exception("Test failure")
        
        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        # Circuit should now be open
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.is_open
        
        # Next call should be rejected
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(fail_func)
        
        stats = circuit_breaker.get_stats()
        assert stats["failed_calls"] == 3
        assert stats["rejected_calls"] == 1
        assert stats["state"] == "open"

    @pytest.mark.asyncio
    async def test_circuit_half_open_recovery(self, circuit_breaker):
        """Test circuit transitions to half-open after recovery timeout."""
        async def fail_func():
            raise Exception("Test failure")
        
        async def success_func():
            return "recovered"
        
        # Fail to open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        assert circuit_breaker.is_open
        
        # Manually set last failure time to simulate timeout passage
        circuit_breaker._stats.last_failure_time = time.time() - 10  # 10 seconds ago
        
        # Next call should transition to half-open
        result = await circuit_breaker.call(success_func)
        assert result == "recovered"
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        
        # Another successful call should close the circuit
        await circuit_breaker.call(success_func)
        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """Test that failure in half-open state reopens circuit."""
        async def fail_func():
            raise Exception("Still failing")
        
        async def success_func():
            return "success"
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        # Simulate recovery timeout
        circuit_breaker._stats.last_failure_time = time.time() - 10
        
        # Transition to half-open with success
        await circuit_breaker.call(success_func)
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        
        # Fail in half-open state
        with pytest.raises(Exception):
            await circuit_breaker.call(fail_func)
        
        # Circuit should be open again
        assert circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_half_open_call_limit(self, circuit_breaker):
        """Test half-open state limits the number of calls."""
        async def success_func():
            return "success"
        
        async def fail_func():
            raise Exception("Test failure")
        
        # Open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        # Simulate recovery timeout
        circuit_breaker._stats.last_failure_time = time.time() - 10
        
        # Make max allowed half-open calls
        for _ in range(2):  # half_open_max_calls = 2
            result = await circuit_breaker.call(success_func)
            assert result == "success"
        
        # Circuit should be closed after successful half-open calls
        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_circuit_statistics(self, circuit_breaker):
        """Test circuit breaker statistics collection."""
        async def success_func():
            return "success"
        
        async def fail_func():
            raise Exception("Test failure")
        
        # Make some calls
        await circuit_breaker.call(success_func)
        await circuit_breaker.call(success_func)
        
        try:
            await circuit_breaker.call(fail_func)
        except Exception:
            pass
        
        stats = circuit_breaker.get_stats()
        
        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["failure_rate_percent"] == 33.33  # 1/3 * 100
        assert "last_success_time" in stats
        assert "state_change_time" in stats

    @pytest.mark.asyncio
    async def test_force_open(self, circuit_breaker):
        """Test manually forcing circuit open."""
        assert circuit_breaker.is_closed
        
        circuit_breaker.force_open()
        
        assert circuit_breaker.is_open
        
        # Calls should be rejected
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(lambda: "test")

    @pytest.mark.asyncio
    async def test_force_close(self, circuit_breaker):
        """Test manually forcing circuit closed."""
        # Open circuit first
        async def fail_func():
            raise Exception("Test failure")
        
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        assert circuit_breaker.is_open
        
        # Force close
        circuit_breaker.force_close()
        
        assert circuit_breaker.is_closed
        
        # Should accept calls again
        result = await circuit_breaker.call(lambda: "recovered")
        assert result == "recovered"

    @pytest.mark.asyncio
    async def test_circuit_reset(self, circuit_breaker):
        """Test resetting circuit breaker to initial state."""
        async def fail_func():
            raise Exception("Test failure")
        
        # Make some calls and open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        assert circuit_breaker.is_open
        
        # Reset
        circuit_breaker.reset()
        
        assert circuit_breaker.is_closed
        
        stats = circuit_breaker.get_stats()
        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0

    @pytest.mark.asyncio
    async def test_recovery_timeout_calculation(self, circuit_breaker):
        """Test time until recovery calculation."""
        async def fail_func():
            raise Exception("Test failure")
        
        # Open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        # Should have time remaining
        time_remaining = circuit_breaker.get_time_until_recovery()
        assert time_remaining is not None
        assert 0 <= time_remaining <= 5  # Recovery timeout is 5 seconds
        
        # Simulate time passage
        circuit_breaker._stats.last_failure_time = time.time() - 10
        time_remaining = circuit_breaker.get_time_until_recovery()
        assert time_remaining == 0  # Should be ready for recovery

    @pytest.mark.asyncio
    async def test_healthy_status(self, circuit_breaker):
        """Test healthy status indication."""
        # Closed circuit is healthy
        assert circuit_breaker.is_healthy()
        
        # Open circuit
        async def fail_func():
            raise Exception("Test failure")
        
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        # Open circuit is not healthy
        assert not circuit_breaker.is_healthy()

    @pytest.mark.asyncio
    async def test_sync_function_call(self, circuit_breaker):
        """Test calling synchronous function through circuit breaker."""
        def sync_success():
            return "sync_success"
        
        def sync_fail():
            raise Exception("Sync failure")
        
        # Test successful sync call
        result = await circuit_breaker.call(sync_success)
        assert result == "sync_success"
        
        # Test failed sync call
        with pytest.raises(Exception, match="Sync failure"):
            await circuit_breaker.call(sync_fail)
        
        stats = circuit_breaker.get_stats()
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, circuit_breaker):
        """Test circuit breaker with concurrent calls."""
        async def slow_success():
            await asyncio.sleep(0.1)
            return "success"
        
        # Make multiple concurrent calls
        tasks = [circuit_breaker.call(slow_success) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert all(result == "success" for result in results)
        
        stats = circuit_breaker.get_stats()
        assert stats["total_calls"] == 5
        assert stats["successful_calls"] == 5

    @pytest.mark.asyncio
    async def test_config_defaults(self, mock_config):
        """Test circuit breaker uses configuration defaults."""
        cb = CircuitBreaker()  # No explicit parameters
        
        assert cb._failure_threshold == 5  # From config
        assert cb._recovery_timeout == 60  # From config
        assert cb._half_open_max_calls == 3  # From config

    @pytest.mark.asyncio
    async def test_state_transitions_logged(self, circuit_breaker, caplog):
        """Test that state transitions are properly logged."""
        import logging
        caplog.set_level(logging.INFO)
        
        async def fail_func():
            raise Exception("Test failure")
        
        # Open circuit (should log transition)
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(fail_func)
        
        # Check that opening was logged
        assert "Circuit breaker opened" in caplog.text
        
        # Force close (should log transition)
        circuit_breaker.force_close()
        
        # Check that closing was logged
        assert "Circuit breaker closed" in caplog.text