"""Simple runtime integration test for Excalidraw MCP Server.

This test verifies the Oneiric runtime integration is working correctly.
Tests import paths, configuration loading, and basic lifecycle operations.
"""

import pytest

# Test 1: Verify Oneiric modules can be imported
def test_oneiric_imports():
    """Test that Oneiric runtime modules are accessible."""
    # Core CLI imports
    from oneiric.core.cli import MCPServerCLIFactory
    from oneiric.core.config import OneiricMCPConfig

    # Runtime imports
    from oneiric.runtime.snapshot import RuntimeSnapshotManager
    from oneiric.runtime.cache import RuntimeCacheManager
    from oneiric.runtime.mcp_health import HealthCheckResponse, HealthStatus, HealthMonitor

    # Verify classes exist
    assert MCPServerCLIFactory is not None
    assert OneiricMCPConfig is not None
    assert RuntimeSnapshotManager is not None
    assert RuntimeCacheManager is not None
    assert HealthMonitor is not None
    assert HealthStatus is not None
    assert HealthCheckResponse is not None


# Test 2: Verify Excalidraw configuration class
def test_excalidraw_config():
    """Test that ExcalidrawConfig can be instantiated."""
    from excalidraw_mcp.__main__ import ExcalidrawConfig

    # Create configuration with defaults
    config = ExcalidrawConfig()

    # Verify default values
    assert config.http_port == 3042
    assert config.http_host == "127.0.0.1"
    assert config.enable_http_transport is True
    assert config.cache_dir is None or config.cache_dir == ".oneiric_cache"


# Test 3: Verify ExcalidrawMCPServer can be created
def test_excalidraw_server_creation():
    """Test that ExcalidrawMCPServer can be instantiated."""
    from excalidraw_mcp.__main__ import ExcalidrawConfig, ExcalidrawMCPServer

    # Create configuration
    config = ExcalidrawConfig()

    # Create server instance
    server = ExcalidrawMCPServer(config)

    # Verify runtime components are initialized
    assert server.config is not None
    assert server.snapshot_manager is not None
    assert server.cache_manager is not None
    assert server.health_monitor is not None
    assert server.mcp is not None


# Test 4: Verify health check can be executed
@pytest.mark.asyncio
async def test_excalidraw_health_check():
    """Test that health check method works."""
    from excalidraw_mcp.__main__ import ExcalidrawConfig, ExcalidrawMCPServer

    # Create server
    config = ExcalidrawConfig()
    server = ExcalidrawMCPServer(config)

    # Execute health check
    health_response = await server.health_check()

    # Verify response structure
    assert health_response is not None
    assert hasattr(health_response, 'status')
    assert hasattr(health_response, 'components')
    assert len(health_response.components) > 0


# Test 5: Verify cache directory can be configured
def test_cache_directory_configuration():
    """Test that custom cache directory can be set."""
    from excalidraw_mcp.__main__ import ExcalidrawConfig

    # Create config with custom cache dir
    config = ExcalidrawConfig(cache_dir="/tmp/test_cache")

    # Verify cache directory is set
    assert config.cache_dir == "/tmp/test_cache"


# Test 6: Verify CLI factory can be created
def test_cli_factory_creation():
    """Test that MCPServerCLIFactory can be created for Excalidraw."""
    from oneiric.core.cli import MCPServerCLIFactory
    from excalidraw_mcp.__main__ import ExcalidrawConfig, ExcalidrawMCPServer

    # Create CLI factory
    cli_factory = MCPServerCLIFactory(
        server_class=ExcalidrawMCPServer,
        config_class=ExcalidrawConfig,
        name="excalidraw-mcp",
        use_subcommands=True,
        legacy_flags=False,
        description="Excalidraw MCP Server - Diagram management via Excalidraw API"
    )

    # Verify factory configuration
    assert cli_factory.server_class == ExcalidrawMCPServer
    assert cli_factory.config_class == ExcalidrawConfig
    assert cli_factory.name == "excalidraw-mcp"
    assert cli_factory.use_subcommands is True
    assert cli_factory.legacy_flags is False


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
