"""
Psutil-based collector: CPU, memory, swap, disk, battery, uptime, load.
"""
from __future__ import annotations

import platform
import time
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

from utils import safe_percent

from collectors.base import BaseCollector, CollectorResult
from models import DiskMount, LoadAverage, SystemInfo


class PsutilCollector(BaseCollector):
    name = "psutil"

    def __init__(
        self,
        disk_mounts_max: int = 20,
        include_system_info: bool = True,
    ) -> None:
        self.disk_mounts_max = disk_mounts_max
        self.include_system_info = include_system_info

    def collect(self) -> CollectorResult:
        if psutil is None:
            return CollectorResult(success=False, error="psutil not installed", data={})
        if platform.system() != "Darwin":
            return CollectorResult(success=False, error="Not macOS", data={})

        data: dict[str, Any] = {}
        data["timestamp"] = time.time()

        # CPU
        data["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        data["cpu_count"] = psutil.cpu_count() or 0
        try:
            per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            data["cpu_per_cpu"] = per_cpu
        except Exception:
            data["cpu_per_cpu"] = []

        # Load average (Unix; on Windows may be empty)
        try:
            load = psutil.getloadavg()
            data["load_average"] = LoadAverage(load[0], load[1], load[2]).to_dict()
        except (AttributeError, OSError):
            data["load_average"] = LoadAverage().to_dict()

        # Memory
        vmem = psutil.virtual_memory()
        data["memory_total_gb"] = vmem.total / (1024**3)
        data["memory_used_gb"] = vmem.used / (1024**3)
        data["memory_percent"] = vmem.percent
        data["memory_available_gb"] = vmem.available / (1024**3)

        # Swap
        try:
            swap = psutil.swap_memory()
            data["swap_total_gb"] = swap.total / (1024**3)
            data["swap_used_gb"] = swap.used / (1024**3)
            data["swap_percent"] = swap.percent
        except Exception:
            data["swap_total_gb"] = 0.0
            data["swap_used_gb"] = 0.0
            data["swap_percent"] = 0.0

        # Disk root (primary)
        try:
            disk = psutil.disk_usage("/")
            data["disk_total_gb"] = disk.total / (1024**3)
            data["disk_used_gb"] = disk.used / (1024**3)
            data["disk_percent"] = disk.percent
        except Exception:
            data["disk_total_gb"] = 0.0
            data["disk_used_gb"] = 0.0
            data["disk_percent"] = 0.0

        # All disk mounts
        try:
            mounts: list[dict[str, Any]] = []
            for part in psutil.disk_partitions(all=False)[: self.disk_mounts_max]:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    m = DiskMount(
                        mountpoint=part.mountpoint,
                        total_gb=usage.total / (1024**3),
                        used_gb=usage.used / (1024**3),
                        free_gb=usage.free / (1024**3),
                        percent=usage.percent,
                        device=part.device,
                        fstype=part.fstype,
                    )
                    mounts.append(m.to_dict())
                except (PermissionError, OSError):
                    continue
            data["disk_mounts"] = mounts
        except Exception:
            data["disk_mounts"] = []

        # Disk I/O
        try:
            io = psutil.disk_io_counters()
            if io:
                data["disk_read_bytes"] = getattr(io, "read_bytes", 0) or 0
                data["disk_write_bytes"] = getattr(io, "write_bytes", 0) or 0
            else:
                data["disk_read_bytes"] = 0
                data["disk_write_bytes"] = 0
        except Exception:
            data["disk_read_bytes"] = 0
            data["disk_write_bytes"] = 0

        # Uptime
        try:
            data["uptime_sec"] = time.time() - psutil.boot_time()
        except Exception:
            data["uptime_sec"] = 0.0

        # Battery
        try:
            bat = psutil.sensors_battery()
            if bat is not None:
                data["battery_percent"] = bat.percent
                data["battery_plugged"] = bat.power_plugged
                data["battery_secs_left"] = getattr(bat, "secsleft", None)
            else:
                data["battery_percent"] = None
                data["battery_plugged"] = None
                data["battery_secs_left"] = None
        except Exception:
            data["battery_percent"] = None
            data["battery_plugged"] = None
            data["battery_secs_left"] = None

        # System info (static, once)
        if self.include_system_info:
            try:
                info = SystemInfo(
                    hostname=platform.node(),
                    platform=platform.system(),
                    platform_release=platform.release(),
                    platform_version=platform.version(),
                    architecture=platform.machine(),
                    processor=platform.processor() or "",
                    physical_cores=psutil.cpu_count(logical=False) or 0,
                    logical_cores=psutil.cpu_count() or 0,
                    total_memory_gb=data.get("memory_total_gb", 0),
                    python_version=platform.python_version(),
                )
                data["system_info"] = info.to_dict()
            except Exception:
                data["system_info"] = {}

        return CollectorResult(success=True, data=data)
