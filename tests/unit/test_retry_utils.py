"""Unit tests for retry utilities."""

import unittest

from excalidraw_mcp.retry_utils import (
    RetryConfig,
    calculate_delay,
    retry_async,
    retry_decorator,
    retry_sync,
)


class TestRetryUtils(unittest.IsolatedAsyncioTestCase):
    """Test cases for retry utilities."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False,
        )

    def test_calculate_delay_no_jitter(self) -> None:
        """Test delay calculation without jitter."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=False,
        )

        # Test exponential backoff
        self.assertAlmostEqual(calculate_delay(0, config), 1.0)  # 1 * 2^0 = 1
        self.assertAlmostEqual(calculate_delay(1, config), 2.0)  # 1 * 2^1 = 2
        self.assertAlmostEqual(calculate_delay(2, config), 4.0)  # 1 * 2^2 = 4
        self.assertAlmostEqual(calculate_delay(3, config), 8.0)  # 1 * 2^3 = 8

        # Test max delay cap
        self.assertAlmostEqual(calculate_delay(10, config), 60.0)  # Capped at max_delay

    def test_calculate_delay_with_jitter(self) -> None:
        """Test delay calculation with jitter."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
            jitter_factor=0.1,
        )

        # Test that jitter adds randomness but stays within bounds
        for attempt in range(5):
            delay = calculate_delay(attempt, config)
            base_delay = config.base_delay * (config.exponential_base**attempt)
            base_delay = min(base_delay, config.max_delay)

            # With 10% jitter, delay should be within 10% of base delay
            self.assertGreaterEqual(delay, base_delay * 0.9)
            self.assertLessEqual(delay, base_delay * 1.1)

    async def test_retry_async_success(self) -> None:
        """Test async retry with immediate success."""

        async def mock_func():
            return "success"

        result = await retry_async(mock_func, self.retry_config)

        self.assertEqual(result, "success")

    async def test_retry_async_eventual_success(self) -> None:
        """Test async retry with eventual success after failures."""
        call_count = 0

        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")
            return "success"

        result = await retry_async(mock_func, self.retry_config)

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    async def test_retry_async_max_attempts_exceeded(self) -> None:
        """Test async retry with all attempts failing."""

        async def mock_func():
            raise Exception("fail")

        with self.assertRaises(Exception) as context:
            await retry_async(mock_func, self.retry_config)

        self.assertEqual(str(context.exception), "fail")

    async def test_retry_async_selective_retry(self) -> None:
        """Test async retry with selective exception handling."""
        call_count = 0

        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("retry me")
            elif call_count == 2:
                raise RuntimeError("dont retry")
            return "success"

        with self.assertRaises(RuntimeError) as context:
            await retry_async(
                mock_func, self.retry_config, retry_on_exceptions=(ValueError,)
            )

        self.assertEqual(str(context.exception), "dont retry")
        # Only first call should be retried, second should raise immediately
        self.assertEqual(call_count, 2)

    async def test_retry_async_with_callback(self) -> None:
        """Test async retry with retry callback."""
        call_count = 0

        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("fail")
            return "success"

        callback_calls = []

        async def callback(attempt, exception):
            callback_calls.append((attempt, str(exception)))

        result = await retry_async(mock_func, self.retry_config, on_retry=callback)

        self.assertEqual(result, "success")
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0], (1, "fail"))

    def test_retry_sync_success(self) -> None:
        """Test sync retry with immediate success."""

        def mock_func():
            return "success"

        result = retry_sync(mock_func, self.retry_config)

        self.assertEqual(result, "success")

    def test_retry_sync_eventual_success(self) -> None:
        """Test sync retry with eventual success after failures."""
        call_count = 0

        def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")
            return "success"

        result = retry_sync(mock_func, self.retry_config)

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    def test_retry_sync_max_attempts_exceeded(self) -> None:
        """Test sync retry with all attempts failing."""

        def mock_func():
            raise Exception("fail")

        with self.assertRaises(Exception) as context:
            retry_sync(mock_func, self.retry_config)

        self.assertEqual(str(context.exception), "fail")

    def test_retry_sync_with_callback(self) -> None:
        """Test sync retry with retry callback."""
        call_count = 0

        def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("fail")
            return "success"

        callback_calls = []

        def callback(attempt, exception):
            callback_calls.append((attempt, str(exception)))

        result = retry_sync(mock_func, self.retry_config, on_retry=callback)

        self.assertEqual(result, "success")
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0], (1, "fail"))

    def test_retry_decorator_sync(self) -> None:
        """Test retry decorator with sync function."""
        call_count = 0

        @retry_decorator(self.retry_config)
        def flaky_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")
            return "success"

        result = flaky_function()

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    async def test_retry_decorator_async(self) -> None:
        """Test retry decorator with async function."""
        call_count = 0

        @retry_decorator(self.retry_config)
        async def flaky_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")
            return "success"

        result = await flaky_function()

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)


if __name__ == "__main__":
    unittest.main()
