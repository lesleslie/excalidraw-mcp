"""Metrics collection system for monitoring canvas server performance."""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

import psutil

from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""

    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class Counter:
    """Counter metric that only increases."""

    name: str
    help_text: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)

    def inc(self, amount: float = 1.0) -> None:
        """Increment counter by amount."""
        self.value += amount

    def reset(self) -> None:
        """Reset counter to zero."""
        self.value = 0.0


@dataclass
class Gauge:
    """Gauge metric that can increase or decrease."""

    name: str
    help_text: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        """Set gauge to specific value."""
        self.value = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge by amount."""
        self.value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge by amount."""
        self.value -= amount


@dataclass
class Histogram:
    """Histogram metric for tracking distributions."""

    name: str
    help_text: str
    buckets: list[float] = field(
        default_factory=lambda: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    counts: dict[float, int] = field(default_factory=dict)
    sum_value: float = 0.0
    count: int = 0
    labels: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Initialize bucket counts
        for bucket in self.buckets:
            self.counts[bucket] = 0
        self.counts[float("inf")] = 0

    def observe(self, value: float) -> None:
        """Record an observation."""
        self.sum_value += value
        self.count += 1

        # Update bucket counts
        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1
        self.counts[float("inf")] += 1

    def reset(self) -> None:
        """Reset histogram."""
        self.counts = {bucket: 0 for bucket in self.buckets}
        self.counts[float("inf")] = 0
        self.sum_value = 0.0
        self.count = 0

    @property
    def average(self) -> float:
        """Get average value."""
        return self.sum_value / max(self.count, 1)


class MetricsCollector:
    """Collects and manages metrics for canvas server monitoring."""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._history: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._collection_task: asyncio.Task | None = None
        self._running = False
        self._lock = asyncio.Lock()

        # Initialize standard metrics
        self._initialize_standard_metrics()

    def _initialize_standard_metrics(self) -> None:
        """Initialize standard metrics for canvas server monitoring."""

        # HTTP request metrics
        self.register_counter(
            "http_requests_total",
            "Total number of HTTP requests",
            {"method": "GET", "endpoint": "/health", "status": "200"},
        )
        self.register_counter(
            "http_request_errors_total",
            "Total number of HTTP request errors",
            {"method": "GET", "endpoint": "/health"},
        )
        self.register_histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )

        # Health check metrics
        self.register_counter(
            "health_checks_total", "Total number of health checks performed"
        )
        self.register_counter(
            "health_check_failures_total", "Total number of failed health checks"
        )
        self.register_gauge(
            "health_check_consecutive_failures",
            "Number of consecutive health check failures",
        )
        self.register_histogram(
            "health_check_duration_seconds", "Health check duration in seconds"
        )

        # Process metrics
        self.register_gauge("process_cpu_percent", "Process CPU usage percentage")
        self.register_gauge("process_memory_bytes", "Process memory usage in bytes")
        self.register_gauge("process_memory_percent", "Process memory usage percentage")
        self.register_gauge("process_threads_count", "Number of process threads")

        # Canvas server metrics
        self.register_counter(
            "canvas_restarts_total", "Total number of canvas server restarts"
        )
        self.register_gauge("canvas_uptime_seconds", "Canvas server uptime in seconds")
        self.register_gauge(
            "canvas_elements_count", "Current number of elements on canvas"
        )

        # Circuit breaker metrics
        self.register_counter(
            "circuit_breaker_state_changes_total", "Circuit breaker state changes"
        )
        self.register_counter(
            "circuit_breaker_calls_total", "Circuit breaker total calls"
        )
        self.register_counter(
            "circuit_breaker_failures_total", "Circuit breaker failures"
        )
        self.register_counter(
            "circuit_breaker_rejections_total", "Circuit breaker rejections"
        )

    def register_counter(
        self, name: str, help_text: str, labels: dict[str, str] | None = None
    ) -> Counter:
        """Register a new counter metric."""
        counter = Counter(name, help_text, labels=labels or {})
        self._counters[name] = counter
        return counter

    def register_gauge(
        self, name: str, help_text: str, labels: dict[str, str] | None = None
    ) -> Gauge:
        """Register a new gauge metric."""
        gauge = Gauge(name, help_text, labels=labels or {})
        self._gauges[name] = gauge
        return gauge

    def register_histogram(
        self, name: str, help_text: str, buckets: list[float] | None = None
    ) -> Histogram:
        """Register a new histogram metric."""
        histogram = Histogram(name, help_text, buckets=buckets or [])
        self._histograms[name] = histogram
        return histogram

    def get_counter(self, name: str) -> Counter | None:
        """Get counter by name."""
        return self._counters.get(name)

    def get_gauge(self, name: str) -> Gauge | None:
        """Get gauge by name."""
        return self._gauges.get(name)

    def get_histogram(self, name: str) -> Histogram | None:
        """Get histogram by name."""
        return self._histograms.get(name)

    def increment_counter(
        self, name: str, amount: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        counter = self._counters.get(name)
        if counter:
            if labels:
                counter.labels.update(labels)
            counter.inc(amount)

    def set_gauge(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Set a gauge metric value."""
        gauge = self._gauges.get(name)
        if gauge:
            if labels:
                gauge.labels.update(labels)
            gauge.set(value)

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a histogram observation."""
        histogram = self._histograms.get(name)
        if histogram:
            if labels:
                histogram.labels.update(labels)
            histogram.observe(value)

    async def collect_system_metrics(self) -> None:
        """Collect system and process metrics."""
        if not config.monitoring.resource_monitoring_enabled:
            return

        try:
            from ..process_manager import process_manager

            # Process metrics
            if process_manager.process_pid:
                try:
                    process = psutil.Process(process_manager.process_pid)

                    self.set_gauge("process_cpu_percent", process.cpu_percent())

                    memory_info = process.memory_info()
                    self.set_gauge("process_memory_bytes", memory_info.rss)
                    self.set_gauge("process_memory_percent", process.memory_percent())
                    self.set_gauge("process_threads_count", process.num_threads())

                    # Calculate uptime
                    create_time = process.create_time()
                    uptime = time.time() - create_time
                    self.set_gauge("canvas_uptime_seconds", uptime)

                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning(f"Failed to collect process metrics: {e}")

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    async def collect_canvas_metrics(self) -> None:
        """Collect canvas-specific metrics."""
        try:
            from ..http_client import http_client

            # Get element count
            elements = await http_client.get_json("/api/elements")
            if elements is not None:
                element_count = (
                    len(elements)
                    if elements is not None and isinstance(elements, list)
                    else 0
                )  # type: ignore
                self.set_gauge("canvas_elements_count", element_count)

        except Exception as e:
            logger.debug(f"Could not collect canvas metrics: {e}")

    async def start_collection(self) -> None:
        """Start automatic metrics collection."""
        if self._running:
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collection started")

    async def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        if not self._running:
            return

        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collection stopped")

    async def _collection_loop(self) -> None:
        """Main metrics collection loop."""
        while self._running:
            try:
                async with self._lock:
                    if config.monitoring.metrics_enabled:
                        await self.collect_system_metrics()
                        await self.collect_canvas_metrics()

                        # Store historical data
                        timestamp = time.time()
                        for name, gauge in self._gauges.items():
                            self._history[name].append(
                                MetricPoint(timestamp, gauge.value, gauge.labels.copy())
                            )

                await asyncio.sleep(
                    config.monitoring.metrics_collection_interval_seconds
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics in a structured format."""
        return {
            "counters": {
                name: {
                    "value": counter.value,
                    "help": counter.help_text,
                    "labels": counter.labels,
                }
                for name, counter in self._counters.items()
            },
            "gauges": {
                name: {
                    "value": gauge.value,
                    "help": gauge.help_text,
                    "labels": gauge.labels,
                }
                for name, gauge in self._gauges.items()
            },
            "histograms": {
                name: {
                    "count": hist.count,
                    "sum": hist.sum_value,
                    "average": hist.average,
                    "buckets": dict(hist.counts),
                    "help": hist.help_text,
                    "labels": hist.labels,
                }
                for name, hist in self._histograms.items()
            },
        }

    def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Counters
        for name, counter in self._counters.items():
            lines.append(f"# HELP {name} {counter.help_text}")
            lines.append(f"# TYPE {name} counter")
            label_str = ",".join(f'{k}="{v}"' for k, v in counter.labels.items())
            if label_str:
                lines.append(f"{name}{{{label_str}}} {counter.value}")
            else:
                lines.append(f"{name} {counter.value}")

        # Gauges
        for name, gauge in self._gauges.items():
            lines.append(f"# HELP {name} {gauge.help_text}")
            lines.append(f"# TYPE {name} gauge")
            label_str = ",".join(f'{k}="{v}"' for k, v in gauge.labels.items())
            if label_str:
                lines.append(f"{name}{{{label_str}}} {gauge.value}")
            else:
                lines.append(f"{name} {gauge.value}")

        # Histograms
        for name, hist in self._histograms.items():
            lines.append(f"# HELP {name} {hist.help_text}")
            lines.append(f"# TYPE {name} histogram")

            label_str = ",".join(f'{k}="{v}"' for k, v in hist.labels.items())
            base_labels = f",{label_str}" if label_str else ""

            # Buckets
            for bucket, count in hist.counts.items():
                bucket_str = "+Inf" if bucket == float("inf") else str(bucket)
                lines.append(f'{name}_bucket{{le="{bucket_str}"{base_labels}}} {count}')

            # Count and sum
            lines.append(f"{name}_count{{{label_str}}} {hist.count}")
            lines.append(f"{name}_sum{{{label_str}}} {hist.sum_value}")

        return "\n".join(lines) + "\n"

    def reset_all_metrics(self) -> None:
        """Reset all metrics to initial state."""
        for counter in self._counters.values():
            counter.reset()
        for gauge in self._gauges.values():
            gauge.set(0.0)
        for histogram in self._histograms.values():
            histogram.reset()
        self._history.clear()
        logger.info("All metrics reset")

    def get_metric_history(
        self, name: str, limit: int | None = None
    ) -> list[MetricPoint]:
        """Get historical data for a metric."""
        history = list(self._history.get(name, []))
        if limit:
            history = history[-limit:]
        return history
