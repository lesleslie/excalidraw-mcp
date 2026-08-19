#!/usr/bin/env python3
"""Excalidraw MCP Server - Python FastMCP Implementation
Provides MCP tools for creating and managing Excalidraw diagrams with canvas sync.
"""

from __future__ import annotations

import asyncio
import atexit
import importlib.util
import logging
from typing import Any

from fastmcp import FastMCP

# Check ServerPanels availability (Phase 3.3 M2: improved pattern)
SERVERPANELS_AVAILABLE = importlib.util.find_spec("mcp_common.ui") is not None

# Import security availability flag (Phase 3 Security Hardening)
from .config import SECURITY_AVAILABLE
from .monitoring.supervisor import MonitoringSupervisor

# Initialize FastMCP server (empty — tools are registered lazily via
# ``create_app`` so the W0 ``EXCALIDRAW_TOOL_PROFILE`` dispatch can gate
# the MCP tool set). The ``/healthz`` HTTP route is kept at module-level
# because it is intentionally always-on for orchestrator probes; the HTTP
# ``/health`` route + MCP ``health_check`` tool are registered by
# ``register_health_tool`` (called via ``apply_excalidraw_tool_profile``).
mcp = FastMCP("Excalidraw MCP Server")


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz_check(request: Any) -> Any:
    """Kubernetes-style health check endpoint."""
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok"})


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


def _run_async_safely(coro: Any) -> Any:
    """Run an async coroutine from a sync context, tolerating a running loop.

    Bridges to the async ``create_app`` via ``asyncio.run`` when no loop
    is running (CLI startup, ``__main__.py``). Falls back to a private
    thread executor when a loop is already running (pytest-asyncio tests
    that instantiate the class).

    Tool profile dispatch is async because the W0 helper from
    mcp-common 0.18.0 (``_apply_tool_profile``) is async. Per the
    W2b.3 lesson, the sync ``apply_tool_profile`` wrapper raises
    ``RuntimeError`` when called from inside a running event loop, so
    the async path is the only correct entry point for any async caller.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Loop already running (pytest-asyncio test). Run the coroutine in a
    # private thread with its own fresh loop, mirroring the W3.4 unifi-mcp
    # pattern that avoids blocking the test's loop.
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def create_server(config: Any) -> FastMCP:
    """Create and configure the MCP server (sync wrapper).

    Bridges to the async ``create_app`` via ``_run_async_safely``. Used
    by the existing tests and the CLI startup path. Tests that exercise
    the real async startup should call ``await create_app(...)``
    directly so any W2b.3-style regression in the production dispatch
    path is caught.

    The caller-supplied ``config`` is forwarded through to the
    registration paths so test-injected overrides are preserved
    (the W4.1 round-1 reviewer fix — caller-supplied settings were
    silently discarded before).
    """
    return _run_async_safely(create_app(config))


async def create_app(
    config: Any, server: FastMCP | None = None
) -> FastMCP:
    """Create and configure the MCP server (async production path).

    Async because the W0 tool profile dispatch helper is async.
    Callers from sync contexts (CLI startup, ``get_app``,
    ``create_server``) wrap with ``asyncio.run(create_app(...))``.
    Tests that exercise the real async startup should call
    ``await create_app(...)`` directly so any W2b.3-style regression
    in the production dispatch path is caught.

    Args:
        config: The caller-supplied ``Config`` instance to thread
            through to every group registration. The W4.1 round-1
            reviewer fix: caller-supplied config is preserved (NOT
            re-loaded from env).
        server: Optional FastMCP server instance. Defaults to the
            module-level ``mcp`` singleton. Tests pass a fresh
            instance to avoid mutating the shared singleton.
    """
    if server is None:
        server = mcp

    # Apply tool profile dispatch (EXCALIDRAW_TOOL_PROFILE env var).
    #
    # Replaces the previous eager ``MCPToolsManager(mcp)`` + module-level
    # ``register_http_health_route(mcp, ...)`` calls. The W0 helper from
    # mcp-common 0.18.0+ dispatches by group name and always registers
    # the ``discover_tools`` meta-tool. The default (no env var) remains
    # FULL = all 12 excalidraw tools — the previous behavior is preserved.
    #
    # Per the W2b.3 keystone: this MUST be the async helper, NOT the
    # sync ``apply_tool_profile`` wrapper (which raises RuntimeError in
    # event loops and would silently break any test that runs
    # ``create_app`` under an async context).
    #
    # The caller-supplied ``config`` instance is forwarded through to
    # the registration paths so test-injected configuration overrides
    # are preserved (the W4.1 round-1 reviewer fix — caller-supplied
    # settings were silently discarded before).
    from .tools.profiles import apply_excalidraw_tool_profile

    await apply_excalidraw_tool_profile(server, config)

    return server


def run_server(config: Any) -> None:
    """Start the excalidraw MCP server."""
    _server = create_server(config)
    logger.info(
        "Excalidraw MCP Server starting",
        endpoint=f"http://{config.mcp.http_host}:{config.mcp.http_port}/mcp",
    )

    _server.run(
        transport="http",
        host=config.mcp.http_host,
        port=config.mcp.http_port,
    )


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
                version="0.37.1",
                features=features,
                endpoint="http://localhost:3032/mcp",
            )
        else:
            # Fallback to plain text
            logger.info("Starting Excalidraw MCP Server...")
            logger.info("  Endpoint: http://localhost:3032/mcp")
            logger.info("  Canvas management & real-time sync enabled")

        # Initialize services first using a simple approach
        init_background_services()

        # Create config and apply tool profile dispatch
        from .config import Config

        config = Config()

        # Build server with profile-aware tool registration
        create_server(config)

        # Run the FastMCP server in HTTP mode
        mcp.run(transport="http", host="localhost", port=3032)

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


def init_background_services() -> None:
    """Initialize background services without asyncio conflicts."""
    import subprocess
    import time
    from pathlib import Path

    # Start canvas server directly via subprocess if not running
    try:
        import requests

        # Check if canvas server is already running
        requests.get("http://localhost:3031/health", timeout=1)
        logger.info("Canvas server already running")
    except (requests.RequestException, ConnectionError, OSError):
        logger.info("Starting canvas server...")
        # Dynamically resolve project root (deployment-safe)
        project_root = Path(__file__).parent.parent.resolve()

        # Start canvas server in background
        subprocess.Popen(
            ["npm", "run", "canvas"],
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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


# Global server instance for lazy initialization
_mcp_instance: FastMCP | None = None


def get_app() -> FastMCP:
    """Get or create the FastMCP server instance (lazy initialization)."""
    global _mcp_instance
    if _mcp_instance is None:
        from .config import Config

        _mcp_instance = create_server(Config())
    return _mcp_instance


def __getattr__(name: str) -> Any:
    """Lazy attribute access for uvicorn compatibility.

    Enables `uvicorn excalidraw_mcp.server:http_app --factory` pattern.
    """
    if name == "app":
        return get_app()
    if name == "http_app":
        return get_app().http_app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


if __name__ == "__main__":
    main()
