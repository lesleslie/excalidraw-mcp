"""Additional tests to improve coverage for server module."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from excalidraw_mcp.server import (
    cleanup_monitoring,
    get_monitoring_supervisor,
    get_process_manager,
    init_background_services,
    main,
)


class TestServerModuleAdditional:
    """Additional tests for server module to improve coverage."""

    def test_get_process_manager_caching(self):
        """Test that get_process_manager returns the same instance."""
        import excalidraw_mcp.server as server_module
        
        # Clear any existing instance
        server_module.process_manager = None
        
        # Get the manager twice
        manager1 = get_process_manager()
        manager2 = get_process_manager()
        
        # They should be the same instance
        assert manager1 is manager2

    def test_get_monitoring_supervisor_caching(self):
        """Test that get_monitoring_supervisor returns the same instance."""
        import excalidraw_mcp.server as server_module
        
        # Clear any existing instance
        server_module.monitoring_supervisor = None
        
        # Get the supervisor twice
        supervisor1 = get_monitoring_supervisor()
        supervisor2 = get_monitoring_supervisor()
        
        # They should be the same instance
        assert supervisor1 is supervisor2

    @patch("mcp_common.ui.ServerPanels")
    @patch("excalidraw_mcp.server.logger")
    @patch("excalidraw_mcp.server.init_background_services")
    @patch("excalidraw_mcp.server.mcp")
    @patch("excalidraw_mcp.server.SERVERPANELS_AVAILABLE", True)
    def test_main_with_serverpanels_enabled(self, mock_mcp, mock_init, mock_logger, mock_serverpanels):
        """Test main function with ServerPanels enabled."""
        # Mock the mcp.run method to avoid actually starting the server
        mock_mcp.run = Mock()

        # Call main function
        main()

        # When ServerPanels is available, it uses ServerPanels.startup_success() instead of logger
        mock_serverpanels.startup_success.assert_called_once()
        # Verify logger.info is NOT called (ServerPanels handles display)
        assert not mock_logger.info.called

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

    @patch("subprocess.Popen")
    @patch("time.sleep")
    @patch("excalidraw_mcp.server.logger")
    @patch("pathlib.Path")
    @patch("requests.get")
    def test_init_background_services_canvas_not_running(
        self, mock_requests_get, mock_path, mock_logger, mock_sleep, mock_popen
    ):
        """Test init_background_services when canvas server is not running."""
        # Make requests.get raise an exception (canvas not running)
        # Use the specific exception types that the function catches
        import requests
        mock_requests_get.side_effect = requests.ConnectionError("Connection refused")

        # Mock the Path object
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.parent.parent.resolve.return_value = "/mock/project/root"

        # Call the function
        init_background_services()

        # Check that subprocess.Popen was called to start canvas server
        mock_popen.assert_called_once()

        # Check that sleep was called during the wait loop
        assert mock_sleep.called

    @patch("requests.get")
    @patch("excalidraw_mcp.server.logger")
    def test_init_background_services_canvas_already_running(
        self, mock_logger, mock_requests_get
    ):
        """Test init_background_services when canvas server is already running."""
        # Make requests.get succeed (canvas is running)
        mock_response = Mock()
        mock_requests_get.return_value = mock_response

        # Call the function
        init_background_services()

        # Check that canvas server was reported as running
        mock_logger.info.assert_any_call("Canvas server already running")

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

    def test_http_app_property(self):
        """Test that http_app property is accessible."""
        from excalidraw_mcp.server import http_app
        # Just ensure it exists and doesn't raise an exception
        assert http_app is not None