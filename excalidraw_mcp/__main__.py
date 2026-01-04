#!/usr/bin/env python3
"""Excalidraw MCP Server - Module entry point for Oneiric CLI integration."""

from typing import Any

from mcp_common.cli import MCPServerCLIFactory
from mcp_common.server import BaseOneiricServerMixin, create_runtime_components
from oneiric.core.config import OneiricMCPConfig
from oneiric.runtime.mcp_health import HealthStatus

from excalidraw_mcp.config import config

# Import the main server from the existing codebase
from excalidraw_mcp.server import mcp


class ExcalidrawConfig(OneiricMCPConfig):
    """Excalidraw MCP Server Configuration."""

    http_port: int = 3042
    http_host: str = "127.0.0.1"
    enable_http_transport: bool = True

    class Config:
        env_prefix = "EXCALIDRAW_MCP_"
        env_file = ".env"


class ExcalidrawMCPServer(BaseOneiricServerMixin):
    """Excalidraw MCP Server with Oneiric integration."""

    def __init__(self, config: ExcalidrawConfig):
        self.config = config
        self.mcp = mcp  # Use the existing FastMCP instance
        # Update global config with Oneiric settings
        self._update_global_config()

        # Initialize runtime components using mcp-common helper
        self.runtime = create_runtime_components(
            server_name="excalidraw-mcp", cache_dir=config.cache_dir or ".oneiric_cache"
        )

    def _update_global_config(self) -> None:
        """Update global config with Oneiric settings."""
        # Update server settings from config
        from excalidraw_mcp.config import config as global_config

        global_config.server.express_host = self.config.http_host
        global_config.server.express_port = self.config.http_port

    async def startup(self) -> None:
        """Server startup lifecycle hook."""
        # Validate configuration
        config._validate()

        # Initialize runtime components
        await self.runtime.initialize()

        # Create startup snapshot with custom components
        await self._create_startup_snapshot(
            custom_components={
                "excalidraw": {
                    "status": "initialized",
                    "timestamp": self._get_timestamp(),
                },
            }
        )

        print("✅ Excalidraw MCP Server started successfully")
        print(f"   Listening on {self.config.http_host}:{self.config.http_port}")
        print(f"   Cache directory: {self.runtime.cache_dir}")
        print("   Snapshot manager: Initialized")
        print("   Cache manager: Initialized")

    async def shutdown(self) -> None:
        """Server shutdown lifecycle hook."""
        # Create shutdown snapshot
        await self._create_shutdown_snapshot()

        # Clean up runtime components
        await self.runtime.cleanup()

        print("👋 Excalidraw MCP Server shutdown complete")

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        import time

        return time.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def health_check(self) -> Any:
        """Perform health check."""
        # Build base health components using mixin helper
        base_components = await self._build_health_components()

        # Check Excalidraw configuration
        excalidraw_configured = bool(config and config.server)

        # Add excalidraw-specific health checks
        base_components.append(
            self.runtime.health_monitor.create_component_health(
                name="excalidraw",
                status=HealthStatus.HEALTHY
                if excalidraw_configured
                else HealthStatus.UNHEALTHY,
                details={
                    "configured": excalidraw_configured,
                    "server": bool(config.server if config else False),
                },
            )
        )

        # Create health response
        return self.runtime.health_monitor.create_health_response(base_components)

    def get_app(self) -> Any:
        """Get the ASGI application."""
        return self.mcp.http_app


def main() -> None:
    """Main entry point for Excalidraw MCP Server."""

    # Create CLI factory using mcp-common's enhanced factory
    cli_factory = MCPServerCLIFactory.create_server_cli(
        server_class=ExcalidrawMCPServer,
        config_class=ExcalidrawConfig,
        name="excalidraw-mcp",
    )

    # Create and run CLI
    cli_factory.create_app()()


if __name__ == "__main__":
    main()
