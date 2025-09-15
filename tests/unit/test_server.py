"""Unit tests for the server module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from excalidraw_mcp.server import main, startup_initialization


class TestServerModule:
    """Test the server module functions."""

    @pytest.mark.asyncio
    async def test_startup_initialization_with_auto_start_enabled(self):
        """Test startup initialization with canvas auto-start enabled."""
        with patch('excalidraw_mcp.server.config') as mock_config, \
             patch('excalidraw_mcp.server.process_manager') as mock_process_manager, \
             patch('excalidraw_mcp.server.MCPToolsManager') as mock_tools_manager, \
             patch('excalidraw_mcp.server.logger') as mock_logger:
            
            # Mock config
            mock_config.server.canvas_auto_start = True
            
            # Mock process manager
            mock_process_manager.ensure_running = AsyncMock(return_value=True)
            
            # Call the function
            await startup_initialization()
            
            # Verify the calls
            mock_process_manager.ensure_running.assert_called_once()
            mock_logger.info.assert_any_call("Starting Excalidraw MCP Server...")
            mock_logger.info.assert_any_call("Checking canvas server status...")
            mock_logger.info.assert_any_call("Canvas server is ready")
            mock_tools_manager.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_initialization_with_auto_start_disabled(self):
        """Test startup initialization with canvas auto-start disabled."""
        with patch('excalidraw_mcp.server.config') as mock_config, \
             patch('excalidraw_mcp.server.process_manager') as mock_process_manager, \
             patch('excalidraw_mcp.server.MCPToolsManager') as mock_tools_manager, \
             patch('excalidraw_mcp.server.logger') as mock_logger:
            
            # Mock config
            mock_config.server.canvas_auto_start = False
            
            # Call the function
            await startup_initialization()
            
            # Verify the calls
            mock_process_manager.ensure_running.assert_not_called()
            mock_logger.info.assert_any_call("Starting Excalidraw MCP Server...")
            mock_logger.info.assert_any_call("Canvas auto-start disabled")
            mock_tools_manager.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_initialization_with_auto_start_failure(self):
        """Test startup initialization when canvas server fails to start."""
        with patch('excalidraw_mcp.server.config') as mock_config, \
             patch('excalidraw_mcp.server.process_manager') as mock_process_manager, \
             patch('excalidraw_mcp.server.MCPToolsManager') as mock_tools_manager, \
             patch('excalidraw_mcp.server.logger') as mock_logger:
            
            # Mock config
            mock_config.server.canvas_auto_start = True
            
            # Mock process manager to fail
            mock_process_manager.ensure_running = AsyncMock(return_value=False)
            
            # Call the function
            await startup_initialization()
            
            # Verify the calls
            mock_process_manager.ensure_running.assert_called_once()
            mock_logger.info.assert_any_call("Starting Excalidraw MCP Server...")
            mock_logger.info.assert_any_call("Checking canvas server status...")
            mock_logger.warning.assert_any_call(
                "Canvas server failed to start - continuing without canvas sync"
            )
            mock_tools_manager.assert_called_once()

    def test_main_function_normal_execution(self):
        """Test main function normal execution path."""
        with patch('excalidraw_mcp.server.asyncio.run') as mock_asyncio_run, \
             patch('excalidraw_mcp.server.mcp.run') as mock_mcp_run, \
             patch('excalidraw_mcp.server.startup_initialization') as mock_startup, \
             patch('excalidraw_mcp.server.logger') as mock_logger:
            
            # Mock the startup to complete normally
            mock_asyncio_run.return_value = None
            
            # Call main
            main()
            
            # Verify calls were made (without checking exact coroutine args)
            mock_asyncio_run.assert_called_once()
            mock_mcp_run.assert_called_once()

    def test_main_function_keyboard_interrupt(self):
        """Test main function handling of keyboard interrupt."""
        with patch('excalidraw_mcp.server.asyncio.run') as mock_asyncio_run, \
             patch('excalidraw_mcp.server.mcp.run') as mock_mcp_run, \
             patch('excalidraw_mcp.server.startup_initialization') as mock_startup, \
             patch('excalidraw_mcp.server.logger') as mock_logger:
            
            # Mock the startup to raise KeyboardInterrupt
            mock_asyncio_run.side_effect = KeyboardInterrupt()
            
            # Call main
            main()
            
            # Verify calls
            mock_asyncio_run.assert_called_once()
            mock_logger.info.assert_called_with("Received interrupt signal, shutting down...")

    def test_main_function_unexpected_exception(self):
        """Test main function handling of unexpected exceptions."""
        with patch('excalidraw_mcp.server.asyncio.run') as mock_asyncio_run, \
             patch('excalidraw_mcp.server.mcp.run') as mock_mcp_run, \
             patch('excalidraw_mcp.server.startup_initialization') as mock_startup, \
             patch('excalidraw_mcp.server.logger') as mock_logger:
            
            # Mock the startup to raise an unexpected exception
            mock_asyncio_run.side_effect = Exception("Unexpected error")
            
            # Call main and expect it to raise the exception
            with pytest.raises(Exception, match="Unexpected error"):
                main()
            
            # Verify calls
            mock_asyncio_run.assert_called_once()
            mock_logger.error.assert_called_once()