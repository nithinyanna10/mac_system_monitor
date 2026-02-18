"""
Data models for Mac System Monitor: process info, network stats, disk mounts,
battery details, alert rules and events.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ProcessInfo:
    """Single process snapshot."""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_rss_mb: float
    status: str
    username: str = ""
    create_time: float = 0.0
    num_threads: int = 0
    exe: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_rss_mb": self.memory_rss_mb,
            "status": self.status,
            "username": self.username,
            "create_time": self.create_time,
            "num_threads": self.num_threads,
            "exe": self.exe,
        }


@dataclass
class NetworkStats:
    """Network I/O counters (system-wide or per-interface)."""
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    errin: int = 0
    errout: int = 0
    dropin: int = 0
    dropout: int = 0
    interface_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "bytes_sent": self.bytes_sent,
            "bytes_recv": self.bytes_recv,
            "packets_sent": self.packets_sent,
            "packets_recv": self.packets_recv,
            "errin": self.errin,
            "errout": self.errout,
            "dropin": self.dropin,
            "dropout": self.dropout,
            "interface_name": self.interface_name,
        }


@dataclass
class DiskMount:
    """Single mount point usage."""
    mountpoint: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float
    device: str = ""
    fstype: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mountpoint": self.mountpoint,
            "total_gb": self.total_gb,
            "used_gb": self.used_gb,
            "free_gb": self.free_gb,
            "percent": self.percent,
            "device": self.device,
            "fstype": self.fstype,
        }


@dataclass
class BatteryDetail:
    """Extended battery info when available."""
    percent: float
    plugged: bool
    secs_left: float | None = None  # None if charging or unknown
    power_plugged: bool | None = None
    # Optional from platform
    cycle_count: int | None = None
    health_percent: float | None = None
    temperature_c: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "percent": self.percent,
            "plugged": self.plugged,
            "secs_left": self.secs_left,
            "power_plugged": self.power_plugged,
            "cycle_count": self.cycle_count,
            "health_percent": self.health_percent,
            "temperature_c": self.temperature_c,
        }


@dataclass
class AlertRule:
    """User-defined alert threshold."""
    id: str
    name: str
    metric: str  # e.g. "cpu_percent", "memory_percent"
    operator: str  # "gt", "lt", "gte", "lte", "eq"
    value: float
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    cooldown_sec: float = 60.0  # Min time between repeated alerts

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "metric": self.metric,
            "operator": self.operator,
            "value": self.value,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "cooldown_sec": self.cooldown_sec,
        }


@dataclass
class AlertEvent:
    """A single fired alert."""
    rule_id: str
    rule_name: str
    metric: str
    value: float
    threshold: float
    severity: AlertSeverity
    message: str
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass
class SystemInfo:
    """Static system information."""
    hostname: str = ""
    platform: str = ""
    platform_release: str = ""
    platform_version: str = ""
    architecture: str = ""
    processor: str = ""
    physical_cores: int = 0
    logical_cores: int = 0
    total_memory_gb: float = 0.0
    python_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "platform": self.platform,
            "platform_release": self.platform_release,
            "platform_version": self.platform_version,
            "architecture": self.architecture,
            "processor": self.processor,
            "physical_cores": self.physical_cores,
            "logical_cores": self.logical_cores,
            "total_memory_gb": self.total_memory_gb,
            "python_version": self.python_version,
        }


@dataclass
class LoadAverage:
    """Load average (1, 5, 15 min) when available."""
    load_1: float = 0.0
    load_5: float = 0.0
    load_15: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"load_1": self.load_1, "load_5": self.load_5, "load_15": self.load_15}
