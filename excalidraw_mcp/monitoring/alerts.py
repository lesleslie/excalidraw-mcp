"""Alert management with rule-based triggering and multiple delivery channels."""

import ast
import asyncio
import json
import logging
import operator
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
    """An alert instance."""

    id: str
    rule_name: str
    level: AlertLevel
    message: str
    timestamp: float
    source: str
    labels: dict = field(default_factory=dict)
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
        rules: list[AlertRule] = []

        # Health check failure alerts
        rules.extend(
            (
                AlertRule(
                    name="health_check_failing",
                    condition="consecutive_health_failures >= 3",
                    level=AlertLevel.WARNING,
                    message_template="Canvas server health checks failing: {consecutive_failures} consecutive failures",
                    channels=[AlertChannel.LOG],
                    throttle_seconds=300,
                ),
                AlertRule(
                    name="health_check_critical",
                    condition="consecutive_health_failures >= 5",
                    level=AlertLevel.CRITICAL,
                    message_template="Canvas server health checks critical: {consecutive_failures} consecutive failures",
                    channels=[AlertChannel.LOG],
                    throttle_seconds=180,
                ),
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

        # CPU/Memory alerts
        rules.extend(
            (
                AlertRule(
                    name="high_cpu_usage",
                    condition="cpu_percent >= 80.0",
                    level=AlertLevel.WARNING,
                    message_template="High CPU usage detected: {cpu_percent:.1f}%",
                    channels=[AlertChannel.LOG],
                    throttle_seconds=600,
                ),
                AlertRule(
                    name="high_memory_usage",
                    condition="memory_percent >= 85.0",
                    level=AlertLevel.WARNING,
                    message_template="High memory usage detected: {memory_percent:.1f}%",
                    channels=[AlertChannel.LOG],
                    throttle_seconds=600,
                ),
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
                if self._safe_eval_condition(rule.condition, metrics):
                    await self._trigger_alert(rule, metrics, current_time)
                else:
                    # Check if we should resolve existing alert
                    await self._resolve_alert(rule.name, current_time)

            except Exception as e:
                logger.error(f"Error evaluating alert rule '{rule.name}': {e}")

    def _eval_expression(
        self,
        node: ast.Expression,
        operators: dict,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Evaluate an expression node."""
        return self._eval_node(node.body, operators, context)

    def _eval_compare(
        self, node: ast.Compare, operators: dict, context: dict[str, Any] | None = None
    ) -> bool:
        """Evaluate a comparison node."""
        left = self._eval_node(node.left, operators, context)
        comparisons = []
        for op, comparator in zip(node.ops, node.comparators):
            right = self._eval_node(comparator, operators, context)
            if type(op) in operators:
                comparisons.append(operators[type(op)](left, right))
            else:
                raise ValueError(f"Unsupported operator: {op}")
            left = right
        return all(comparisons)

    def _eval_bool_op(
        self, node: ast.BoolOp, operators: dict, context: dict[str, Any] | None = None
    ) -> Any:
        """Evaluate a boolean operation node."""
        values = [self._eval_node(value, operators, context) for value in node.values]
        if type(node.op) in operators:
            result = values[0]
            for value in values[1:]:
                result = operators[type(node.op)](result, value)
            return result
        else:
            raise ValueError(f"Unsupported boolean operator: {node.op}")

    def _eval_unary_op(
        self, node: ast.UnaryOp, operators: dict, context: dict[str, Any] | None = None
    ) -> Any:
        """Evaluate a unary operation node."""
        if isinstance(node.op, ast.Not) and type(node.op) in operators:
            return operators[type(node.op)](
                self._eval_node(node.operand, operators, context)
            )
        else:
            raise ValueError(f"Unsupported unary operator: {node.op}")

    def _eval_constant(self, node: ast.Constant) -> Any:
        """Evaluate a constant node."""
        return node.value

    def _eval_name(self, node: ast.Name, context: dict[str, Any]) -> Any:
        """Evaluate a name node."""
        if node.id in context:
            return context[node.id]
        else:
            raise ValueError(f"Undefined variable: {node.id}")

    def _eval_node(
        self, node: ast.AST, operators: dict, context: dict[str, Any] | None = None
    ) -> Any:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Expression):
            return self._eval_expression(node, operators, context)
        elif isinstance(node, ast.Compare):
            return self._eval_compare(node, operators, context)
        elif isinstance(node, ast.BoolOp):
            return self._eval_bool_op(node, operators, context)
        elif isinstance(node, ast.UnaryOp):
            return self._eval_unary_op(node, operators, context)
        elif isinstance(node, ast.Constant):
            return self._eval_constant(node)
        elif isinstance(node, ast.Num):  # For Python < 3.8
            return node.n
        elif isinstance(node, ast.Str):  # For Python < 3.8
            return node.s
        elif isinstance(node, ast.Name):
            if context is None:
                raise ValueError("Context required for name evaluation")
            return self._eval_name(node, context)
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")

    def _safe_eval_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Safely evaluate an alert condition using AST parsing.

        Supports basic comparisons and logical operators only.
        """
        try:
            # Parse the condition into an AST
            tree = ast.parse(condition, mode="eval")

            # Define allowed operations
            operators = {
                ast.Eq: operator.eq,
                ast.NotEq: operator.ne,
                ast.Lt: operator.lt,
                ast.LtE: operator.le,
                ast.Gt: operator.gt,
                ast.GtE: operator.ge,
                ast.And: operator.and_,
                ast.Or: operator.or_,
                ast.Not: operator.not_,
            }

            result = self._eval_node(tree, operators, context)
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

            alert = Alert(
                id=alert_id,
                rule_name=rule.name,
                level=rule.level,
                message=message,
                timestamp=timestamp,
                source="excalidraw-mcp",
                labels=metrics,
            )

            # Store alert
            self._active_alerts[rule.name] = alert
            self._alert_history.append(alert)
            self._alert_counts[rule.name] = self._alert_counts.get(rule.name, 0) + 1
            self._last_sent[rule.name] = timestamp

            # Send alert through configured channels
            await self._send_alert(alert, rule.channels)

            logger.info(f"Alert triggered: {alert.rule_name} - {alert.message}")

    async def _resolve_alert(self, rule_name: str, timestamp: float) -> None:
        """Resolve an active alert."""
        async with self._lock:
            if rule_name in self._active_alerts:
                alert = self._active_alerts[rule_name]
                alert.resolved = True
                alert.resolved_at = timestamp

                # Remove from active alerts
                del self._active_alerts[rule_name]

                logger.info(f"Alert resolved: {alert.rule_name}")

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

        log_level(
            f"ALERT [{alert.level.value.upper()}] {alert.rule_name}: {alert.message}"
        )

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
            "title": alert.rule_name,
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
            rule_name=title,
            level=level,
            message=message,
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
