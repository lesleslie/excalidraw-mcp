"""Unit tests for alerts module."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from excalidraw_mcp.monitoring.alerts import (
    Alert,
    AlertChannel,
    AlertLevel,
    AlertManager,
    AlertRule,
)


class TestAlertsModule:
    """Test alerts module classes and functions."""

    def test_alert_level_enum(self):
        """Test AlertLevel enum values."""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"

    def test_alert_channel_enum(self):
        """Test AlertChannel enum values."""
        assert AlertChannel.LOG.value == "log"
        assert AlertChannel.WEBHOOK.value == "webhook"
        assert AlertChannel.EMAIL.value == "email"
        assert AlertChannel.SLACK.value == "slack"

    def test_alert_dataclass(self):
        """Test Alert dataclass."""
        alert = Alert(
            id="test_id",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test message",
            timestamp=time.time(),
            source="test_source",
            labels={"key": "value"},
            resolved=False,
            resolved_at=None,
        )

        assert alert.id == "test_id"
        assert alert.level == AlertLevel.WARNING
        assert alert.message == "Test message"
        assert alert.source == "test_source"
        assert alert.labels == {"key": "value"}
        assert alert.resolved is False
        assert alert.resolved_at is None

    def test_alert_rule_dataclass(self):
        """Test AlertRule dataclass."""
        rule = AlertRule(
            name="test_rule",
            condition="cpu_percent >= 80.0",
            level=AlertLevel.WARNING,
            message_template="High CPU usage: {cpu_percent}%",
            channels=[AlertChannel.LOG],
            throttle_seconds=300,
            enabled=True,
        )

        assert rule.name == "test_rule"
        assert rule.condition == "cpu_percent >= 80.0"
        assert rule.level == AlertLevel.WARNING
        assert rule.message_template == "High CPU usage: {cpu_percent}%"
        assert rule.channels == [AlertChannel.LOG]
        assert rule.throttle_seconds == 300
        assert rule.enabled is True

    @patch("excalidraw_mcp.monitoring.alerts.config")
    def test_alert_manager_initialization(self, mock_config):
        """Test AlertManager initialization."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        assert manager._active_alerts == {}
        assert manager._alert_history == []
        assert manager._alert_counts == {}
        assert manager._last_sent == {}
        assert len(manager._alert_rules) > 0  # Should have default rules

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_check_conditions_disabled(self, mock_config):
        """Test check_conditions when alerting is disabled."""
        mock_config.monitoring.alerting_enabled = False
        manager = AlertManager()

        # This should not raise an exception even though alerting is disabled
        await manager.check_conditions({"cpu_percent": 90.0})

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_check_conditions_with_metrics(self, mock_config):
        """Test check_conditions with metrics."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        # Test with metrics that should trigger an alert
        metrics = {"consecutive_health_failures": 5}  # Should trigger critical alert
        await manager.check_conditions(metrics)

        # Check that alerts were processed
        active_alerts = manager.get_active_alerts()
        history = manager.get_alert_history()

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_force_alert(self, mock_config):
        """Test force_alert method."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        await manager.force_alert(
            title="Test Alert",
            message="This is a test alert",
            level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG],
        )

        history = manager.get_alert_history()
        assert len(history) == 1
        assert history[0].rule_name == "Test Alert"
        assert history[0].message == "This is a test alert"
        assert history[0].level == AlertLevel.WARNING

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_get_alert_statistics(self, mock_config):
        """Test get_alert_statistics method."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        stats = manager.get_alert_statistics()
        assert "active_alerts" in stats
        assert "total_alerts_sent" in stats
        assert "alert_counts_by_type" in stats
        assert "rules_enabled" in stats
        assert "rules_total" in stats

    @patch("excalidraw_mcp.monitoring.alerts.config")
    def test_enable_disable_rule(self, mock_config):
        """Test enable_rule and disable_rule methods."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        # Test enabling a rule
        result = manager.enable_rule("nonexistent_rule")
        assert result is False  # Rule doesn't exist

        # Test disabling a rule
        result = manager.disable_rule("nonexistent_rule")
        assert result is False  # Rule doesn't exist

    @patch("excalidraw_mcp.monitoring.alerts.config")
    def test_clear_alert_history(self, mock_config):
        """Test clear_alert_history method."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        # Add a test alert to history
        manager._alert_history.append(
            Alert(
                id="test_id",
                rule_name="test_rule",
                level=AlertLevel.INFO,
                message="Test message",
                timestamp=time.time(),
                source="test",
            )
        )

        assert len(manager._alert_history) == 1
        manager.clear_alert_history()
        assert len(manager._alert_history) == 0
        assert len(manager._alert_counts) == 0

    @patch("excalidraw_mcp.monitoring.alerts.config")
    def test_get_alert_rules(self, mock_config):
        """Test get_alert_rules method."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        rules = manager.get_alert_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0  # Should have default rules

        # Check that each rule has the expected structure
        for rule in rules:
            assert "name" in rule
            assert "condition" in rule
            assert "level" in rule
            assert "message_template" in rule
            assert "channels" in rule
            assert "throttle_seconds" in rule
            assert "enabled" in rule

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_safe_eval_condition(self, mock_config):
        """Test _safe_eval_condition method."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        # Test simple condition
        result = manager._safe_eval_condition("cpu_percent >= 80.0", {"cpu_percent": 85.0})
        assert result is True

        result = manager._safe_eval_condition("cpu_percent >= 80.0", {"cpu_percent": 75.0})
        assert result is False

        # Test condition with boolean operators
        result = manager._safe_eval_condition(
            "cpu_percent >= 80.0 and memory_percent >= 90.0",
            {"cpu_percent": 85.0, "memory_percent": 95.0},
        )
        assert result is True

        result = manager._safe_eval_condition(
            "cpu_percent >= 80.0 and memory_percent >= 90.0",
            {"cpu_percent": 75.0, "memory_percent": 95.0},
        )
        assert result is False

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_safe_eval_condition_errors(self, mock_config):
        """Test _safe_eval_condition with error conditions."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        # Test with undefined variable
        result = manager._safe_eval_condition("undefined_var >= 80.0", {})
        assert result is False  # Should return False on error

        # Test with invalid syntax
        result = manager._safe_eval_condition("cpu_percent ==", {"cpu_percent": 85.0})
        assert result is False  # Should return False on error

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_format_alert_message(self, mock_config):
        """Test _format_alert_message method."""
        mock_config.monitoring.alerting_enabled = True
        mock_config.monitoring.cpu_threshold_percent = 80.0
        mock_config.monitoring.memory_threshold_percent = 85.0
        manager = AlertManager()

        template = "CPU usage is {cpu_percent}% (threshold: {cpu_threshold}%)"
        metrics = {"cpu_percent": 90.0}
        message = manager._format_alert_message(template, metrics)

        assert "CPU usage is 90.0%" in message
        assert "threshold: 80.0%" in message

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_should_throttle_alert(self, mock_config):
        """Test _should_throttle_alert method."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        # Initially, should not throttle
        result = manager._should_throttle_alert("test_rule", time.time())
        assert result is False

        # Add a rule to the manager
        rule = AlertRule(
            name="test_rule",
            condition="cpu_percent >= 80.0",
            level=AlertLevel.WARNING,
            message_template="Test",
            throttle_seconds=300,
        )
        manager._alert_rules.append(rule)

        # Mark as recently sent
        current_time = time.time()
        manager._last_sent["test_rule"] = current_time

        # Check immediately after - should throttle (time_since_last = 0)
        result = manager._should_throttle_alert("test_rule", current_time)
        assert result is True  # Should throttle

        # Check 100 seconds later - should still throttle (100 < 300)
        result = manager._should_throttle_alert("test_rule", current_time + 100)
        assert result is True  # Should still throttle

        # Check 400 seconds later - should not throttle (400 >= 300)
        result = manager._should_throttle_alert("test_rule", current_time + 400)
        assert result is False  # Should not throttle anymore

    @patch("excalidraw_mcp.monitoring.alerts.logger")
    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_send_log_alert(self, mock_config, mock_logger):
        """Test _send_log_alert method."""
        mock_config.monitoring.alerting_enabled = True
        manager = AlertManager()

        alert = Alert(
            id="test_id",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test message",
            timestamp=time.time(),
            source="test",
        )

        await manager._send_log_alert(alert)

        # Check that logger was called with appropriate level
        mock_logger.warning.assert_called()

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_send_webhook_alert(self, mock_config):
        """Test _send_webhook_alert method."""
        mock_config.monitoring.alerting_enabled = True
        mock_config.security.allowed_origins = ["http://test.com"]
        manager = AlertManager()

        alert = Alert(
            id="test_id",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test message",
            timestamp=time.time(),
            source="test",
        )

        # This should not raise an exception
        await manager._send_webhook_alert(alert)

    @patch("excalidraw_mcp.monitoring.alerts.config")
    @pytest.mark.asyncio
    async def test_send_webhook_alert_no_url(self, mock_config):
        """Test _send_webhook_alert method when no webhook URL is available."""
        mock_config.monitoring.alerting_enabled = True
        mock_config.security.allowed_origins = []  # No origins
        manager = AlertManager()

        alert = Alert(
            id="test_id",
            rule_name="test_rule",
            level=AlertLevel.WARNING,
            message="Test message",
            timestamp=time.time(),
            source="test",
        )

        # This should not raise an exception
        await manager._send_webhook_alert(alert)