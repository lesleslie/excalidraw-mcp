#!/usr/bin/env python3
"""
Excalidraw MCP Server - Python FastMCP Implementation
Provides MCP tools for creating and managing Excalidraw diagrams with canvas sync.
"""

import asyncio
import atexit
import logging

from fastmcp import FastMCP

from .config import config
from .mcp_tools import MCPToolsManager
from .process_manager import process_manager
from .monitoring.supervisor import MonitoringSupervisor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize monitoring supervisor
monitoring_supervisor = MonitoringSupervisor()

# Register cleanup function
atexit.register(process_manager.cleanup)
atexit.register(lambda: asyncio.create_task(monitoring_supervisor.stop()) if monitoring_supervisor.is_running else None)

# Initialize FastMCP server
mcp = FastMCP("Excalidraw MCP Server")


async def startup_initialization():
    """Initialize canvas server and monitoring on startup"""
    logger.info("Starting Excalidraw MCP Server...")

    # Start canvas server if configured
    if config.server.canvas_auto_start:
        logger.info("Checking canvas server status...")
        is_running = await process_manager.ensure_running()
        if is_running:
            logger.info("Canvas server is ready")
        else:
            logger.warning(
                "Canvas server failed to start - continuing without canvas sync"
            )
    else:
        logger.info("Canvas auto-start disabled")

    # Initialize MCP tools manager
    MCPToolsManager(mcp)
    
    # Start monitoring supervisor
    if config.monitoring.enabled:
        logger.info("Starting monitoring supervisor...")
        await monitoring_supervisor.start()
        logger.info("Monitoring supervisor started")
    else:
        logger.info("Monitoring disabled in configuration")


def main():
    """Main entry point for the CLI"""
    async def shutdown():
        """Graceful shutdown procedure."""
        logger.info("Starting graceful shutdown...")
        if monitoring_supervisor.is_running:
            await monitoring_supervisor.stop()
        logger.info("Shutdown complete")
    
    try:
        # Run startup initialization
        asyncio.run(startup_initialization())

        # Start MCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        asyncio.run(shutdown())
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        asyncio.run(shutdown())
        raise
    finally:
        # Cleanup is handled by atexit and signal handlers
        pass


if __name__ == "__main__":
    main()
