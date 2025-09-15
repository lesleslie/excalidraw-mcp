"""Unit tests for the process manager module."""

import asyncio
import os
import signal
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import psutil
import pytest

from excalidraw_mcp.process_manager import CanvasProcessManager


class TestCanvasProcessManager:
    """Test the CanvasProcessManager class."""

    @pytest.fixture
    def process_manager(self):
        """Create a CanvasProcessManager instance for testing."""
        return CanvasProcessManager()

    def test_process_manager_initialization(self, process_manager):
        """Test that process manager initializes correctly."""
        assert process_manager.process is None
        assert process_manager.process_pid is None
        assert hasattr(process_manager, '_startup_lock')

    def test_reset_process_info(self, process_manager):
        """Test that process info is reset correctly."""
        # Set up fake process info
        process_manager.process = Mock()
        process_manager.process_pid = 12345

        # Reset the info
        process_manager._reset_process_info()

        # Verify it's reset
        assert process_manager.process is None
        assert process_manager.process_pid is None

    def test_get_project_root(self, process_manager):
        """Test that project root is determined correctly."""
        project_root = process_manager._get_project_root()
        assert isinstance(project_root, Path)
        # The project directory name might have underscores or dashes depending on system
        assert "excalidraw" in project_root.name

    def test_signal_handler(self, process_manager):
        """Test that signal handler works correctly."""
        with patch.object(process_manager, 'cleanup') as mock_cleanup, \
             patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            
            # Call the signal handler
            process_manager._signal_handler(signal.SIGTERM, None)
            
            # Verify cleanup was called
            mock_cleanup.assert_called_once()
            mock_logger.info.assert_called_once_with("Received signal 15, cleaning up...")

    def test_cleanup(self, process_manager):
        """Test that cleanup works correctly."""
        with patch.object(process_manager, '_terminate_current_process') as mock_terminate, \
             patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            
            # Call cleanup
            process_manager.cleanup()
            
            # Verify termination was called
            mock_terminate.assert_called_once()
            mock_logger.info.assert_called_once_with("Cleaning up canvas process manager...")

    @pytest.mark.asyncio
    async def test_restart(self, process_manager):
        """Test that restart works correctly."""
        with patch.object(process_manager, '_terminate_current_process') as mock_terminate, \
             patch.object(process_manager, 'ensure_running', new=AsyncMock(return_value=True)), \
             patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            
            # Call restart
            result = await process_manager.restart()
            
            # Verify the calls
            mock_terminate.assert_called_once()
            mock_logger.info.assert_called_once_with("Restarting canvas server...")
            assert result is True

    @pytest.mark.asyncio
    async def test_stop(self, process_manager):
        """Test that stop works correctly."""
        with patch.object(process_manager, '_terminate_current_process') as mock_terminate, \
             patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            
            # Call stop
            await process_manager.stop()
            
            # Verify termination was called
            mock_terminate.assert_called_once()
            mock_logger.info.assert_called_once_with("Stopping canvas server...")

    def test_get_status(self, process_manager):
        """Test that status information is returned correctly."""
        # Mock the process running check
        with patch.object(process_manager, '_is_process_running', return_value=True):
            status = process_manager.get_status()
            
            # Verify status contains expected keys
            assert "running" in status
            assert "pid" in status
            assert "healthy" in status
            assert "auto_start_enabled" in status
            assert status["running"] is True
            assert status["pid"] is None  # No PID set
            assert status["healthy"] is False  # Default value
            assert isinstance(status["auto_start_enabled"], bool)

    def test_is_process_running_no_process(self, process_manager):
        """Test that process running check returns False when no process."""
        # No process set, should return False
        result = process_manager._is_process_running()
        assert result is False

    def test_is_process_running_process_exited(self, process_manager):
        """Test that process running check handles exited processes."""
        # Set up a mock process that has exited
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process has exited
        mock_process_pid = 12345
        
        process_manager.process = mock_process
        process_manager.process_pid = mock_process_pid

        with patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            # Check if process is running
            result = process_manager._is_process_running()
            
            # Should return False
            assert result is False
            # Should have reset process info
            assert process_manager.process is None
            assert process_manager.process_pid is None
            mock_logger.debug.assert_called_once_with("Canvas server process has exited")

    def test_is_process_running_pid_does_not_exist(self, process_manager):
        """Test that process running check handles non-existent PIDs."""
        # Set up a mock process with a non-existent PID
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_process_pid = 999999  # Non-existent PID
        
        process_manager.process = mock_process
        process_manager.process_pid = mock_process_pid

        with patch('psutil.pid_exists', return_value=False), \
             patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            
            # Check if process is running
            result = process_manager._is_process_running()
            
            # Should return False
            assert result is False
            # Should have reset process info
            assert process_manager.process is None
            assert process_manager.process_pid is None
            mock_logger.debug.assert_called_once_with("Canvas server PID no longer exists")

    def test_is_process_running_exception_handling(self, process_manager):
        """Test that process running check handles exceptions gracefully."""
        # Set up a mock process
        mock_process = Mock()
        mock_process.poll.side_effect = Exception("Test exception")
        mock_process_pid = 12345
        
        process_manager.process = mock_process
        process_manager.process_pid = mock_process_pid

        with patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            # Check if process is running
            result = process_manager._is_process_running()
            
            # Should return False
            assert result is False
            # Should have reset process info
            assert process_manager.process is None
            assert process_manager.process_pid is None
            mock_logger.debug.assert_called_once()
            assert "Error checking process status" in str(mock_logger.debug.call_args[0])

    def test_terminate_existing_process_no_pid(self, process_manager):
        """Test that terminate handles case with no PID."""
        # No PID set, should not raise exception
        process_manager._terminate_existing_process()
        # Should just reset process info silently

    def test_terminate_existing_process_successful_termination(self, process_manager):
        """Test that terminate successfully terminates a process."""
        # Set up a mock process
        mock_process = Mock()
        mock_process_pid = 12345
        
        process_manager.process = mock_process
        process_manager.process_pid = mock_process_pid

        with patch('os.getpgid', return_value=mock_process_pid), \
             patch('os.killpg'), \
             patch('time.sleep'), \
             patch('psutil.pid_exists', return_value=False), \
             patch('excalidraw_mcp.process_manager.logger'):
            
            # Terminate the process
            process_manager._terminate_existing_process()
            
            # Should have reset process info
            assert process_manager.process is None
            assert process_manager.process_pid is None

    def test_terminate_existing_process_already_terminated(self, process_manager):
        """Test that terminate handles already terminated processes."""
        # Set up a mock process
        mock_process = Mock()
        mock_process_pid = 12345
        
        process_manager.process = mock_process
        process_manager.process_pid = mock_process_pid

        with patch('os.getpgid', return_value=mock_process_pid), \
             patch('os.killpg', side_effect=ProcessLookupError("Process already terminated")), \
             patch('time.sleep'), \
             patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            
            # Terminate the process
            process_manager._terminate_existing_process()
            
            # Should have reset process info
            assert process_manager.process is None
            assert process_manager.process_pid is None
            mock_logger.debug.assert_called_once()

    def test_terminate_existing_process_other_exception(self, process_manager):
        """Test that terminate handles other exceptions gracefully."""
        # Set up a mock process
        mock_process = Mock()
        mock_process_pid = 12345
        
        process_manager.process = mock_process
        process_manager.process_pid = mock_process_pid

        with patch('os.getpgid', return_value=mock_process_pid), \
             patch('os.killpg', side_effect=Exception("Test exception")), \
             patch('time.sleep'), \
             patch('excalidraw_mcp.process_manager.logger') as mock_logger:
            
            # Terminate the process
            process_manager._terminate_existing_process()
            
            # Should have reset process info
            assert process_manager.process is None
            assert process_manager.process_pid is None
            mock_logger.warning.assert_called_once()
            assert "Error terminating existing process" in str(mock_logger.warning.call_args[0])