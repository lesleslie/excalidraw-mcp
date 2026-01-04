"""CLI interface for excalidraw-mcp server management."""

import asyncio
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import typer

# ACB has been removed - using standard logging and Oneiric patterns
# from acb.console import Console
# from acb.depends import depends
from rich import print as rprint

# Check ServerPanels availability (Phase 3.3 M2: improved pattern)
try:
    from mcp_common.ui import ServerPanels

    SERVERPANELS_AVAILABLE = True
except ImportError:
    SERVERPANELS_AVAILABLE = False
    ServerPanels = None  # type: ignore

from excalidraw_mcp.config import Config
from excalidraw_mcp.monitoring.supervisor import MonitoringSupervisor
from excalidraw_mcp.process_manager import CanvasProcessManager

# console = depends.get_sync(Console)

# Global process manager instance
_process_manager: CanvasProcessManager | None = None
_monitoring_supervisor: MonitoringSupervisor | None = None


def get_process_manager() -> CanvasProcessManager:
    """Get or create process manager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = CanvasProcessManager()
    return _process_manager


def get_monitoring_supervisor() -> MonitoringSupervisor:
    """Get or create monitoring supervisor instance."""
    global _monitoring_supervisor
    if _monitoring_supervisor is None:
        _monitoring_supervisor = MonitoringSupervisor()
    return _monitoring_supervisor


def find_mcp_server_process() -> psutil.Process | None:
    """Find running MCP server process."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if cmdline and any("excalidraw_mcp.server" in arg for arg in cmdline):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def find_canvas_server_process() -> psutil.Process | None:
    """Find running canvas server process."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if cmdline and any(
                "src/server.js" in arg or "dist/server.js" in arg for arg in cmdline
            ):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def start_mcp_server_impl(background: bool = False, monitoring: bool = True) -> None:
    """Implementation for starting MCP server."""
    # Check if already running
    existing_proc = find_mcp_server_process()
    if existing_proc:
        rprint(
            f"[yellow]MCP server already running (PID: {existing_proc.pid})[/yellow]"
        )
        return

    rprint("[green]Starting Excalidraw MCP server...[/green]")

    try:
        if background:
            # Start in background
            subprocess.Popen(
                [sys.executable, "-m", "excalidraw_mcp.server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            # Wait a moment and check if it started
            time.sleep(2)
            proc = find_mcp_server_process()
            if proc:
                rprint(
                    f"[green]✓ MCP server started in background (PID: {proc.pid})[/green]"
                )
            else:
                rprint("[red]✗ Failed to start MCP server in background[/red]")
                sys.exit(1)
        else:
            # Start in foreground with optional monitoring
            if monitoring:
                # Start with monitoring supervisor
                async def run_with_monitoring() -> None:
                    supervisor = get_monitoring_supervisor()
                    process_manager = get_process_manager()

                    # Set up signal handlers for graceful shutdown
                    def signal_handler(signum: int, frame: Any) -> None:
                        rprint(
                            "\n[yellow]Received shutdown signal, stopping servers...[/yellow]"
                        )
                        asyncio.create_task(supervisor.stop())
                        asyncio.create_task(process_manager.stop())
                        sys.exit(0)

                    signal.signal(signal.SIGINT, signal_handler)
                    signal.signal(signal.SIGTERM, signal_handler)

                    # Start monitoring
                    await supervisor.start()

                    # Keep the process running
                    try:
                        # Import and run the main server
                        from excalidraw_mcp.server import main

                        await main()  # type: ignore
                    finally:
                        await supervisor.stop()

                asyncio.run(run_with_monitoring())
            else:
                # Start without monitoring
                from excalidraw_mcp.server import main

                asyncio.run(main())  # type: ignore

    except KeyboardInterrupt:
        rprint("\n[yellow]Shutting down MCP server...[/yellow]")
        # Clean up any running processes
        process_manager = get_process_manager()
        asyncio.run(process_manager.stop())
    except Exception as e:
        rprint(f"[red]Failed to start MCP server: {e}[/red]")
        sys.exit(1)


def _stop_process(
    process: psutil.Process, process_name: str, force: bool, timeout: int
) -> str:
    """Stop a single process and return a status message."""
    try:
        if force:
            process.kill()
            return f"{process_name} (PID: {process.pid}) - killed"
        else:
            process.terminate()
            try:
                process.wait(timeout=timeout)
                return f"{process_name} (PID: {process.pid}) - terminated"
            except psutil.TimeoutExpired:
                process.kill()
                return f"{process_name} (PID: {process.pid}) - force killed"
    except psutil.NoSuchProcess:
        return f"{process_name} - already stopped"
    except Exception as e:
        return f"{process_name} - failed to stop: {e}"


def stop_mcp_server_impl(force: bool = False) -> None:
    """Implementation for stopping MCP server."""
    mcp_proc = find_mcp_server_process()
    canvas_proc = find_canvas_server_process()

    if not mcp_proc and not canvas_proc:
        rprint("[yellow]No MCP server processes found running[/yellow]")
        return

    rprint("[yellow]Stopping Excalidraw MCP server...[/yellow]")

    stopped_procs = []

    # Stop MCP server
    if mcp_proc:
        status = _stop_process(mcp_proc, "MCP server", force, 10)
        if "failed to stop" in status:
            rprint(f"[red]Failed to stop MCP server: {status.split(': ')[-1]}[/red]")
        else:
            stopped_procs.append(status)

    # Stop canvas server
    if canvas_proc:
        status = _stop_process(canvas_proc, "Canvas server", force, 5)
        if "failed to stop" in status:
            rprint(f"[red]Failed to stop canvas server: {status.split(': ')[-1]}[/red]")
        else:
            stopped_procs.append(status)

    # Display results
    if stopped_procs:
        rprint("[green]✓ Stopped processes:[/green]")
        for proc_info in stopped_procs:
            rprint(f"  • {proc_info}")
    else:
        rprint("[yellow]No processes were stopped[/yellow]")


def restart_mcp_server_impl(background: bool = False, monitoring: bool = True) -> None:
    """Implementation for restarting MCP server."""
    rprint("[yellow]Restarting Excalidraw MCP server...[/yellow]")

    # Stop existing servers
    stop_mcp_server_impl()

    # Wait a moment for processes to fully stop
    time.sleep(2)

    # Start server again
    start_mcp_server_impl(background=background)


def status_impl() -> None:
    """Implementation for showing status."""
    rows: list[list[str]] = []

    # Check MCP server
    mcp_proc = find_mcp_server_process()
    if mcp_proc:
        try:
            cpu_percent = mcp_proc.cpu_percent()
            memory_mb = mcp_proc.memory_info().rss / 1024 / 1024
            rows.append(
                [
                    "MCP Server",
                    "[green]Running[/green]",
                    str(mcp_proc.pid),
                    f"CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB",
                ]
            )
        except psutil.NoSuchProcess:
            rows.append(["MCP Server", "[red]Stopped[/red]", "-", "-"])
    else:
        rows.append(["MCP Server", "[red]Stopped[/red]", "-", "-"])

    # Check canvas server
    canvas_proc = find_canvas_server_process()
    if canvas_proc:
        try:
            cpu_percent = canvas_proc.cpu_percent()
            memory_mb = canvas_proc.memory_info().rss / 1024 / 1024
            rows.append(
                [
                    "Canvas Server",
                    "[green]Running[/green]",
                    str(canvas_proc.pid),
                    f"CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB",
                ]
            )
        except psutil.NoSuchProcess:
            rows.append(["Canvas Server", "[red]Stopped[/red]", "-", "-"])
    else:
        rows.append(["Canvas Server", "[red]Stopped[/red]", "-", "-"])

    if SERVERPANELS_AVAILABLE and ServerPanels:
        ServerPanels.server_status_table(
            rows,
            title="Excalidraw MCP Server Status",
            headers=("Component", "Status", "PID", "Details"),
        )
    else:
        # Fallback to simple output if ServerPanels is not available
        rprint("[bold]Excalidraw MCP Server Status[/bold]")
        for row in rows:
            rprint(" | ".join(row))

    # Show configuration info
    config = Config()
    if SERVERPANELS_AVAILABLE and ServerPanels:
        ServerPanels.config_table(
            title="Server Configuration",
            items={
                "Canvas URL": config.server.express_url,
                "Canvas Auto-start": config.server.canvas_auto_start,
                "Monitoring": config.monitoring.enabled,
                "Health Check Interval": f"{config.monitoring.health_check_interval_seconds}s",
            },
        )
    else:
        # Fallback to simple output if ServerPanels is not available
        rprint("[bold]Server Configuration[/bold]")
        rprint(f"Canvas URL: {config.server.express_url}")
        rprint(f"Canvas Auto-start: {config.server.canvas_auto_start}")
        rprint(f"Monitoring: {config.monitoring.enabled}")
        rprint(
            f"Health Check Interval: {config.monitoring.health_check_interval_seconds}s"
        )


def _find_log_file() -> Path | None:
    """Find the log file in common locations."""
    log_paths = [
        Path("excalidraw-mcp.log"),
        Path("logs/excalidraw-mcp.log"),
        Path.home() / "tmp" / "excalidraw-mcp.log",
        Path.home() / ".local" / "state" / "excalidraw-mcp" / "server.log",
    ]

    for path in log_paths:
        if path.exists():
            return path
    return None


def _show_missing_log_message() -> None:
    """Show message when log file is not found."""
    rprint("[yellow]No log file found. Logs may be going to stdout/stderr.[/yellow]")
    rprint("Try running the server with output redirection:")
    rprint("  [cyan]excalidraw-mcp --start-mcp-server > server.log 2>&1[/cyan]")


def _follow_log_output(log_file: Path) -> None:
    """Follow log output (basic implementation)."""
    with log_file.open() as f:
        # Move to end of file
        f.seek(0, 2)
        while True:
            line = f.readline()
            if line:
                print(line.rstrip())
            else:
                time.sleep(0.1)


def _show_recent_log_lines(log_file: Path, lines: int) -> None:
    """Show recent lines from log file."""
    with log_file.open() as f:
        # Read all lines and show last N
        all_lines = f.readlines()
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        for line in recent_lines:
            print(line.rstrip())


def logs_impl(lines: int = 50, follow: bool = False) -> None:
    """Implementation for showing logs."""
    log_file = _find_log_file()

    if not log_file:
        _show_missing_log_message()
        return

    try:
        if follow:
            _follow_log_output(log_file)
        else:
            _show_recent_log_lines(log_file, lines)
    except KeyboardInterrupt:
        rprint("\n[yellow]Stopped following logs[/yellow]")
    except Exception as e:
        rprint(f"[red]Error reading logs: {e}[/red]")


def main(
    start_mcp_server: bool = typer.Option(
        False, "--start-mcp-server", help="Start the Excalidraw MCP server"
    ),
    stop_mcp_server: bool = typer.Option(
        False, "--stop-mcp-server", help="Stop the Excalidraw MCP server"
    ),
    restart_mcp_server: bool = typer.Option(
        False, "--restart-mcp-server", help="Restart the Excalidraw MCP server"
    ),
    status: bool = typer.Option(
        False, "--status", help="Show status of MCP server and canvas server"
    ),
    logs: bool = typer.Option(False, "--logs", help="Show server logs (if available)"),
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Run MCP server in background (for start/restart commands)",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force kill server processes (for stop command)"
    ),
    monitoring: bool = typer.Option(
        True,
        "--monitoring/--no-monitoring",
        help="Enable monitoring supervisor (for start/restart commands)",
    ),
    lines: int = typer.Option(
        50,
        "--lines",
        "-n",
        help="Number of recent log lines to show (for logs command)",
    ),
    follow: bool = typer.Option(
        False, "--follow", help="Follow log output (for logs command)"
    ),
) -> None:
    """CLI for managing Excalidraw MCP server."""

    # Count how many main actions were requested
    actions = [start_mcp_server, stop_mcp_server, restart_mcp_server, status, logs]
    action_count = sum(1 for action in actions if action)

    if action_count == 0:
        # No action specified, show help
        rprint(
            "[yellow]No action specified. Use --help to see available options.[/yellow]"
        )
        return
    elif action_count > 1:
        # Multiple actions specified
        rprint("[red]Error: Only one action can be specified at a time.[/red]")
        sys.exit(1)

    # Execute the requested action
    if start_mcp_server:
        start_mcp_server_impl(background=background, monitoring=monitoring)
    elif stop_mcp_server:
        stop_mcp_server_impl(force=force)
    elif restart_mcp_server:
        restart_mcp_server_impl(background=background, monitoring=monitoring)
    elif status:
        status_impl()
    elif logs:
        logs_impl()


app = typer.Typer()
app.command()(main)

if __name__ == "__main__":
    app()
