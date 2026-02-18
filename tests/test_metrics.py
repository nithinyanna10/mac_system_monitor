"""Tests for metrics collection and MacMetrics."""
from __future__ import annotations

import platform
import sys

import pytest

# Allow importing from project root
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from metrics import MacMetrics, collect


def test_mac_metrics_defaults() -> None:
    m = MacMetrics()
    assert m.cpu_percent == 0.0
    assert m.cpu_count == 0
    assert m.memory_percent == 0.0
    assert m.error is None
    assert m.temperatures == {}
    assert m.fan_speeds == {}
    assert m.timestamp == 0.0
    assert m.swap_total_gb == 0.0
    assert m.uptime_sec == 0.0


def test_mac_metrics_to_dict() -> None:
    m = MacMetrics(cpu_percent=50.0, cpu_count=8, thermal_pressure="Nominal")
    d = m.to_dict()
    assert d["cpu_percent"] == 50.0
    assert d["cpu_count"] == 8
    assert d["thermal_pressure"] == "Nominal"
    assert "timestamp" in d
    assert isinstance(d["temperatures"], dict)
    assert isinstance(d["power_estimates"], dict)


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
def test_collect_returns_metrics_on_darwin() -> None:
    m = collect()
    assert isinstance(m, MacMetrics)
    if m.error:
        pytest.skip(f"collect() reported: {m.error}")
    assert m.cpu_count >= 0
    assert 0 <= m.cpu_percent <= 100
    assert m.memory_total_gb >= 0
    assert m.timestamp > 0
