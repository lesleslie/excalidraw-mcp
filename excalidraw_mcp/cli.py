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
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from excalidraw_mcp.config import Config
from excalidraw_mcp.monitoring.supervisor import MonitoringSupervisor
from excalidraw_mcp.process_manager import CanvasProcessManager

console = Console()

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
        try:
            if force:
                mcp_proc.kill()
                stopped_procs.append(f"MCP server (PID: {mcp_proc.pid}) - killed")
            else:
                mcp_proc.terminate()
                try:
                    mcp_proc.wait(timeout=10)
                    stopped_procs.append(
                        f"MCP server (PID: {mcp_proc.pid}) - terminated"
                    )
                except psutil.TimeoutExpired:
                    mcp_proc.kill()
                    stopped_procs.append(
                        f"MCP server (PID: {mcp_proc.pid}) - force killed"
                    )
        except psutil.NoSuchProcess:
            stopped_procs.append("MCP server - already stopped")
        except Exception as e:
            rprint(f"[red]Failed to stop MCP server: {e}[/red]")

    # Stop canvas server
    if canvas_proc:
        try:
            if force:
                canvas_proc.kill()
                stopped_procs.append(f"Canvas server (PID: {canvas_proc.pid}) - killed")
            else:
                canvas_proc.terminate()
                try:
                    canvas_proc.wait(timeout=5)
                    stopped_procs.append(
                        f"Canvas server (PID: {canvas_proc.pid}) - terminated"
                    )
                except psutil.TimeoutExpired:
                    canvas_proc.kill()
                    stopped_procs.append(
                        f"Canvas server (PID: {canvas_proc.pid}) - force killed"
                    )
        except psutil.NoSuchProcess:
            stopped_procs.append("Canvas server - already stopped")
        except Exception as e:
            rprint(f"[red]Failed to stop canvas server: {e}[/red]")

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
    stop_mcp_server_impl(force=False)

    # Wait a moment for processes to fully stop
    time.sleep(2)

    # Start server again
    start_mcp_server_impl(background=background, monitoring=monitoring)


def status_impl() -> None:
    """Implementation for showing status."""
    table = Table(title="Excalidraw MCP Server Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("PID", style="yellow")
    table.add_column("Details", style="white")

    # Check MCP server
    mcp_proc = find_mcp_server_process()
    if mcp_proc:
        try:
            cpu_percent = mcp_proc.cpu_percent()
            memory_mb = mcp_proc.memory_info().rss / 1024 / 1024
            table.add_row(
                "MCP Server",
                "[green]Running[/green]",
                str(mcp_proc.pid),
                f"CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB",
            )
        except psutil.NoSuchProcess:
            table.add_row("MCP Server", "[red]Stopped[/red]", "-", "-")
    else:
        table.add_row("MCP Server", "[red]Stopped[/red]", "-", "-")

    # Check canvas server
    canvas_proc = find_canvas_server_process()
    if canvas_proc:
        try:
            cpu_percent = canvas_proc.cpu_percent()
            memory_mb = canvas_proc.memory_info().rss / 1024 / 1024
            table.add_row(
                "Canvas Server",
                "[green]Running[/green]",
                str(canvas_proc.pid),
                f"CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB",
            )
        except psutil.NoSuchProcess:
            table.add_row("Canvas Server", "[red]Stopped[/red]", "-", "-")
    else:
        table.add_row("Canvas Server", "[red]Stopped[/red]", "-", "-")

    console.print(table)

    # Show configuration info
    config = Config()
    config_panel = Panel.fit(
        f"[bold]Configuration[/bold]\n"
        f"Canvas URL: {config.server.express_url}\n"
        f"Canvas Auto-start: {config.server.canvas_auto_start}\n"
        f"Monitoring: {config.monitoring.enabled}\n"
        f"Health Check Interval: {config.monitoring.health_check_interval_seconds}s",
        title="Server Configuration",
    )
    console.print("\n")
    console.print(config_panel)


def logs_impl(lines: int = 50, follow: bool = False) -> None:
    """Implementation for showing logs."""
    # Look for common log file locations
    log_paths = [
        Path("excalidraw-mcp.log"),
        Path("logs/excalidraw-mcp.log"),
        Path("/tmp/excalidraw-mcp.log"),
        Path.home() / ".local" / "state" / "excalidraw-mcp" / "server.log",
    ]

    log_file = None
    for path in log_paths:
        if path.exists():
            log_file = path
            break

    if not log_file:
        rprint(
            "[yellow]No log file found. Logs may be going to stdout/stderr.[/yellow]"
        )
        rprint("Try running the server with output redirection:")
        rprint("  [cyan]excalidraw-mcp --start-mcp-server > server.log 2>&1[/cyan]")
        return

    try:
        if follow:
            # Follow log output (basic implementation)
            rprint(f"[green]Following logs from: {log_file}[/green]")
            rprint("[yellow]Press Ctrl+C to stop[/yellow]\n")

            subprocess.run(["tail", "-f", str(log_file)])
        else:
            # Show recent logs
            with open(log_file) as f:
                log_lines = f.readlines()
                recent_lines = (
                    log_lines[-lines:] if len(log_lines) > lines else log_lines
                )

                rprint(f"[green]Recent logs from: {log_file}[/green]\n")
                for line in recent_lines:
                    print(line.rstrip())

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
    action_count = sum(actions)

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
        logs_impl(lines=lines, follow=follow)


app = typer.Typer()
app.command()(main)

if __name__ == "__main__":
    app()
