"""Unit tests for CLI module."""

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from excalidraw_mcp.cli import (
    _find_log_file,
    _serve_background,
    _serve_http,
    _show_missing_log_message,
    app,
    find_canvas_server_process,
    find_mcp_server_process,
    get_monitoring_supervisor,
    get_process_manager,
    logs,
    restart,
    status,
    stop,
)
from excalidraw_mcp.monitoring.supervisor import MonitoringSupervisor
from excalidraw_mcp.process_manager import CanvasProcessManager

runner = CliRunner()


class TestCLIModule:
    """Test CLI module functions."""

    def test_get_process_manager(self):
        """Test get_process_manager function."""
        # Clear any existing instance
        import excalidraw_mcp.cli as cli_module
        cli_module._process_manager = None

        # Get the manager
        manager1 = get_process_manager()
        manager2 = get_process_manager()

        # Should return the same instance
        assert isinstance(manager1, CanvasProcessManager)
        assert manager1 is manager2

    def test_get_monitoring_supervisor(self):
        """Test get_monitoring_supervisor function."""
        # Clear any existing instance
        import excalidraw_mcp.cli as cli_module
        cli_module._monitoring_supervisor = None

        # Get the supervisor
        supervisor1 = get_monitoring_supervisor()
        supervisor2 = get_monitoring_supervisor()

        # Should return the same instance
        assert isinstance(supervisor1, MonitoringSupervisor)
        assert supervisor1 is supervisor2

    @patch("excalidraw_mcp.cli.psutil.process_iter")
    def test_find_mcp_server_process(self, mock_process_iter):
        """Test find_mcp_server_process function."""
        # Create mock process
        mock_proc = Mock()
        mock_proc.info = {"cmdline": ["python", "-m", "excalidraw_mcp.server", "arg1"]}

        mock_process_iter.return_value = [mock_proc]

        result = find_mcp_server_process()
        assert result is mock_proc

    @patch("excalidraw_mcp.cli.psutil.process_iter")
    def test_find_mcp_server_process_not_found(self, mock_process_iter):
        """Test find_mcp_server_process function when not found."""
        mock_process_iter.return_value = []
        result = find_mcp_server_process()
        assert result is None

    @patch("excalidraw_mcp.cli.psutil.process_iter")
    def test_find_canvas_server_process(self, mock_process_iter):
        """Test find_canvas_server_process function."""
        # Create mock process
        mock_proc = Mock()
        mock_proc.info = {"cmdline": ["node", "src/server.js", "arg1"]}

        mock_process_iter.return_value = [mock_proc]

        result = find_canvas_server_process()
        assert result is mock_proc

    @patch("excalidraw_mcp.cli.psutil.process_iter")
    def test_find_canvas_server_process_dist(self, mock_process_iter):
        """Test find_canvas_server_process function with dist path."""
        # Create mock process
        mock_proc = Mock()
        mock_proc.info = {"cmdline": ["node", "dist/server.js", "arg1"]}

        mock_process_iter.return_value = [mock_proc]

        result = find_canvas_server_process()
        assert result is mock_proc

    @patch("excalidraw_mcp.cli.psutil.process_iter")
    def test_find_canvas_server_process_not_found(self, mock_process_iter):
        """Test find_canvas_server_process function when not found."""
        mock_process_iter.return_value = []
        result = find_canvas_server_process()
        assert result is None

    @patch("excalidraw_mcp.cli.find_mcp_server_process")
    @patch("excalidraw_mcp.cli.rprint")
    def test_serve_background_already_running(self, mock_rprint, mock_find_proc):
        """Test _serve_background when already running."""
        mock_find_proc.return_value = Mock(pid=1234)

        _serve_background()

        mock_rprint.assert_called_once()
        assert "already running" in str(mock_rprint.call_args)

    @patch("excalidraw_mcp.cli.find_mcp_server_process")
    @patch("excalidraw_mcp.cli.subprocess.Popen")
    @patch("excalidraw_mcp.cli.time.sleep")
    @patch("excalidraw_mcp.cli.rprint")
    def test_serve_background_starts_server(
        self, mock_rprint, mock_sleep, mock_popen, mock_find_proc
    ):
        """Test _serve_background starting server in background mode."""
        # First call: not running, second call: running successfully
        mock_process = Mock()
        mock_process.pid = 1234
        mock_find_proc.side_effect = [None, mock_process]
        mock_popen.return_value = Mock()

        _serve_background()

        mock_popen.assert_called_once()
        # Check that it tries to find the process after starting
        assert mock_sleep.called
        # Should have called find_mcp_server_process twice (before and after Popen)
        assert mock_find_proc.call_count == 2

    @patch("excalidraw_mcp.cli.find_mcp_server_process")
    @patch("excalidraw_mcp.cli.rprint")
    @patch("excalidraw_mcp.cli.get_monitoring_supervisor")
    @patch("excalidraw_mcp.cli.get_process_manager")
    @patch("excalidraw_mcp.cli.asyncio.run")
    def test_serve_http_foreground_with_monitoring(
        self, mock_asyncio_run, mock_get_pm, mock_get_sup, mock_rprint, mock_find_proc
    ):
        """Test _serve_http in foreground with monitoring."""
        mock_find_proc.return_value = None  # Not running
        mock_supervisor = Mock()
        mock_get_sup.return_value = mock_supervisor
        mock_pm = Mock()
        mock_get_pm.return_value = mock_pm

        _serve_http(monitoring=True)

        # Should run the async function
        assert mock_asyncio_run.called

    @patch("excalidraw_mcp.cli.find_mcp_server_process")
    @patch("excalidraw_mcp.cli.find_canvas_server_process")
    @patch("excalidraw_mcp.cli.rprint")
    def test_stop_no_processes(
        self, mock_rprint, mock_find_canvas, mock_find_mcp
    ):
        """Test stop when no processes are running."""
        mock_find_mcp.return_value = None
        mock_find_canvas.return_value = None

        # Call the function directly rather than through runner to ensure mocks work
        stop(force=False)

        mock_rprint.assert_called_once()
        assert "No MCP server processes found" in str(mock_rprint.call_args)

    @patch("excalidraw_mcp.cli._stop_process")
    @patch("excalidraw_mcp.cli.find_mcp_server_process")
    @patch("excalidraw_mcp.cli.find_canvas_server_process")
    @patch("excalidraw_mcp.cli.rprint")
    def test_stop_with_processes(
        self, mock_rprint, mock_find_canvas, mock_find_mcp, mock_stop_process
    ):
        """Test stop when processes are running."""
        mock_mcp_proc = Mock()
        mock_canvas_proc = Mock()
        mock_find_mcp.return_value = mock_mcp_proc
        mock_find_canvas.return_value = mock_canvas_proc
        mock_stop_process.side_effect = [
            "MCP server terminated",
            "Canvas server terminated",
        ]

        stop(force=False)

        assert mock_stop_process.call_count == 2

    @patch("excalidraw_mcp.cli.stop")
    @patch("excalidraw_mcp.cli._serve_http")
    @patch("excalidraw_mcp.cli.time.sleep")
    @patch("excalidraw_mcp.cli.rprint")
    def test_restart_server(
        self, mock_rprint, mock_sleep, mock_serve_http, mock_stop
    ):
        """Test restart."""
        restart(background=False, monitoring=True)

        mock_stop.assert_called_once_with(force=False)
        mock_sleep.assert_called_once_with(2)
        mock_serve_http.assert_called_once_with(monitoring=True)

    @patch("excalidraw_mcp.cli.find_mcp_server_process")
    @patch("excalidraw_mcp.cli.find_canvas_server_process")
    @patch("excalidraw_mcp.cli.rprint")
    @patch("excalidraw_mcp.cli.Config")
    @patch("excalidraw_mcp.cli.ServerPanels")
    def test_status_no_processes(
        self, mock_server_panels, mock_config, mock_rprint, mock_find_canvas, mock_find_mcp
    ):
        """Test status when no processes are running."""
        mock_find_mcp.return_value = None
        mock_find_canvas.return_value = None
        mock_config.return_value = Mock()
        mock_config.return_value.server.express_url = "http://localhost:3031"
        mock_config.return_value.server.canvas_auto_start = True
        mock_config.return_value.monitoring.enabled = True
        mock_config.return_value.monitoring.health_check_interval_seconds = 30

        status()

        # Should call ServerPanels methods when available
        assert mock_server_panels.server_status_table.called
        assert mock_server_panels.config_table.called

    @patch("excalidraw_mcp.cli.Path")
    def test_find_log_file_exists(self, mock_path):
        """Test _find_log_file when log file exists."""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        result = _find_log_file()
        assert result is mock_path_instance

    @patch("excalidraw_mcp.cli.Path")
    def test_find_log_file_not_exists(self, mock_path):
        """Test _find_log_file when log file doesn't exist."""
        # Create mock path instances that return False for exists()
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False

        # Mock Path() constructor calls and Path.home() calls
        mock_path.return_value = mock_path_instance
        mock_path.home.return_value = mock_path_instance

        # Mock __truediv__ to return instances that don't exist
        mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

        result = _find_log_file()
        assert result is None

    @patch("excalidraw_mcp.cli.rprint")
    def test_show_missing_log_message(self, mock_rprint):
        """Test _show_missing_log_message."""
        _show_missing_log_message()

        # Should print two messages
        assert mock_rprint.call_count >= 1

    @patch("excalidraw_mcp.cli._find_log_file")
    @patch("excalidraw_mcp.cli._show_missing_log_message")
    def test_logs_no_log_file(self, mock_show_missing, mock_find_log_file):
        """Test logs when no log file is found."""
        mock_find_log_file.return_value = None

        logs(lines=50, follow=False)

        mock_show_missing.assert_called_once()

    def test_cli_help(self):
        """Test CLI help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Excalidraw MCP Server" in result.output

    def test_serve_help(self):
        """Test serve subcommand help."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--stdio" in result.output
        assert "--http" in result.output

    def test_stop_help(self):
        """Test stop subcommand help."""
        result = runner.invoke(app, ["stop", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_status_help(self):
        """Test status subcommand help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_logs_help(self):
        """Test logs subcommand help."""
        result = runner.invoke(app, ["logs", "--help"])
        assert result.exit_code == 0
        assert "--lines" in result.output
        assert "--follow" in result.output
