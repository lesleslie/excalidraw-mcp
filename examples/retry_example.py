#!/usr/bin/env python3
"""
Example script demonstrating the retry utilities.
"""

import asyncio
import random

from excalidraw_mcp.retry_utils import RetryConfig, retry_async, retry_sync


def unreliable_sync_function() -> str:
    """A sync function that randomly fails 70% of the time."""
    if random.random() < 0.7:
        raise Exception("Random failure!")
    return "Success!"


async def unreliable_async_function() -> str:
    """An async function that randomly fails 70% of the time."""
    if random.random() < 0.7:
        raise Exception("Random failure!")
    return "Success!"


def main() -> None:
    """Demonstrate sync retry functionality."""
    print("Demonstrating sync retry functionality...")

    # Configure retry behavior
    retry_config = RetryConfig(
        max_attempts=5,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=True,
    )

    try:
        result = retry_sync(
            unreliable_sync_function,
            retry_config=retry_config,
            retry_on_exceptions=(Exception,),
        )
        print(f"Sync function succeeded: {result}")
    except Exception as e:
        print(f"Sync function failed after all retries: {e}")


async def async_main() -> None:
    """Demonstrate async retry functionality."""
    print("\nDemonstrating async retry functionality...")

    # Configure retry behavior
    retry_config = RetryConfig(
        max_attempts=5,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=True,
    )

    try:
        result = await retry_async(
            unreliable_async_function,
            retry_config=retry_config,
            retry_on_exceptions=(Exception,),
        )
        print(f"Async function succeeded: {result}")
    except Exception as e:
        print(f"Async function failed after all retries: {e}")


if __name__ == "__main__":
    main()
    asyncio.run(async_main())
