"""Additional tests to cover missing lines in process_manager.py"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from excalidraw_mcp.process_manager import CanvasProcessManager


class TestProcessManagerCoverage:
    """Additional tests to cover missing lines in process_manager.py"""

    @pytest.fixture
    def process_manager(self):
        """Create a CanvasProcessManager instance for testing."""
        return CanvasProcessManager()

    @pytest.mark.asyncio
    async def test_ensure_running_auto_start_disabled(self, process_manager):
        """Test ensure_running when auto-start is disabled."""
        with (
            patch("excalidraw_mcp.process_manager.config") as mock_config,
            patch.object(process_manager, "_is_process_healthy", return_value=False),
            patch("excalidraw_mcp.process_manager.logger") as mock_logger,
        ):
            # Mock config to disable auto-start
            mock_config.server.canvas_auto_start = False

            # Call ensure_running
            result = await process_manager.ensure_running()

            # Should return False and log a warning
            assert result is False
            mock_logger.warning.assert_called_once_with(
                "Canvas server not running and auto-start is disabled"
            )

    @pytest.mark.asyncio
    async def test_ensure_running_start_process_failure(self, process_manager):
        """Test ensure_running when starting process fails."""
        with (
            patch.object(process_manager, "_is_process_healthy", return_value=False),
            patch.object(process_manager, "_start_process", return_value=False),
            patch("excalidraw_mcp.process_manager.logger") as mock_logger,
        ):
            # Call ensure_running
            result = await process_manager.ensure_running()

            # Should return False and log an error
            assert result is False
            mock_logger.error.assert_called_once_with("Failed to start canvas server")

    @pytest.mark.asyncio
    async def test_ensure_running_wait_for_health_failure(self, process_manager):
        """Test ensure_running when waiting for health fails."""
        with (
            patch.object(process_manager, "_is_process_healthy", return_value=False),
            patch.object(process_manager, "_start_process", return_value=True),
            patch.object(process_manager, "_wait_for_health", return_value=False),
        ):
            # Call ensure_running
            result = await process_manager.ensure_running()

            # Should return False
            assert result is False

    @pytest.mark.asyncio
    async def test_start_process_exception(self, process_manager):
        """Test _start_process when an exception occurs."""
        with (
            patch.object(
                process_manager,
                "_get_project_root",
                side_effect=Exception("Test exception"),
            ),
            patch("excalidraw_mcp.process_manager.logger") as mock_logger,
        ):
            # Call _start_process
            result = await process_manager._start_process()

            # Should return False and log an error
            assert result is False
            mock_logger.error.assert_called_once()
            assert "Failed to start canvas server: Test exception" in str(
                mock_logger.error.call_args[0]
            )

    @pytest.mark.asyncio
    async def test_start_process_success(self, process_manager):
        """Test _start_process when it succeeds."""
        with (
            patch.object(process_manager, "_get_project_root"),
            patch("subprocess.Popen") as mock_popen,
            patch("asyncio.sleep", new=AsyncMock()),
        ):
            # Mock the process
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            # Call _start_process
            result = await process_manager._start_process()

            # Should return True
            assert result is True
            assert process_manager.process == mock_process
            assert process_manager.process_pid == 12345

    @pytest.mark.asyncio
    async def test_wait_for_health_timeout(self, process_manager):
        """Test _wait_for_health when it times out."""
        with (
            patch.object(process_manager, "_is_process_running", return_value=True),
            patch("excalidraw_mcp.process_manager.http_client") as mock_http_client,
            patch.object(process_manager, "_terminate_current_process"),
            patch("excalidraw_mcp.process_manager.logger") as mock_logger,
        ):
            # Mock http_client to always return False (unhealthy)
            mock_http_client.check_health = AsyncMock(return_value=False)

            # Mock config to have a small timeout for testing
            with patch("excalidraw_mcp.process_manager.config") as mock_config:
                mock_config.server.startup_timeout_seconds = 3
                mock_config.server.health_check_timeout_seconds = 1.0
                mock_config.server.health_check_interval_seconds = 1

                # Call _wait_for_health
                result = await process_manager._wait_for_health()

                # Should return False
                assert result is False
                mock_logger.error.assert_called_once_with(
                    "Canvas server failed to become healthy within timeout"
                )

    @pytest.mark.asyncio
    async def test_wait_for_health_process_dies(self, process_manager):
        """Test _wait_for_health when process dies during waiting."""
        with (
            patch.object(
                process_manager, "_is_process_running", side_effect=[True, False]
            ),
            patch("excalidraw_mcp.process_manager.logger") as mock_logger,
        ):
            # Call _wait_for_health
            result = await process_manager._wait_for_health()

            # Should return False
            assert result is False
            mock_logger.error.assert_called_once_with(
                "Canvas server process died during startup"
            )

    @pytest.mark.asyncio
    async def test_wait_for_health_success(self, process_manager):
        """Test _wait_for_health when it succeeds."""
        with (
            patch.object(process_manager, "_is_process_running", return_value=True),
            patch("excalidraw_mcp.process_manager.http_client") as mock_http_client,
            patch("asyncio.sleep", new=AsyncMock()),
            patch("excalidraw_mcp.process_manager.logger") as mock_logger,
        ):
            # Mock http_client to return True (healthy) on second call
            mock_http_client.check_health = AsyncMock(side_effect=[False, True])

            # Call _wait_for_health
            result = await process_manager._wait_for_health()

            # Should return True
            assert result is True
            mock_logger.info.assert_any_call("Canvas server is healthy and ready")

    @pytest.mark.asyncio
    async def test_is_process_healthy_success(self, process_manager):
        """Test _is_process_healthy when process is healthy."""
        with (
            patch.object(process_manager, "_is_process_running", return_value=True),
            patch("excalidraw_mcp.process_manager.http_client") as mock_http_client,
        ):
            # Mock http_client to return True (healthy)
            mock_http_client.check_health = AsyncMock(return_value=True)

            # Call _is_process_healthy
            result = await process_manager._is_process_healthy()

            # Should return True
            assert result is True

    @pytest.mark.asyncio
    async def test_is_process_healthy_unhealthy(self, process_manager):
        """Test _is_process_healthy when process is unhealthy."""
        with (
            patch.object(process_manager, "_is_process_running", return_value=True),
            patch("excalidraw_mcp.process_manager.http_client") as mock_http_client,
        ):
            # Mock http_client to return False (unhealthy)
            mock_http_client.check_health = AsyncMock(return_value=False)

            # Call _is_process_healthy
            result = await process_manager._is_process_healthy()

            # Should return False
            assert result is False

    @pytest.mark.asyncio
    async def test_is_process_healthy_not_running(self, process_manager):
        """Test _is_process_healthy when process is not running."""
        with patch.object(process_manager, "_is_process_running", return_value=False):
            # Call _is_process_healthy
            result = await process_manager._is_process_healthy()

            # Should return False
            assert result is False

    @pytest.mark.asyncio
    async def test_terminate_existing_process_force_kill(self, process_manager):
        """Test _terminate_existing_process with force kill."""
        # Set up a mock process
        mock_process = Mock()
        mock_process_pid = 12345

        process_manager.process = mock_process
        process_manager.process_pid = mock_process_pid

        with (
            patch("os.name", "posix"),
            patch("os.getpgid", return_value=mock_process_pid),
            patch("os.killpg") as mock_killpg,
            patch("time.sleep"),
            patch("psutil.pid_exists", side_effect=[True, False]),
            patch("excalidraw_mcp.process_manager.logger"),
        ):
            # Terminate the process
            process_manager._terminate_existing_process()

            # Should have called killpg twice (TERM then KILL)
            assert mock_killpg.call_count == 2

    @pytest.mark.asyncio
    async def test_terminate_existing_process_windows(self, process_manager):
        """Test _terminate_existing_process on Windows."""
        # Set up a mock process
        mock_process = Mock()
        mock_process_pid = 12345

        process_manager.process = mock_process
        process_manager.process_pid = mock_process_pid

        with (
            patch("os.name", "nt"),
            patch("time.sleep"),
            patch("psutil.pid_exists", return_value=False),
            patch("excalidraw_mcp.process_manager.logger"),
        ):
            # Terminate the process
            process_manager._terminate_existing_process()

            # Should have called terminate/kill on the process
            mock_process.terminate.assert_called_once()
