"""Tests for collectors."""
from __future__ import annotations

import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.base import BaseCollector, CollectorResult
from collectors.psutil_collector import PsutilCollector
from collectors.network_collector import NetworkCollector
from collectors.process_collector import ProcessCollector
from collectors.powermetrics_collector import PowermetricsCollector
from collectors.external_collector import ExternalToolsCollector


def test_collector_result_merge() -> None:
    r = CollectorResult(success=True, data={"a": 1, "b": {"x": 10}})
    target = {"b": {"y": 20}}
    r.merge_into(target)
    assert target["a"] == 1
    assert target["b"]["x"] == 10
    assert target["b"]["y"] == 20


def test_psutil_collector_on_darwin() -> None:
    if platform.system() != "Darwin":
        return
    c = PsutilCollector(disk_mounts_max=5, include_system_info=True)
    r = c.collect_safe()
    if r.error and "psutil" in r.error:
        return
    assert r.success
    assert "cpu_percent" in r.data
    assert "memory_percent" in r.data
    assert "timestamp" in r.data


def test_network_collector() -> None:
    c = NetworkCollector(per_interface=True)
    r = c.collect_safe()
    if r.error:
        return
    assert r.success
    assert "network" in r.data


def test_process_collector() -> None:
    c = ProcessCollector(top_n=5)
    r = c.collect_safe()
    if r.error:
        return
    assert r.success
    assert "processes" in r.data
    assert isinstance(r.data["processes"], list)


def test_powermetrics_collector() -> None:
    c = PowermetricsCollector()
    r = c.collect_safe()
    assert r.success
    assert "temperatures" in r.data
    assert "thermal_pressure" in r.data


def test_external_collector() -> None:
    c = ExternalToolsCollector(timeout_sec=1)
    r = c.collect_safe()
    assert r.success
    assert "temperatures_extra" in r.data or "fan_speeds_extra" in r.data
