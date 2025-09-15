"""Alert management system for monitoring notifications."""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..config import config

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels."""

    LOG = "log"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"


@dataclass
class Alert:
    """An alert notification."""

    id: str
    title: str
    message: str
    level: AlertLevel
    timestamp: float
    source: str
    labels: dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: float | None = None


@dataclass
class AlertRule:
    """Configuration for an alert rule."""

    name: str
    condition: str
    level: AlertLevel
    message_template: str
    channels: list[AlertChannel] = field(default_factory=list)
    throttle_seconds: int = 300
    enabled: bool = True


class AlertManager:
    """Manages alert notifications and delivery."""

    def __init__(self) -> None:
        self._active_alerts: dict[str, Alert] = {}
        self._alert_history: list[Alert] = []
        self._alert_counts: dict[str, int] = {}
        self._last_sent: dict[str, float] = {}
        self._lock = asyncio.Lock()

        # Initialize alert rules
        self._alert_rules = self._initialize_alert_rules()

    def _initialize_alert_rules(self) -> list[AlertRule]:
        """Initialize standard alert rules."""
        rules = []

        # Health check failure alerts
        rules.append(
            AlertRule(
                name="health_check_failing",
                condition="consecutive_health_failures >= 3",
                level=AlertLevel.WARNING,
                message_template="Canvas server health checks failing: {consecutive_failures} consecutive failures",
                channels=[AlertChannel.LOG],
                throttle_seconds=300,
            )
        )

        rules.append(
            AlertRule(
                name="health_check_critical",
                condition="consecutive_health_failures >= 5",
                level=AlertLevel.CRITICAL,
                message_template="Canvas server health checks critical: {consecutive_failures} consecutive failures",
                channels=[AlertChannel.LOG],
                throttle_seconds=180,
            )
        )

        # Circuit breaker alerts
        rules.append(
            AlertRule(
                name="circuit_breaker_opened",
                condition="circuit_state == 'open'",
                level=AlertLevel.ERROR,
                message_template="Circuit breaker opened: {failure_rate}% failure rate",
                channels=[AlertChannel.LOG],
                throttle_seconds=600,
            )
        )

        # Resource usage alerts
        rules.append(
            AlertRule(
                name="high_cpu_usage",
                condition="cpu_percent > cpu_threshold",
                level=AlertLevel.WARNING,
                message_template="High CPU usage: {cpu_percent}% (threshold: {cpu_threshold}%)",
                channels=[AlertChannel.LOG],
                throttle_seconds=300,
            )
        )

        rules.append(
            AlertRule(
                name="high_memory_usage",
                condition="memory_percent > memory_threshold",
                level=AlertLevel.WARNING,
                message_template="High memory usage: {memory_percent}% (threshold: {memory_threshold}%)",
                channels=[AlertChannel.LOG],
                throttle_seconds=300,
            )
        )

        # Process failure alerts
        rules.append(
            AlertRule(
                name="canvas_process_died",
                condition="process_status == 'dead'",
                level=AlertLevel.CRITICAL,
                message_template="Canvas server process has died",
                channels=[AlertChannel.LOG],
                throttle_seconds=60,
            )
        )

        return rules

    async def check_conditions(self, metrics: dict[str, Any]) -> None:
        """Check alert conditions against current metrics."""
        if not config.monitoring.alerting_enabled:
            return

        current_time = time.time()

        for rule in self._alert_rules:
            if not rule.enabled:
                continue

            try:
                # Evaluate condition
                if self._evaluate_condition(rule.condition, metrics):
                    await self._trigger_alert(rule, metrics, current_time)
                else:
                    # Check if we should resolve existing alert
                    await self._resolve_alert(rule.name, current_time)

            except Exception as e:
                logger.error(f"Error evaluating alert rule '{rule.name}': {e}")

    def _evaluate_condition(self, condition: str, metrics: dict[str, Any]) -> bool:
        """Evaluate alert condition against metrics."""
        try:
            # Create safe evaluation context
            context = {
                # Health metrics
                "consecutive_health_failures": metrics.get(
                    "consecutive_health_failures", 0
                ),
                "health_response_time": metrics.get("health_response_time", 0),
                # Circuit breaker metrics
                "circuit_state": metrics.get("circuit_state", "closed"),
                "circuit_failure_rate": metrics.get("circuit_failure_rate", 0),
                "circuit_failures": metrics.get("circuit_failures", 0),
                # Resource metrics
                "cpu_percent": metrics.get("cpu_percent", 0),
                "memory_percent": metrics.get("memory_percent", 0),
                "cpu_threshold": config.monitoring.cpu_threshold_percent,
                "memory_threshold": config.monitoring.memory_threshold_percent,
                # Process metrics
                "process_status": metrics.get("process_status", "unknown"),
                "uptime_seconds": metrics.get("uptime_seconds", 0),
                # Request metrics
                "error_rate": metrics.get("error_rate", 0),
                "avg_response_time": metrics.get("avg_response_time", 0),
            }

            # Safe evaluation (only allow basic comparisons and logical operators)
            result = eval(condition, {"__builtins__": {}}, context)
            return bool(result)

        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False

    async def _trigger_alert(
        self, rule: AlertRule, metrics: dict[str, Any], timestamp: float
    ) -> None:
        """Trigger an alert if conditions are met."""
        async with self._lock:
            # Check throttling
            if self._should_throttle_alert(rule.name, timestamp):
                return

            # Generate alert ID
            alert_id = f"{rule.name}_{int(timestamp)}"

            # Format message
            message = self._format_alert_message(rule.message_template, metrics)

            # Create alert
            alert = Alert(
                id=alert_id,
                title=rule.name.replace("_", " ").title(),
                message=message,
                level=rule.level,
                timestamp=timestamp,
                source="canvas_monitoring",
                labels={"rule": rule.name},
            )

            # Store alert
            self._active_alerts[rule.name] = alert
            self._alert_history.append(alert)
            self._alert_counts[rule.name] = self._alert_counts.get(rule.name, 0) + 1
            self._last_sent[rule.name] = timestamp

            # Send alert through configured channels
            await self._send_alert(alert, rule.channels)

            logger.info(f"Alert triggered: {alert.title} - {alert.message}")

    async def _resolve_alert(self, rule_name: str, timestamp: float) -> None:
        """Resolve an active alert."""
        async with self._lock:
            if rule_name in self._active_alerts:
                alert = self._active_alerts[rule_name]
                alert.resolved = True
                alert.resolved_at = timestamp

                # Remove from active alerts
                del self._active_alerts[rule_name]

                logger.info(f"Alert resolved: {alert.title}")

    def _should_throttle_alert(self, rule_name: str, timestamp: float) -> bool:
        """Check if alert should be throttled."""
        if rule_name not in self._last_sent:
            return False

        rule = next((r for r in self._alert_rules if r.name == rule_name), None)
        if not rule:
            return False

        time_since_last = timestamp - self._last_sent[rule_name]
        return time_since_last < rule.throttle_seconds

    def _format_alert_message(self, template: str, metrics: dict[str, Any]) -> str:
        """Format alert message template with metric values."""
        try:
            # Create formatting context
            context = {
                "consecutive_failures": metrics.get("consecutive_health_failures", 0),
                "cpu_percent": metrics.get("cpu_percent", 0),
                "memory_percent": metrics.get("memory_percent", 0),
                "cpu_threshold": config.monitoring.cpu_threshold_percent,
                "memory_threshold": config.monitoring.memory_threshold_percent,
                "failure_rate": metrics.get("circuit_failure_rate", 0),
                "uptime": metrics.get("uptime_seconds", 0),
            }

            return template.format(**context)

        except Exception as e:
            logger.error(f"Error formatting alert message: {e}")
            return template

    async def _send_alert(self, alert: Alert, channels: list[AlertChannel]) -> None:
        """Send alert through specified channels."""
        for channel in channels:
            try:
                if channel == AlertChannel.LOG:
                    await self._send_log_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_alert(alert)
                # Add more channels as needed

            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {e}")

    async def _send_log_alert(self, alert: Alert) -> None:
        """Send alert to log."""
        log_level = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical,
        }.get(alert.level, logger.info)

        log_level(f"ALERT [{alert.level.value.upper()}] {alert.title}: {alert.message}")

    async def _send_webhook_alert(self, alert: Alert) -> None:
        """Send alert via webhook."""
        # This would integrate with external webhook system
        webhook_url = (
            config.security.allowed_origins[0]
            if config.security.allowed_origins
            else None
        )

        if not webhook_url:
            logger.warning("Webhook alert configured but no webhook URL available")
            return

        payload = {
            "alert_id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "level": alert.level.value,
            "timestamp": alert.timestamp,
            "source": alert.source,
            "labels": alert.labels,
        }

        # Would use httpx to send webhook
        logger.info(f"Would send webhook alert to {webhook_url}: {json.dumps(payload)}")

    async def force_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        channels: list[AlertChannel] | None = None,
    ) -> None:
        """Manually trigger an alert."""
        alert = Alert(
            id=f"manual_{int(time.time())}",
            title=title,
            message=message,
            level=level,
            timestamp=time.time(),
            source="manual",
        )

        channels = channels or [AlertChannel.LOG]
        await self._send_alert(alert, channels)

        async with self._lock:
            self._alert_history.append(alert)

    def get_active_alerts(self) -> dict[str, Alert]:
        """Get all currently active alerts."""
        return self._active_alerts.copy()

    def get_alert_history(self, limit: int | None = None) -> list[Alert]:
        """Get alert history."""
        history = self._alert_history.copy()
        if limit:
            history = history[-limit:]
        return history

    def get_alert_statistics(self) -> dict[str, Any]:
        """Get alert statistics."""
        return {
            "active_alerts": len(self._active_alerts),
            "total_alerts_sent": len(self._alert_history),
            "alert_counts_by_type": self._alert_counts.copy(),
            "rules_enabled": sum(1 for rule in self._alert_rules if rule.enabled),
            "rules_total": len(self._alert_rules),
        }

    def enable_rule(self, rule_name: str) -> bool:
        """Enable an alert rule."""
        for rule in self._alert_rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info(f"Alert rule '{rule_name}' enabled")
                return True
        return False

    def disable_rule(self, rule_name: str) -> bool:
        """Disable an alert rule."""
        for rule in self._alert_rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info(f"Alert rule '{rule_name}' disabled")
                return True
        return False

    def clear_alert_history(self) -> None:
        """Clear alert history."""
        self._alert_history.clear()
        self._alert_counts.clear()
        logger.info("Alert history cleared")

    def get_alert_rules(self) -> list[dict[str, Any]]:
        """Get all alert rules configuration."""
        return [
            {
                "name": rule.name,
                "condition": rule.condition,
                "level": rule.level.value,
                "message_template": rule.message_template,
                "channels": [c.value for c in rule.channels],
                "throttle_seconds": rule.throttle_seconds,
                "enabled": rule.enabled,
            }
            for rule in self._alert_rules
        ]
