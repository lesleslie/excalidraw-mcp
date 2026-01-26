#!/usr/bin/env python3
"""Excalidraw MCP Server - Python FastMCP Implementation
Provides MCP tools for creating and managing Excalidraw diagrams with canvas sync.
"""

import asyncio
import atexit
import importlib.util
import logging
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Check ServerPanels availability (Phase 3.3 M2: improved pattern)
SERVERPANELS_AVAILABLE = importlib.util.find_spec("mcp_common.ui") is not None

# Import security availability flag (Phase 3 Security Hardening)
from .config import SECURITY_AVAILABLE
from .monitoring.supervisor import MonitoringSupervisor

# Initialize FastMCP server
mcp = FastMCP("Excalidraw MCP Server")

# Register MCP tools
from .mcp_tools import MCPToolsManager

tools_manager = MCPToolsManager(mcp)

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
        # Register cleanup function
        atexit.register(process_manager.cleanup)
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


def cleanup_monitoring() -> None:
    if monitoring_supervisor.is_running:
        from contextlib import suppress

        with suppress(RuntimeError):
            asyncio.create_task(monitoring_supervisor.stop())


def main() -> None:
    """Main entry point for the CLI"""
    try:
        # Display beautiful startup message with ServerPanels (or fallback to plain text)
        if SERVERPANELS_AVAILABLE:
            from mcp_common.ui import ServerPanels

            # Build features list with optional security feature
            features = [
                "🎨 Canvas Management",
                "  • Create, update, and query elements",
                "  • Group/ungroup operations",
                "  • Align and distribute elements",
                "🔒 Element Locking & State Control",
                "  • Lock/unlock elements",
                "  • Batch operations support",
                "⚡ Real-time Canvas Sync",
                "  • Background monitoring supervisor",
                "  • Process management",
                "🎨 Modern FastMCP Architecture",
            ]
            if SECURITY_AVAILABLE:
                features.append("🔒 JWT Secret Validation (32+ chars)")

            ServerPanels.startup_success(
                server_name="Excalidraw MCP",
                version="0.34.0",
                features=features,
                endpoint="http://localhost:3032/mcp",
            )
        else:
            # Fallback to plain text
            logger.info("Starting Excalidraw MCP Server...")
            logger.info("  Endpoint: http://localhost:3032/mcp")
            logger.info("  Canvas management & real-time sync enabled")

        # Ensure canvas is running (idempotent - checks if already running first)
        init_background_services()

        # Run the FastMCP server in HTTP mode
        mcp.run(transport="http", host="localhost", port=3032)

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


def init_background_services() -> None:
    """Initialize background services without asyncio conflicts."""
    import os
    import subprocess
    import time

    # Start canvas server directly via subprocess if not running
    try:
        import requests

        # Check if canvas server is already running
        requests.get("http://localhost:3031/health", timeout=1)
        logger.info("Canvas server already running")
    except (requests.RequestException, ConnectionError, OSError):
        logger.info("Starting canvas server...")

        # Find server.js (same logic as process_manager for uvx compatibility)
        server_js = _find_server_js()
        if not server_js:
            logger.error("Could not find canvas server (dist/server.js)")
            logger.warning("Canvas server will not be started")
            return

        logger.info(f"Starting canvas server from {server_js}")

        # Start canvas server in background using node directly (works with uv run/uvx)
        subprocess.Popen(
            ["node", str(server_js)],
            cwd=str(server_js.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid if os.name != "nt" else None,
        )

        # Wait for it to be ready
        for i in range(30):
            try:
                requests.get("http://localhost:3031/health", timeout=1)
                logger.info("Canvas server is ready")
                break
            except (requests.RequestException, ConnectionError, OSError):
                time.sleep(1)
        else:
            logger.warning("Canvas server may not be ready")

    logger.info("Background services initialized")


def _find_server_js() -> Path | None:
    """Find the canvas server.js file.

    Looks in multiple locations to support both:
    - Local development (project root/dist/server.js)
    - uv run/uvx installation (package/dist/server.js bundled in wheel)
    """
    current_file = Path(__file__).resolve()
    package_dir = current_file.parent  # excalidraw_mcp/

    # Candidate locations for server.js
    candidates = [
        # Bundled in package (uvx/pip install)
        package_dir / "dist" / "server.js",
        # Development: project root
        package_dir.parent / "dist" / "server.js",
    ]

    for candidate in candidates:
        if candidate.exists():
            logger.debug(f"Found canvas server at: {candidate}")
            return candidate

    logger.warning(f"Canvas server not found. Searched: {candidates}")
    return None


# Export ASGI app for uvicorn (standardized startup pattern)
http_app = mcp.http_app


def ensure_canvas_running() -> None:
    """Ensure canvas server is running.

    This checks if canvas is already running and starts it if not.
    Unlike auto-start, this always attempts to start the canvas
    regardless of the CANVAS_AUTO_START setting.
    """
    init_background_services()


# Track if auto-start has been performed to avoid duplicate calls
_canvas_auto_started = False


def _auto_start_canvas() -> None:
    """Auto-start canvas on module load if configured.
    
    Only runs once per process, even if module is re-imported.
    """
    global _canvas_auto_started
    if _canvas_auto_started:
        return
    
    from .config import config

    if config.server.canvas_auto_start:
        logger.info("CANVAS_AUTO_START enabled, starting canvas server...")
        init_background_services()
        _canvas_auto_started = True


# Perform auto-start check on module import
_auto_start_canvas()


if __name__ == "__main__":
    main()
