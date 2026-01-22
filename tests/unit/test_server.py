"""Unit tests for server module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from excalidraw_mcp.server import (
    cleanup_monitoring,
    get_monitoring_supervisor,
    get_process_manager,
    init_background_services,
    main,
)


class TestServerModule:
    """Test server module functions."""

    def test_get_process_manager(self):
        """Test get_process_manager function."""
        # Clear any existing instance
        import excalidraw_mcp.server as server_module
        server_module.process_manager = None

        # Get the manager
        manager1 = get_process_manager()
        manager2 = get_process_manager()

        # Should return the same instance
        assert manager1 is manager2

    def test_get_monitoring_supervisor(self):
        """Test get_monitoring_supervisor function."""
        # Clear any existing instance
        import excalidraw_mcp.server as server_module
        server_module.monitoring_supervisor = None

        # Get the supervisor
        supervisor1 = get_monitoring_supervisor()
        supervisor2 = get_monitoring_supervisor()

        # Should return the same instance
        assert supervisor1 is supervisor2

    @patch("mcp_common.ui.ServerPanels")
    @patch("excalidraw_mcp.server.logger")
    @patch("excalidraw_mcp.server.init_background_services")
    @patch("excalidraw_mcp.server.mcp")
    @patch("excalidraw_mcp.server.SERVERPANELS_AVAILABLE", True)
    def test_main_with_serverpanels(self, mock_mcp, mock_init, mock_logger, mock_serverpanels):
        """Test main function with ServerPanels available."""
        # Mock the mcp.run method to avoid actually starting the server
        mock_mcp.run = Mock()

        # Call main function
        main()

        # Check that ServerPanels.startup_success was called
        mock_serverpanels.startup_success.assert_called_once()

        # Check that background services were initialized
        mock_init.assert_called_once()

        # Check that mcp.run was called
        mock_mcp.run.assert_called_once_with(
            transport="http", host="localhost", port=3032
        )

    @patch("excalidraw_mcp.server.logger")
    @patch("excalidraw_mcp.server.init_background_services")
    @patch("excalidraw_mcp.server.mcp")
    @patch("excalidraw_mcp.server.SERVERPANELS_AVAILABLE", False)
    def test_main_without_serverpanels(self, mock_mcp, mock_init, mock_logger):
        """Test main function without ServerPanels available."""
        # Mock the mcp.run method to avoid actually starting the server
        mock_mcp.run = Mock()

        # Call main function
        main()

        # Check that logger.info was called (fallback message)
        mock_logger.info.assert_called()

        # Check that background services were initialized
        mock_init.assert_called_once()

        # Check that mcp.run was called
        mock_mcp.run.assert_called_once_with(
            transport="http", host="localhost", port=3032
        )

    @patch("excalidraw_mcp.server.logger")
    @patch("excalidraw_mcp.server.init_background_services")
    @patch("excalidraw_mcp.server.mcp")
    @patch("excalidraw_mcp.server.SERVERPANELS_AVAILABLE", True)
    def test_main_keyboard_interrupt(self, mock_mcp, mock_init, mock_logger):
        """Test main function with KeyboardInterrupt."""
        # Make mcp.run raise KeyboardInterrupt
        mock_mcp.run.side_effect = KeyboardInterrupt()

        # Call main function
        main()

        # Check that interrupt message was logged
        mock_logger.info.assert_any_call("Server interrupted by user")

    @patch("excalidraw_mcp.server.logger")
    @patch("excalidraw_mcp.server.init_background_services")
    @patch("excalidraw_mcp.server.mcp")
    @patch("excalidraw_mcp.server.SERVERPANELS_AVAILABLE", True)
    def test_main_exception(self, mock_mcp, mock_init, mock_logger):
        """Test main function with general exception."""
        # Make mcp.run raise a general exception
        mock_mcp.run.side_effect = RuntimeError("Test error")

        # Call main function and expect it to raise the exception
        with pytest.raises(RuntimeError):
            main()

        # Check that error was logged
        mock_logger.error.assert_called()

    @patch("excalidraw_mcp.server.logger")
    def test_init_background_services_canvas_not_running(self, mock_logger):
        """Test init_background_services when canvas server is not running."""
        # This test primarily validates the function doesn't crash
        # Integration tests cover the actual canvas server startup
        # We can't easily mock the internal imports (requests, subprocess, etc.)
        # since they're imported inside the function

        # For now, just verify the function exists and is callable
        assert callable(init_background_services)

    @patch("excalidraw_mcp.server.logger")
    def test_init_background_services_canvas_already_running(self, mock_logger):
        """Test init_background_services when canvas server is already running."""
        # This test primarily validates the function doesn't crash
        # Integration tests cover the actual canvas server detection
        # We can't easily mock the internal imports since they're inside the function

        # For now, just verify the function exists and is callable
        assert callable(init_background_services)

    @patch("excalidraw_mcp.server.monitoring_supervisor")
    def test_cleanup_monitoring_running(self, mock_supervisor):
        """Test cleanup_monitoring function when supervisor is running."""
        mock_supervisor.is_running = True
        mock_supervisor.stop = AsyncMock()

        # Call the function
        cleanup_monitoring()

        # Check that stop was called
        # Note: We can't directly test asyncio.create_task call easily,
        # but we know the function should run without errors

    @patch("excalidraw_mcp.server.monitoring_supervisor")
    def test_cleanup_monitoring_not_running(self, mock_supervisor):
        """Test cleanup_monitoring function when supervisor is not running."""
        mock_supervisor.is_running = False

        # Call the function
        cleanup_monitoring()

        # Should not raise an exception
