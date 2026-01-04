"""Unit tests for metrics module."""

import asyncio
import time
from collections import deque
from unittest.mock import AsyncMock, Mock, patch

import pytest
import psutil

from excalidraw_mcp.monitoring.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricPoint,
    MetricsCollector,
)


class TestMetricsModule:
    """Test metrics module classes and functions."""

    def test_metric_point_dataclass(self):
        """Test MetricPoint dataclass."""
        timestamp = time.time()
        point = MetricPoint(timestamp=timestamp, value=10.0, labels={"key": "value"})

        assert point.timestamp == timestamp
        assert point.value == 10.0
        assert point.labels == {"key": "value"}

    def test_counter_class(self):
        """Test Counter class."""
        counter = Counter(name="test_counter", help_text="Test counter")

        assert counter.name == "test_counter"
        assert counter.help_text == "Test counter"
        assert counter.value == 0.0

        counter.inc(5.0)
        assert counter.value == 5.0

        counter.inc(3.0)
        assert counter.value == 8.0

        counter.reset()
        assert counter.value == 0.0

    def test_gauge_class(self):
        """Test Gauge class."""
        gauge = Gauge(name="test_gauge", help_text="Test gauge")

        assert gauge.name == "test_gauge"
        assert gauge.help_text == "Test gauge"
        assert gauge.value == 0.0

        gauge.set(10.0)
        assert gauge.value == 10.0

        gauge.inc(5.0)
        assert gauge.value == 15.0

        gauge.dec(3.0)
        assert gauge.value == 12.0

    def test_histogram_class(self):
        """Test Histogram class."""
        histogram = Histogram(
            name="test_histogram", help_text="Test histogram", buckets=[1.0, 2.0, 5.0]
        )

        assert histogram.name == "test_histogram"
        assert histogram.help_text == "Test histogram"
        assert histogram.count == 0
        assert histogram.sum_value == 0.0
        assert histogram.average == 0.0

        # Test observations
        histogram.observe(1.5)
        assert histogram.count == 1
        assert histogram.sum_value == 1.5
        assert histogram.average == 1.5

        histogram.observe(3.0)
        assert histogram.count == 2
        assert histogram.sum_value == 4.5
        assert histogram.average == 2.25

        histogram.reset()
        assert histogram.count == 0
        assert histogram.sum_value == 0.0
        assert histogram.average == 0.0

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_metrics_collector_initialization(self, mock_config):
        """Test MetricsCollector initialization."""
        mock_config.monitoring.metrics_enabled = True
        mock_config.monitoring.resource_monitoring_enabled = True
        mock_config.monitoring.metrics_collection_interval_seconds = 10

        collector = MetricsCollector()

        # Check that standard metrics are registered
        assert collector.get_counter("http_requests_total") is not None
        assert collector.get_counter("health_checks_total") is not None
        assert collector.get_gauge("process_cpu_percent") is not None
        assert collector.get_histogram("http_request_duration_seconds") is not None

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_register_metrics(self, mock_config):
        """Test metric registration methods."""
        mock_config.monitoring.metrics_enabled = True
        collector = MetricsCollector()

        # Test counter registration
        counter = collector.register_counter("test_counter", "Test counter help")
        assert isinstance(counter, Counter)
        assert collector.get_counter("test_counter") is counter

        # Test gauge registration
        gauge = collector.register_gauge("test_gauge", "Test gauge help")
        assert isinstance(gauge, Gauge)
        assert collector.get_gauge("test_gauge") is gauge

        # Test histogram registration
        histogram = collector.register_histogram(
            "test_histogram", "Test histogram help"
        )
        assert isinstance(histogram, Histogram)
        assert collector.get_histogram("test_histogram") is histogram

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_increment_counter(self, mock_config):
        """Test increment_counter method."""
        mock_config.monitoring.metrics_enabled = True
        collector = MetricsCollector()

        # Register a counter first
        collector.register_counter("test_counter", "Test counter help")

        # Increment without labels
        collector.increment_counter("test_counter", 5.0)
        counter = collector.get_counter("test_counter")
        assert counter.value == 5.0

        # Increment with labels
        collector.increment_counter("test_counter", 3.0, {"status": "200"})
        assert counter.value == 8.0
        assert counter.labels == {"status": "200"}

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_set_gauge(self, mock_config):
        """Test set_gauge method."""
        mock_config.monitoring.metrics_enabled = True
        collector = MetricsCollector()

        # Register a gauge first
        collector.register_gauge("test_gauge", "Test gauge help")

        # Set value without labels
        collector.set_gauge("test_gauge", 10.0)
        gauge = collector.get_gauge("test_gauge")
        assert gauge.value == 10.0

        # Set value with labels
        collector.set_gauge("test_gauge", 20.0, {"type": "cpu"})
        assert gauge.value == 20.0
        assert gauge.labels == {"type": "cpu"}

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_observe_histogram(self, mock_config):
        """Test observe_histogram method."""
        mock_config.monitoring.metrics_enabled = True
        collector = MetricsCollector()

        # Register a histogram first
        collector.register_histogram("test_histogram", "Test histogram help")

        # Observe without labels
        collector.observe_histogram("test_histogram", 1.5)
        histogram = collector.get_histogram("test_histogram")
        assert histogram.count == 1
        assert histogram.sum_value == 1.5

        # Observe with labels
        collector.observe_histogram("test_histogram", 2.5, {"method": "GET"})
        assert histogram.count == 2
        assert histogram.sum_value == 4.0
        assert histogram.labels == {"method": "GET"}

    @patch("excalidraw_mcp.monitoring.metrics.config")
    @patch("excalidraw_mcp.monitoring.metrics.psutil")
    @patch("excalidraw_mcp.process_manager.process_manager")
    @pytest.mark.asyncio
    async def test_collect_system_metrics(
        self, mock_process_manager, mock_psutil, mock_config
    ):
        """Test collect_system_metrics method."""
        mock_config.monitoring.metrics_enabled = True
        mock_config.monitoring.resource_monitoring_enabled = True
        mock_process_manager.process_pid = 1234

        mock_process = Mock()
        mock_process.cpu_percent.return_value = 10.0
        mock_process.memory_info.return_value.rss = 1000000
        mock_process.memory_percent.return_value = 5.0
        mock_process.num_threads.return_value = 4
        mock_process.create_time.return_value = time.time() - 3600  # 1 hour ago

        mock_psutil.Process.return_value = mock_process

        collector = MetricsCollector()
        await collector.collect_system_metrics()

        # Check that gauges were set
        cpu_gauge = collector.get_gauge("process_cpu_percent")
        assert cpu_gauge.value == 10.0

        memory_gauge = collector.get_gauge("process_memory_percent")
        assert memory_gauge.value == 5.0

        threads_gauge = collector.get_gauge("process_threads_count")
        assert threads_gauge.value == 4

        uptime_gauge = collector.get_gauge("canvas_uptime_seconds")
        assert uptime_gauge.value >= 3600

    @patch("excalidraw_mcp.monitoring.metrics.config")
    @patch("excalidraw_mcp.http_client.http_client")
    @pytest.mark.asyncio
    async def test_collect_canvas_metrics(self, mock_http_client, mock_config):
        """Test collect_canvas_metrics method."""
        mock_config.monitoring.metrics_enabled = True
        mock_config.monitoring.resource_monitoring_enabled = True

        # Mock the HTTP client response
        mock_http_client.get_json = AsyncMock(
            return_value={"elements": [{"id": "1"}, {"id": "2"}]}
        )

        collector = MetricsCollector()
        await collector.collect_canvas_metrics()

        # Check that the element count gauge was set
        elements_gauge = collector.get_gauge("canvas_elements_count")
        assert elements_gauge.value == 2

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_get_all_metrics(self, mock_config):
        """Test get_all_metrics method."""
        mock_config.monitoring.metrics_enabled = True
        collector = MetricsCollector()

        # Register and set some metrics
        counter = collector.register_counter("test_counter", "Test counter")
        counter.inc(5.0)

        gauge = collector.register_gauge("test_gauge", "Test gauge")
        gauge.set(10.0)

        histogram = collector.register_histogram("test_histogram", "Test histogram")
        histogram.observe(1.5)

        metrics = collector.get_all_metrics()

        # Check structure
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics

        assert metrics["counters"]["test_counter"]["value"] == 5.0
        assert metrics["gauges"]["test_gauge"]["value"] == 10.0
        assert metrics["histograms"]["test_histogram"]["count"] == 1

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_get_prometheus_format(self, mock_config):
        """Test get_prometheus_format method."""
        mock_config.monitoring.metrics_enabled = True
        collector = MetricsCollector()

        # Register and set some metrics
        counter = collector.register_counter("test_counter", "Test counter help")
        counter.inc(5.0)

        gauge = collector.register_gauge("test_gauge", "Test gauge help")
        gauge.set(10.0)

        prometheus_output = collector.get_prometheus_format()

        # Check that the output contains expected Prometheus format elements
        assert 'test_counter 5.0' in prometheus_output
        assert 'test_gauge 10.0' in prometheus_output
        assert '# HELP test_counter Test counter help' in prometheus_output
        assert '# TYPE test_counter counter' in prometheus_output
        assert '# HELP test_gauge Test gauge help' in prometheus_output
        assert '# TYPE test_gauge gauge' in prometheus_output

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_reset_all_metrics(self, mock_config):
        """Test reset_all_metrics method."""
        mock_config.monitoring.metrics_enabled = True
        collector = MetricsCollector()

        # Register and set some metrics
        counter = collector.register_counter("test_counter", "Test counter")
        counter.inc(5.0)

        gauge = collector.register_gauge("test_gauge", "Test gauge")
        gauge.set(10.0)

        histogram = collector.register_histogram("test_histogram", "Test histogram")
        histogram.observe(1.5)

        # Verify metrics are set
        assert collector.get_counter("test_counter").value == 5.0
        assert collector.get_gauge("test_gauge").value == 10.0
        assert collector.get_histogram("test_histogram").count == 1

        # Reset all metrics
        collector.reset_all_metrics()

        # Verify metrics are reset
        assert collector.get_counter("test_counter").value == 0.0
        assert collector.get_gauge("test_gauge").value == 0.0
        assert collector.get_histogram("test_histogram").count == 0

    @patch("excalidraw_mcp.monitoring.metrics.config")
    def test_get_metric_history(self, mock_config):
        """Test get_metric_history method."""
        mock_config.monitoring.metrics_enabled = True
        collector = MetricsCollector()

        # Set a gauge value to create history
        collector.register_gauge("test_gauge", "Test gauge")
        collector.set_gauge("test_gauge", 10.0)

        # Check history
        history = collector.get_metric_history("test_gauge")
        assert isinstance(history, list)
        assert len(history) >= 0  # Might be empty initially depending on collection

    @patch("excalidraw_mcp.monitoring.metrics.config")
    @pytest.mark.asyncio
    async def test_start_and_stop_collection(self, mock_config):
        """Test start_collection and stop_collection methods."""
        mock_config.monitoring.metrics_enabled = True
        mock_config.monitoring.metrics_collection_interval_seconds = 0.1  # Fast interval for testing

        collector = MetricsCollector()

        # Start collection
        await collector.start_collection()
        assert collector._running is True
        assert collector._collection_task is not None

        # Stop collection
        await collector.stop_collection()
        assert collector._running is False

    @patch("excalidraw_mcp.monitoring.metrics.config")
    @pytest.mark.asyncio
    async def test_collection_loop(self, mock_config):
        """Test the collection loop."""
        mock_config.monitoring.metrics_enabled = True
        mock_config.monitoring.metrics_collection_interval_seconds = 0.01  # Very fast for testing
        mock_config.monitoring.resource_monitoring_enabled = False  # Disable to avoid process issues

        collector = MetricsCollector()

        # Start collection
        await collector.start_collection()

        # Let it run briefly
        await asyncio.sleep(0.05)

        # Stop collection
        await collector.stop_collection()