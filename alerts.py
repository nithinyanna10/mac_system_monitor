"""
Alert engine: evaluate rules against current metrics and maintain alert history.
"""
from __future__ import annotations

import time
from typing import Any

from models import AlertEvent, AlertRule, AlertSeverity


def _get_metric_value(metrics: dict[str, Any], key: str) -> float | None:
    """Resolve metric value from metrics dict. Supports nested keys and thermal_pressure as level."""
    if key == "thermal_pressure":
        level = metrics.get("thermal_pressure")
        if level is None or not isinstance(level, str):
            return None
        order = ("Nominal", "Moderate", "Serious", "Heavy", "Critical")
        for i, name in enumerate(order):
            if name.lower() == level.strip().lower():
                return float(i)
        return None
    val = metrics.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _eval_rule(rule: AlertRule, value: float) -> bool:
    if rule.operator == "gt":
        return value > rule.value
    if rule.operator == "gte":
        return value >= rule.value
    if rule.operator == "lt":
        return value < rule.value
    if rule.operator == "lte":
        return value <= rule.value
    if rule.operator == "eq":
        return value == rule.value
    return False


class AlertEngine:
    """Evaluate alert rules and record events."""

    def __init__(self) -> None:
        self.rules: list[AlertRule] = []
        self.events: list[AlertEvent] = []
        self._last_fire: dict[str, float] = {}
        self._max_events = 500

    def add_rule(self, rule: AlertRule) -> None:
        if not any(r.id == rule.id for r in self.rules):
            self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        return len(self.rules) < before

    def evaluate(self, metrics: dict[str, Any]) -> list[AlertEvent]:
        """Evaluate all enabled rules against metrics. Returns new events this round."""
        now = time.time()
        new_events: list[AlertEvent] = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            val = _get_metric_value(metrics, rule.metric)
            if val is None:
                continue
            if not _eval_rule(rule, val):
                continue
            last = self._last_fire.get(rule.id, 0)
            if now - last < rule.cooldown_sec:
                continue
            self._last_fire[rule.id] = now
            msg = f"{rule.metric}={val} (threshold {rule.operator} {rule.value})"
            event = AlertEvent(
                rule_id=rule.id,
                rule_name=rule.name,
                metric=rule.metric,
                value=val,
                threshold=rule.value,
                severity=rule.severity,
                message=msg,
                timestamp=now,
            )
            self.events.append(event)
            new_events.append(event)
            while len(self.events) > self._max_events:
                self.events.pop(0)
        return new_events

    def get_events(self, limit: int = 100) -> list[AlertEvent]:
        return list(reversed(self.events[-limit:]))

    def clear_events(self) -> None:
        self.events.clear()
        self._last_fire.clear()

    def get_rules(self) -> list[AlertRule]:
        return list(self.rules)
