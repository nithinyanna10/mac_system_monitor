"""Tests for config module."""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from config import (
    ALERT_BATTERY_PERCENT,
    ALERT_CPU_PERCENT,
    HISTORY_MAX_POINTS,
    REFRESH_DEFAULT_SEC,
    REFRESH_MAX_SEC,
    REFRESH_MIN_SEC,
)


def test_config_constants() -> None:
    assert REFRESH_MIN_SEC >= 1
    assert REFRESH_MAX_SEC >= REFRESH_MIN_SEC
    assert REFRESH_DEFAULT_SEC >= REFRESH_MIN_SEC
    assert REFRESH_DEFAULT_SEC <= REFRESH_MAX_SEC
    assert HISTORY_MAX_POINTS > 0
    assert ALERT_CPU_PERCENT > 0
    assert ALERT_BATTERY_PERCENT >= 0
