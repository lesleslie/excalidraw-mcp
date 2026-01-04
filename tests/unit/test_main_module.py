"""Unit tests for __main__ module."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest

from excalidraw_mcp.__main__ import ExcalidrawMCPServer, ExcalidrawConfig, main


class TestMainModule:
    """Test __main__ module classes and functions."""

    def test_excalidraw_config(self):
        """Test ExcalidrawConfig class."""
        config = ExcalidrawConfig()

        assert config.http_port == 3042
        assert config.http_host == "127.0.0.1"
        assert config.enable_http_transport is True

    @patch("excalidraw_mcp.__main__.BaseOneiricServerMixin.__init__", return_value=None)
    @patch("excalidraw_mcp.__main__.mcp")
    @patch("excalidraw_mcp.__main__.create_runtime_components")
    def test_excalidraw_mcp_server_init(self, mock_create_runtime, mock_mcp, mock_base_init):
        """Test ExcalidrawMCPServer initialization."""
        config = ExcalidrawConfig()
        mock_runtime = Mock()
        mock_create_runtime.return_value = mock_runtime

        server = ExcalidrawMCPServer(config)

        # Check that the server has the expected attributes
        assert server.config is config
        assert server.mcp is mock_mcp
        assert server.runtime is mock_runtime

    @patch("excalidraw_mcp.__main__.config")
    @patch("excalidraw_mcp.__main__.create_runtime_components")
    @patch("excalidraw_mcp.__main__.mcp")
    @pytest.mark.asyncio
    async def test_excalidraw_mcp_server_startup(self, mock_mcp, mock_create_runtime, mock_config):
        """Test ExcalidrawMCPServer startup method."""
        config = ExcalidrawConfig()
        mock_runtime = AsyncMock()
        mock_create_runtime.return_value = mock_runtime

        server = ExcalidrawMCPServer(config)

        # Call startup
        await server.startup()

        # Check that runtime was initialized
        mock_runtime.initialize.assert_awaited()

        # Check that validation was called
        mock_config._validate.assert_called()

    @patch("excalidraw_mcp.__main__.create_runtime_components")
    @patch("excalidraw_mcp.__main__.mcp")
    @patch("excalidraw_mcp.__main__.print")
    @pytest.mark.asyncio
    async def test_excalidraw_mcp_server_shutdown(self, mock_print, mock_mcp, mock_create_runtime):
        """Test ExcalidrawMCPServer shutdown method."""
        config = ExcalidrawConfig()
        mock_runtime = AsyncMock()
        mock_create_runtime.return_value = mock_runtime

        server = ExcalidrawMCPServer(config)

        # Call shutdown
        await server.shutdown()

        # Check that runtime was cleaned up
        mock_runtime.cleanup.assert_awaited()

        # Check that shutdown message was printed
        mock_print.assert_called()

    @patch("excalidraw_mcp.__main__.create_runtime_components")
    @patch("excalidraw_mcp.__main__.mcp")
    def test_excalidraw_mcp_server_get_timestamp(self, mock_mcp, mock_create_runtime):
        """Test ExcalidrawMCPServer _get_timestamp method."""
        config = ExcalidrawConfig()
        mock_runtime = Mock()
        mock_create_runtime.return_value = mock_runtime

        server = ExcalidrawMCPServer(config)

        # Call _get_timestamp
        timestamp = server._get_timestamp()

        # Check that the timestamp is in the expected format
        assert isinstance(timestamp, str)
        assert len(timestamp) == 20  # ISO format: YYYY-MM-DDTHH:MM:SSZ

    @patch("excalidraw_mcp.__main__.config")
    @patch("excalidraw_mcp.__main__.create_runtime_components")
    @patch("excalidraw_mcp.__main__.mcp")
    @patch("excalidraw_mcp.__main__.HealthStatus")
    @pytest.mark.asyncio
    async def test_excalidraw_mcp_server_health_check(self, mock_health_status, mock_mcp, mock_create_runtime, mock_config):
        """Test ExcalidrawMCPServer health_check method."""
        config = ExcalidrawConfig()
        mock_runtime = Mock()
        mock_component_health = Mock()
        mock_health_response = Mock()

        mock_runtime.health_monitor.create_component_health.return_value = mock_component_health
        mock_runtime.health_monitor.create_health_response.return_value = mock_health_response
        mock_create_runtime.return_value = mock_runtime
        mock_config.server = True  # Simulate that server is configured

        server = ExcalidrawMCPServer(config)

        # Mock the _build_health_components method to return the expected value
        with patch.object(server, '_build_health_components', new_callable=AsyncMock) as mock_build_health:
            mock_build_health.return_value = [mock_component_health]

            # Call health_check
            result = await server.health_check()

            # Check that the result is the expected health response
            assert result is mock_health_response

    @patch("excalidraw_mcp.__main__.mcp")
    @patch("excalidraw_mcp.__main__.create_runtime_components")
    def test_excalidraw_mcp_server_get_app(self, mock_create_runtime, mock_mcp):
        """Test ExcalidrawMCPServer get_app method."""
        config = ExcalidrawConfig()
        mock_runtime = Mock()
        mock_create_runtime.return_value = mock_runtime

        server = ExcalidrawMCPServer(config)

        # Call get_app
        app = server.get_app()

        # Check that the app is the mcp.http_app
        assert app is mock_mcp.http_app

    @patch("excalidraw_mcp.__main__.MCPServerCLIFactory")
    def test_main_function(self, mock_cli_factory):
        """Test main function."""
        # Mock the CLI factory and app
        mock_factory_instance = Mock()
        mock_app = Mock()
        mock_cli_factory.create_server_cli.return_value = mock_factory_instance

        # create_app() returns a callable that when invoked returns and calls mock_app
        # This matches the actual implementation: cli_factory.create_app()()
        mock_factory_instance.create_app.return_value = lambda: mock_app()

        # Call main function
        main()

        # Check that the CLI factory was called correctly
        mock_cli_factory.create_server_cli.assert_called_once_with(
            server_class=ExcalidrawMCPServer,
            config_class=ExcalidrawConfig,
            name="excalidraw-mcp",
        )
        mock_factory_instance.create_app.assert_called_once()
        # The app should be called once when main() executes the lambda
        assert mock_app.called