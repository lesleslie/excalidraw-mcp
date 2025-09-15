#!/usr/bin/env python3
"""
Excalidraw MCP Server - Python FastMCP Implementation
Provides MCP tools for creating and managing Excalidraw diagrams with canvas sync.
"""

import asyncio
import atexit
import logging
import signal
from typing import Any

from fastmcp import FastMCP

from .monitoring.supervisor import MonitoringSupervisor

# Initialize FastMCP server
mcp = FastMCP("Excalidraw MCP Server", streamable_http_path="/mcp")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
process_manager: Any = None
monitoring_supervisor: Any = None


def get_process_manager() -> Any:
    """Get or create the global process manager instance."""
    global process_manager
    if process_manager is None:
        from .process_manager import CanvasProcessManager

        process_manager = CanvasProcessManager()
    return process_manager


def get_monitoring_supervisor() -> Any:
    """Get or create the global monitoring supervisor instance."""
    global monitoring_supervisor
    if monitoring_supervisor is None:
        from .monitoring.supervisor import MonitoringSupervisor

        monitoring_supervisor = MonitoringSupervisor()
    return monitoring_supervisor


# Initialize monitoring supervisor
monitoring_supervisor = MonitoringSupervisor()

# Register cleanup function
atexit.register(process_manager.cleanup)


def cleanup_monitoring() -> None:
    if monitoring_supervisor.is_running:
        try:
            asyncio.create_task(monitoring_supervisor.stop())
        except RuntimeError:
            # No running event loop, monitoring supervisor will clean up naturally
            pass


async def startup_initialization() -> None:
    """Initialize canvas server and monitoring on startup"""
    logger.info("Starting Excalidraw MCP Server...")
    # Initialize components
    process_manager = get_process_manager()
    monitoring_supervisor = get_monitoring_supervisor()

    # Start canvas server
    await process_manager.start()

    # Start monitoring
    monitoring_supervisor.start_monitoring()

    logger.info("Excalidraw MCP Server started successfully")


def main() -> None:
    """Main entry point for the CLI"""

    async def shutdown() -> None:
        """Graceful shutdown procedure."""
        logger.info("Starting graceful shutdown...")
        process_manager = get_process_manager()
        monitoring_supervisor = get_monitoring_supervisor()

        # Stop monitoring first
        monitoring_supervisor.stop_monitoring()

        # Stop canvas server
        await process_manager.stop()

        logger.info("Graceful shutdown completed")

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, lambda signum, frame: asyncio.create_task(shutdown()))
    signal.signal(signal.SIGINT, lambda signum, frame: asyncio.create_task(shutdown()))

    try:
        logger.info("Starting Excalidraw MCP Server...")
        asyncio.run(startup_initialization())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
