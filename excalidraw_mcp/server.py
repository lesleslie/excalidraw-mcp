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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register cleanup function
atexit.register(process_manager.cleanup)

# Initialize FastMCP server
mcp = FastMCP("Excalidraw MCP Server")


async def startup_initialization():
    """Initialize canvas server on startup"""
    logger.info("Starting Excalidraw MCP Server...")

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


def main():
    """Main entry point for the CLI"""
    try:
        # Run startup initialization
        asyncio.run(startup_initialization())

        # Start MCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        # Cleanup is handled by atexit and signal handlers
        pass


if __name__ == "__main__":
    main()
