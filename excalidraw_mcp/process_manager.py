"""Process management for canvas server lifecycle."""

import asyncio
import atexit
import logging
import os
import signal
import subprocess
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import psutil

from .config import config
from .http_client import http_client

logger = logging.getLogger(__name__)


class CanvasProcessManager:
    """Manages the canvas server process lifecycle with monitoring hooks."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[Any] | None = None
        self.process_pid: int | None = None
        self._startup_lock = asyncio.Lock()
        self._start_time: float | None = None
        self._restart_count = 0

        # Event hooks for monitoring integration
        self._on_start_callbacks: list[Callable[..., Awaitable[None]]] = []
        self._on_stop_callbacks: list[Callable[..., Awaitable[None]]] = []
        self._on_restart_callbacks: list[Callable[..., Awaitable[None]]] = []
        self._on_health_change_callbacks: list[Callable[..., Awaitable[None]]] = []

        # Register cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    async def ensure_running(self) -> bool:
        """Ensure canvas server is running and healthy."""
        async with self._startup_lock:
            # Check if process is already running and healthy
            if await self._is_process_healthy():
                return True

            # If auto-start is disabled, just check health
            if not config.server.canvas_auto_start:
                logger.warning("Canvas server not running and auto-start is disabled")
                return False

            # Try to start the process
            success = await self._start_process()
            if not success:
                logger.error("Failed to start canvas server")
                return False

            # Wait for process to become healthy
            return await self._wait_for_health()

    async def _is_process_healthy(self) -> bool:
        """Check if the current process is running and healthy."""
        if not self._is_process_running():
            return False

        return await http_client.check_health()

    def _is_process_running(self) -> bool:
        """Check if the canvas server process is running."""
        if not self.process or not self.process_pid:
            return False

        try:
            # Check if process is still running
            if self.process.poll() is not None:
                logger.debug("Canvas server process has exited")
                self._reset_process_info()
                return False

            # Verify PID is valid
            if not psutil.pid_exists(self.process_pid):
                logger.debug("Canvas server PID no longer exists")
                self._reset_process_info()
                return False

            return True

        except Exception as e:
            logger.debug(f"Error checking process status: {e}")
            self._reset_process_info()
            return False

    async def _start_process(self) -> bool:
        """Start the canvas server process."""
        try:
            project_root = self._get_project_root()
            logger.info(f"Starting canvas server from {project_root}")

            # Kill any existing process
            self._terminate_existing_process()

            # Start new process
            self.process = subprocess.Popen(
                ["npm", "run", "canvas"],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            self.process_pid = self.process.pid
            self._start_time = time.time()
            logger.info(f"Canvas server started with PID: {self.process_pid}")

            # Trigger start callbacks
            await self._trigger_callbacks(self._on_start_callbacks, self.process_pid)

            # Give the server a moment to start
            await asyncio.sleep(config.server.startup_retry_delay_seconds)

            return True

        except Exception as e:
            logger.error(f"Failed to start canvas server: {e}")
            self._reset_process_info()
            return False

    async def _wait_for_health(self) -> bool:
        """Wait for canvas server to become healthy."""
        logger.info("Waiting for canvas server to become healthy...")

        for _ in range(config.server.startup_timeout_seconds):
            if not self._is_process_running():
                logger.error("Canvas server process died during startup")
                return False

            if await http_client.check_health(force=True):
                logger.info("Canvas server is healthy and ready")
                return True

            await asyncio.sleep(1)

        logger.error("Canvas server failed to become healthy within timeout")
        self._terminate_current_process()
        return False

    def _terminate_existing_process(self) -> None:
        """Terminate any existing canvas server process."""
        if self.process_pid:
            try:
                # Trigger stop callbacks before termination
                asyncio.create_task(
                    self._trigger_callbacks(
                        self._on_stop_callbacks, self.process_pid, "terminating"
                    )
                )

                # Try to find and kill the process group
                if self.process is not None:
                    if os.name != "nt":
                        os.killpg(os.getpgid(self.process_pid), signal.SIGTERM)
                    else:
                        self.process.terminate()

                # Wait a moment for graceful shutdown
                time.sleep(2)

                # Force kill if still running
                if self.process is not None and psutil.pid_exists(self.process_pid):
                    if os.name != "nt":
                        os.killpg(os.getpgid(self.process_pid), signal.SIGKILL)
                    else:
                        self.process.kill()

            except (ProcessLookupError, OSError) as e:
                logger.debug(f"Process already terminated: {e}")
            except Exception as e:
                logger.warning(f"Error terminating existing process: {e}")

        self._reset_process_info()

    def _terminate_current_process(self) -> None:
        """Terminate the current canvas server process."""
        self._terminate_existing_process()

    def _reset_process_info(self) -> None:
        """Reset process information."""
        was_running = self.process_pid is not None
        self.process = None
        self.process_pid = None
        self._start_time = None

        if was_running:
            # Trigger stop callbacks when process info is reset
            try:
                asyncio.create_task(
                    self._trigger_callbacks(self._on_stop_callbacks, None, "stopped")
                )
            except RuntimeError:
                # No running event loop, skip callback triggering
                logger.debug("No event loop running, skipping stop callbacks")

    def _get_project_root(self) -> Path:
        """Get the project root directory."""
        current_file = Path(__file__).resolve()
        return current_file.parent.parent

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle system signals for graceful shutdown."""
        logger.info(f"Received signal {signum}, cleaning up...")
        self.cleanup()

    def cleanup(self) -> None:
        """Clean up resources and terminate processes."""
        logger.info("Cleaning up canvas process manager...")
        self._terminate_current_process()

    async def restart(self) -> bool:
        """Restart the canvas server."""
        logger.info("Restarting canvas server...")
        self._restart_count += 1

        # Trigger restart callbacks
        await self._trigger_callbacks(
            self._on_restart_callbacks, self._restart_count, "starting"
        )

        self._terminate_current_process()
        success = await self.ensure_running()

        # Trigger restart completion callbacks
        status = "success" if success else "failed"
        await self._trigger_callbacks(
            self._on_restart_callbacks, self._restart_count, status
        )

        return success

    async def stop(self) -> None:
        """Stop the canvas server."""
        logger.info("Stopping canvas server...")
        self._terminate_current_process()

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive process status information."""
        is_running = self._is_process_running()
        uptime = (
            time.time() - self._start_time if self._start_time and is_running else 0
        )

        return {
            "running": is_running,
            "pid": self.process_pid,
            "healthy": False,  # Will be updated by health check
            "auto_start_enabled": config.server.canvas_auto_start,
            "start_time": self._start_time,
            "uptime_seconds": uptime,
            "restart_count": self._restart_count,
        }

    # Event hook management methods
    def add_start_callback(self, callback: Callable[..., Awaitable[None]]) -> None:
        """Add callback for process start events."""
        self._on_start_callbacks.append(callback)

    def add_stop_callback(self, callback: Callable[..., Awaitable[None]]) -> None:
        """Add callback for process stop events."""
        self._on_stop_callbacks.append(callback)

    def add_restart_callback(self, callback: Callable[..., Awaitable[None]]) -> None:
        """Add callback for process restart events."""
        self._on_restart_callbacks.append(callback)

    def add_health_change_callback(
        self, callback: Callable[..., Awaitable[None]]
    ) -> None:
        """Add callback for health status changes."""
        self._on_health_change_callbacks.append(callback)

    async def _trigger_callbacks(
        self, callbacks: list[Callable[..., Awaitable[None]]], *args: Any
    ) -> None:
        """Trigger a list of callbacks with error handling."""
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
            except Exception as e:
                logger.error(f"Error in process manager callback: {e}")

    def get_restart_count(self) -> int:
        """Get the number of times the process has been restarted."""
        return self._restart_count

    def get_uptime(self) -> float:
        """Get process uptime in seconds."""
        if not self._start_time or not self._is_process_running():
            return 0.0
        return time.time() - self._start_time


# Global process manager instance
process_manager = CanvasProcessManager()
