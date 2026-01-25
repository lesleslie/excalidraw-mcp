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
from .retry_utils import RetryConfig, retry_async

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

    async def _check_process_health(self) -> bool:
        """Check if process is already running and healthy."""
        return await self._is_process_healthy()

    async def _handle_disabled_auto_start(self) -> bool:
        """Handle case when auto-start is disabled."""
        logger.warning("Canvas server not running and auto-start is disabled")
        return False

    async def _attempt_process_start(self) -> bool:
        """Attempt to start the canvas server process."""
        success = await self._start_process()
        if not success:
            logger.error("Failed to start canvas server")
        return success

    async def _ensure_process_healthy(self) -> bool:
        """Ensure process is healthy or start it if needed."""
        # Check if process is already running and healthy
        if await self._check_process_health():
            return True

        # If auto-start is disabled, just check health
        if not config.server.canvas_auto_start:
            return await self._handle_disabled_auto_start()

        # Try to start the process
        if not await self._attempt_process_start():
            return False

        # Wait for process to become healthy
        return await self._wait_for_health()

    async def start(self) -> bool:
        """Start the canvas server if not already running."""
        return await self.ensure_running()

    async def ensure_running(self) -> bool:
        """Ensure canvas server is running and healthy."""
        async with self._startup_lock:
            return await self._ensure_process_healthy()

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
            server_js = self._find_server_js()
            if not server_js:
                logger.error("Could not find canvas server (dist/server.js)")
                return False
            logger.info(f"Starting canvas server from {server_js}")

            # Kill any existing process
            self._terminate_existing_process()

            # Start new process using node directly (works with uvx)
            self.process = subprocess.Popen(
                ["node", str(server_js)],
                cwd=server_js.parent,
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

    async def _check_health_with_process_check(self) -> bool:
        """Check health with process validation."""
        if not self._is_process_running():
            raise RuntimeError("Canvas server process died during startup")

        if await http_client.check_health(force=True):
            return True
        else:
            raise RuntimeError("Canvas server not yet healthy")

    async def _wait_for_health(self) -> bool:
        """Wait for canvas server to become healthy."""
        logger.info("Waiting for canvas server to become healthy...")

        # Configure retry for health checks
        retry_config = RetryConfig(
            max_attempts=config.server.startup_timeout_seconds,
            max_delay=5.0,
            exponential_base=config.server.sync_retry_exponential_base,
            jitter=config.server.sync_retry_jitter,
        )

        try:
            await retry_async(
                self._check_health_with_process_check,
                retry_config=retry_config,
                retry_on_exceptions=(RuntimeError, Exception),
            )
            logger.info("Canvas server is healthy and ready")
            return True
        except Exception as e:
            logger.error(f"Canvas server failed to become healthy: {e}")
            self._terminate_current_process()
            return False

    def _send_termination_signal(self, sig: int) -> None:
        """Send termination signal to the process group."""
        if self.process is not None and self.process_pid is not None:
            if os.name != "nt":
                os.killpg(os.getpgid(self.process_pid), sig)
            else:
                if sig == signal.SIGTERM:
                    self.process.terminate()
                else:
                    self.process.kill()

    def _terminate_existing_process(self) -> None:
        """Terminate any existing canvas server process."""
        if self.process_pid:
            try:
                # Trigger stop callbacks before termination (if event loop exists)
                self._trigger_callbacks_sync(
                    self._on_stop_callbacks, self.process_pid, "terminating"
                )

                # Try to find and kill the process group
                self._send_termination_signal(signal.SIGTERM)

                # Wait a moment for graceful shutdown
                time.sleep(2)

                # Force kill if still running
                if self.process is not None and psutil.pid_exists(self.process_pid):
                    self._send_termination_signal(signal.SIGKILL)

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
            # Trigger stop callbacks when process info is reset (if event loop exists)
            self._trigger_callbacks_sync(self._on_stop_callbacks, None, "stopped")

    def _find_server_js(self) -> Path | None:
        """Find the canvas server.js file.
        
        Looks in multiple locations to support both:
        - Local development (project root/dist/server.js)
        - uvx installation (package/dist/server.js bundled in wheel)
        """
        current_file = Path(__file__).resolve()
        package_dir = current_file.parent  # excalidraw_mcp/
        
        # Candidate locations for server.js
        candidates = [
            # Bundled in package (uvx/pip install)
            package_dir / "dist" / "server.js",
            # Development: project root
            package_dir.parent / "dist" / "server.js",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                logger.debug(f"Found canvas server at: {candidate}")
                return candidate
        
        logger.warning(f"Canvas server not found. Searched: {candidates}")
        return None

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

    def _trigger_callbacks_sync(
        self, callbacks: list[Callable[..., Awaitable[None]]], *args: Any
    ) -> None:
        """Trigger callbacks from synchronous context, safely handling async callbacks."""
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Check if there's an active event loop
                    try:
                        loop = asyncio.get_running_loop()
                        # Schedule the coroutine on the existing loop
                        loop.create_task(callback(*args))
                    except RuntimeError:
                        # No running event loop, skip async callbacks
                        logger.debug("No running event loop, skipping async callback")
                else:
                    # Call sync callbacks directly
                    callback(*args)
            except Exception as e:
                logger.error(f"Error in process manager callback: {e}")

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
