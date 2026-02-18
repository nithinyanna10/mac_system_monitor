"""Tests for alert engine."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alerts import AlertEngine
from models import AlertRule, AlertSeverity


def test_alert_engine_add_rule() -> None:
    engine = AlertEngine()
    rule = AlertRule(id="r1", name="High CPU", metric="cpu_percent", operator="gte", value=90.0, severity=AlertSeverity.WARNING)
    engine.add_rule(rule)
    assert len(engine.get_rules()) == 1
    engine.add_rule(rule)
    assert len(engine.get_rules()) == 1


def test_alert_engine_evaluate_fires() -> None:
    engine = AlertEngine()
    engine.add_rule(AlertRule(id="r1", name="High CPU", metric="cpu_percent", operator="gte", value=90.0, severity=AlertSeverity.CRITICAL))
    events = engine.evaluate({"cpu_percent": 95.0})
    assert len(events) == 1
    assert events[0].rule_id == "r1"
    assert events[0].value == 95.0


def test_alert_engine_evaluate_no_fire() -> None:
    engine = AlertEngine()
    engine.add_rule(AlertRule(id="r1", name="High CPU", metric="cpu_percent", operator="gte", value=90.0))
    events = engine.evaluate({"cpu_percent": 50.0})
    assert len(events) == 0


def test_alert_engine_remove_rule() -> None:
    engine = AlertEngine()
    engine.add_rule(AlertRule(id="r1", name="R1", metric="cpu_percent", operator="gt", value=0))
    assert engine.remove_rule("r1") is True
    assert len(engine.get_rules()) == 0
    assert engine.remove_rule("r1") is False


def test_alert_engine_clear_events() -> None:
    engine = AlertEngine()
    engine.add_rule(AlertRule(id="r1", name="High CPU", metric="cpu_percent", operator="gte", value=0))
    engine.evaluate({"cpu_percent": 1.0})
    assert len(engine.get_events()) == 1
    engine.clear_events()
    assert len(engine.get_events()) == 0
