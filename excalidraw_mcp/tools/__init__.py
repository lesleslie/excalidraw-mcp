"""MCP tool registration groups for excalidraw-mcp.

Maps ``register_<group>`` callables to the W0 tool profile dispatch
hierarchy (see ``excalidraw_mcp.tools.profiles``). Two groups exist:

- ``health_tools`` — registers the MCP ``health_check`` tool plus the
  HTTP ``/health`` readiness route (always available at MINIMAL).
- ``canvas_tools`` — registers the 12 canvas MCP tools (elements,
  groups, locks, batch ops, resources). Tier-A trivial mapping puts
  this group behind STANDARD/FULL.

The split mirrors css-mcp's W4.1 pattern (the only prior Tier-A trivial
reference) and enables ``MINIMAL=health`` without re-loading canvas
state at startup.

Backward-compat: ``MCPToolsManager`` still lives in
``excalidraw_mcp.mcp_tools`` and is re-exported here so existing
``from excalidraw_mcp.mcp_tools import MCPToolsManager`` imports
continue to work. ``register_canvas_tools`` is the new profile-aware
entry point and the recommended surface for new code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_common.fastmcp import FastMCP

    from excalidraw_mcp.config import Config

__all__ = [
    "register_canvas_tools",
    "register_health_tool",
]


def register_health_tool(mcp: FastMCP, config: Config) -> None:
    """Register the MCP ``health_check`` tool plus the HTTP ``/health`` route.

    Split out from the canvas-registration group so the W0 tool profile
    dispatch can expose ``health_check`` independently at the MINIMAL
    profile (the canonical W4.1 mapping: ``MINIMAL=health``). The HTTP
    ``/health`` route is registered alongside the MCP health tool — it
    is load-bearing for launchd / orchestrator readiness probes and
    must stay co-located with the MCP health tool, NOT move into
    ``register_canvas_tools``.

    The MCP-level ``health_check`` tool is intentionally lightweight: it
    returns a static snapshot of service identity and component health.
    It does NOT exercise the canvas subprocess (the canvas HTTP
    endpoint is the source of truth for canvas readiness; if the
    canvas is down, the tool will report that via ``canvas`` key).

    Args:
        mcp: FastMCP server instance.
        config: Server configuration (used for service_name/version
            metadata on the HTTP route response).
    """
    from mcp_common.health import register_http_health_route

    from excalidraw_mcp import __version__

    @mcp.tool()
    async def health_check() -> dict[str, Any]:
        """Check excalidraw-mcp server health.

        Returns:
            Status, version, and component health (canvas subprocess
            state). Pure status check — does not mutate canvas.
        """
        canvas_state = "unknown"
        try:
            # Avoid importing the singleton ``get_process_manager`` at
            # module-import time (would force canvas subprocess state).
            # Use ``process_manager`` global if already initialized,
            # otherwise report ``stopped``.
            from excalidraw_mcp import server as _server_module

            manager = _server_module.process_manager
            if manager is None:
                canvas_state = "stopped"
            else:
                # CanvasProcessManager exposes ``process`` (Popen) and
                # ``process_pid`` (int). Check via psutil so we don't
                # bind to a private helper.
                import psutil

                pid = manager.process_pid
                if pid is not None and psutil.pid_exists(pid):
                    canvas_state = "running"
                else:
                    canvas_state = "stopped"
        except Exception:
            canvas_state = "error"

        return {
            "status": "healthy",
            "service": "excalidraw-mcp",
            "version": __version__,
            "canvas": canvas_state,
        }

    register_http_health_route(
        mcp,
        service_name="excalidraw-mcp",
        version=__version__,
    )


def register_canvas_tools(mcp: FastMCP, config: Config) -> None:
    """Register the 12 canvas MCP tools (elements, groups, locks, batch, resource).

    Wraps ``MCPToolsManager`` so the existing tool implementations stay
    intact — this is the profile-aware entry point that the W0 helper
    will dispatch to at STANDARD/FULL profiles.

    Args:
        mcp: FastMCP server instance.
        config: Server configuration (currently unused at the tool
            level — the tools delegate to the canvas subprocess via
            ``process_manager`` / ``http_client``).
    """
    # Imported lazily to avoid a circular import between
    # ``excalidraw_mcp.mcp_tools`` and the rest of the package
    # (MCPToolsManager imports from element_factory / http_client).
    from excalidraw_mcp.mcp_tools import MCPToolsManager

    MCPToolsManager(mcp)
