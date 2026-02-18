"""Tests for models."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import (
    ProcessInfo,
    NetworkStats,
    DiskMount,
    BatteryDetail,
    AlertRule,
    AlertEvent,
    AlertSeverity,
    SystemInfo,
    LoadAverage,
)


def test_process_info_to_dict() -> None:
    p = ProcessInfo(pid=1, name="init", cpu_percent=0.5, memory_percent=0.1, memory_rss_mb=10.0, status="running")
    d = p.to_dict()
    assert d["pid"] == 1
    assert d["name"] == "init"
    assert d["cpu_percent"] == 0.5
    assert d["memory_rss_mb"] == 10.0


def test_network_stats_to_dict() -> None:
    n = NetworkStats(bytes_sent=1000, bytes_recv=2000, interface_name="en0")
    d = n.to_dict()
    assert d["bytes_sent"] == 1000
    assert d["bytes_recv"] == 2000
    assert d["interface_name"] == "en0"


def test_disk_mount_to_dict() -> None:
    m = DiskMount(mountpoint="/", total_gb=100.0, used_gb=50.0, free_gb=50.0, percent=50.0)
    d = m.to_dict()
    assert d["mountpoint"] == "/"
    assert d["total_gb"] == 100.0
    assert d["percent"] == 50.0


def test_battery_detail_to_dict() -> None:
    b = BatteryDetail(percent=80.0, plugged=True, secs_left=None)
    d = b.to_dict()
    assert d["percent"] == 80.0
    assert d["plugged"] is True


def test_alert_rule_to_dict() -> None:
    r = AlertRule(id="a1", name="High CPU", metric="cpu_percent", operator="gte", value=90.0, severity=AlertSeverity.WARNING)
    d = r.to_dict()
    assert d["id"] == "a1"
    assert d["metric"] == "cpu_percent"
    assert d["severity"] == "warning"


def test_alert_event_to_dict() -> None:
    e = AlertEvent(rule_id="r1", rule_name="R1", metric="cpu", value=95.0, threshold=90.0, severity=AlertSeverity.CRITICAL, message="High", timestamp=0.0)
    d = e.to_dict()
    assert d["rule_id"] == "r1"
    assert d["value"] == 95.0


def test_system_info_to_dict() -> None:
    s = SystemInfo(hostname="mac", logical_cores=8, total_memory_gb=16.0)
    d = s.to_dict()
    assert d["hostname"] == "mac"
    assert d["logical_cores"] == 8


def test_load_average_to_dict() -> None:
    l = LoadAverage(load_1=1.5, load_5=1.2, load_15=1.0)
    d = l.to_dict()
    assert d["load_1"] == 1.5
    assert d["load_5"] == 1.2
