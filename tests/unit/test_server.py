"""Unit tests for the server module."""

import sys
from unittest.mock import Mock, patch

import pytest

from excalidraw_mcp.server import init_background_services, main


class TestServerModule:
    """Test the server module functions."""

    def test_init_background_services_server_already_running(self):
        """Test initialization when canvas server is already running."""
        # Create a mock requests module
        mock_requests = Mock()
        mock_requests.get.return_value = Mock()
        mock_requests.RequestException = Exception

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch("excalidraw_mcp.server.logger") as mock_logger,
        ):
            # Call the function
            init_background_services()

            # Verify the calls
            mock_requests.get.assert_called_with(
                "http://localhost:3031/health", timeout=1
            )
            mock_logger.info.assert_any_call("Canvas server already running")
            mock_logger.info.assert_any_call("Background services initialized")

    def test_init_background_services_starts_server(self):
        """Test initialization when canvas server needs to be started."""
        # Create a mock requests module
        mock_requests = Mock()
        mock_requests.get.side_effect = [
            Exception("Connection refused"),  # Initial check fails
            Mock(),  # Health check after start succeeds
        ]
        mock_requests.RequestException = Exception

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch("subprocess.Popen") as mock_popen,
            patch("time.sleep"),
            patch("excalidraw_mcp.server.logger") as mock_logger,
        ):
            # Call the function
            init_background_services()

            # Verify subprocess was called to start canvas server
            mock_popen.assert_called_once()
            mock_logger.info.assert_any_call("Starting canvas server...")
            mock_logger.info.assert_any_call("Canvas server is ready")
            mock_logger.info.assert_any_call("Background services initialized")

    def test_init_background_services_server_not_ready(self):
        """Test initialization when canvas server fails to become ready."""
        # Create a mock requests module
        mock_requests = Mock()
        mock_requests.get.side_effect = Exception("Connection refused")
        mock_requests.RequestException = Exception

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch("subprocess.Popen") as mock_popen,
            patch("time.sleep"),
            patch("excalidraw_mcp.server.logger") as mock_logger,
        ):
            # Call the function
            init_background_services()

            # Verify subprocess was called and warning was logged
            mock_popen.assert_called_once()
            mock_logger.warning.assert_any_call("Canvas server may not be ready")
            mock_logger.info.assert_any_call("Background services initialized")

    def test_main_function_normal_execution(self):
        """Test main function normal execution path."""
        with (
            patch("excalidraw_mcp.server.init_background_services") as mock_init,
            patch("excalidraw_mcp.server.mcp") as mock_mcp,
            patch("excalidraw_mcp.server.logger") as mock_logger,
        ):
            # Call main
            main()

            # Verify calls were made
            mock_init.assert_called_once()
            mock_mcp.run.assert_called_once_with(
                transport="http", host="localhost", port=3032
            )
            mock_logger.info.assert_called_with("Starting Excalidraw MCP Server...")

    def test_main_function_keyboard_interrupt(self):
        """Test main function handling of keyboard interrupt."""
        with (
            patch("excalidraw_mcp.server.init_background_services") as mock_init,
            patch("excalidraw_mcp.server.mcp") as mock_mcp,
            patch("excalidraw_mcp.server.logger") as mock_logger,
        ):
            # Mock the mcp.run to raise KeyboardInterrupt
            mock_mcp.run.side_effect = KeyboardInterrupt()

            # Call main
            main()

            # Verify calls
            mock_init.assert_called_once()
            mock_mcp.run.assert_called_once()
            mock_logger.info.assert_any_call("Server interrupted by user")

    def test_main_function_unexpected_exception(self):
        """Test main function handling of unexpected exceptions."""
        with (
            patch("excalidraw_mcp.server.init_background_services") as mock_init,
            patch("excalidraw_mcp.server.mcp") as mock_mcp,
            patch("excalidraw_mcp.server.logger") as mock_logger,
        ):
            # Mock the mcp.run to raise an unexpected exception
            test_exception = Exception("Unexpected error")
            mock_mcp.run.side_effect = test_exception

            # Call main and expect it to raise the exception
            with pytest.raises(Exception, match="Unexpected error"):
                main()

            # Verify calls
            mock_init.assert_called_once()
            mock_mcp.run.assert_called_once()
            mock_logger.error.assert_called_with("Server error: Unexpected error")
