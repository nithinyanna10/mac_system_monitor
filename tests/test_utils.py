"""Tests for utils."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import (
    format_bytes,
    format_uptime,
    safe_percent,
    thermal_pressure_level,
    is_thermal_critical,
    clamp,
)


def test_format_bytes() -> None:
    assert "1.0 B" in format_bytes(1) or "1 " in format_bytes(1)
    assert "KB" in format_bytes(1024) or "1.0" in format_bytes(1024)
    assert "GB" in format_bytes(1024**3)
    assert "0 B" in format_bytes(0)
    assert format_bytes(-1) == "0 B"


def test_format_uptime() -> None:
    assert format_uptime(0) == "—"
    assert "m" in format_uptime(60)
    assert "h" in format_uptime(3600)
    assert "d" in format_uptime(86400)


def test_safe_percent() -> None:
    assert safe_percent(50, 100) == 50.0
    assert safe_percent(0, 100) == 0.0
    assert safe_percent(100, 100) == 100.0
    assert safe_percent(50, 0) == 0.0
    assert safe_percent(150, 100) == 100.0


def test_thermal_pressure_level() -> None:
    assert thermal_pressure_level("Nominal") == 0
    assert thermal_pressure_level("Critical") == 4
    assert thermal_pressure_level(None) == -1
    assert thermal_pressure_level("unknown") == -1


def test_is_thermal_critical() -> None:
    assert is_thermal_critical("Heavy") is True
    assert is_thermal_critical("Critical") is True
    assert is_thermal_critical("Nominal") is False
    assert is_thermal_critical("Moderate") is False
    assert is_thermal_critical(None) is False


def test_clamp() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
