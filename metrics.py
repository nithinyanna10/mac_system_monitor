"""
Gather Mac system metrics: temperature, fan speed, CPU, memory, disk, battery.
Uses psutil for CPU/memory/disk; powermetrics (macOS) for thermal/fan when available.
"""
from __future__ import annotations

import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any

# Optional cache for powermetrics to avoid hammering on fast refresh
_powermetrics_cache: tuple[float, str] | None = None


@dataclass
class MacMetrics:
    """Collected system metrics."""

    cpu_percent: float = 0.0
    cpu_count: int = 0
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_percent: float = 0.0
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_percent: float = 0.0
    temperatures: dict[str, float] = field(default_factory=dict)  # name -> °C
    fan_speeds: dict[str, int] = field(default_factory=dict)     # name -> RPM
    battery_percent: float | None = None
    battery_plugged: bool | None = None
    power_estimates: dict[str, float] = field(default_factory=dict)  # subsystem -> Watts
    thermal_pressure: str | None = None  # Apple Silicon: Nominal, Moderate, Heavy, Critical
    smc_available: bool = False
    error: str | None = None
    # Extended metrics (production)
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0
    swap_percent: float = 0.0
    disk_read_bytes: int = 0
    disk_write_bytes: int = 0
    uptime_sec: float = 0.0
    timestamp: float = 0.0  # time.time() at collection
    # Extended from collectors
    load_average: dict[str, float] = field(default_factory=dict)  # load_1, load_5, load_15
    network: dict[str, Any] = field(default_factory=dict)  # bytes_sent, bytes_recv, etc.
    network_per_interface: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    disk_mounts: list[dict[str, Any]] = field(default_factory=list)
    system_info: dict[str, Any] = field(default_factory=dict)
    cpu_per_cpu: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for history storage and JSON export. Nested dicts are copied."""
        return {
            "cpu_percent": self.cpu_percent,
            "cpu_count": self.cpu_count,
            "memory_total_gb": self.memory_total_gb,
            "memory_used_gb": self.memory_used_gb,
            "memory_percent": self.memory_percent,
            "disk_total_gb": self.disk_total_gb,
            "disk_used_gb": self.disk_used_gb,
            "disk_percent": self.disk_percent,
            "swap_total_gb": self.swap_total_gb,
            "swap_used_gb": self.swap_used_gb,
            "swap_percent": self.swap_percent,
            "disk_read_bytes": self.disk_read_bytes,
            "disk_write_bytes": self.disk_write_bytes,
            "uptime_sec": self.uptime_sec,
            "timestamp": self.timestamp,
            "battery_percent": self.battery_percent,
            "battery_plugged": self.battery_plugged,
            "thermal_pressure": self.thermal_pressure,
            "smc_available": self.smc_available,
            "error": self.error,
            "temperatures": dict(self.temperatures),
            "fan_speeds": dict(self.fan_speeds),
            "power_estimates": dict(self.power_estimates),
            "load_average": dict(self.load_average),
            "network": dict(self.network),
            "network_per_interface": list(self.network_per_interface),
            "processes": list(self.processes),
            "disk_mounts": list(self.disk_mounts),
            "system_info": dict(self.system_info),
            "cpu_per_cpu": list(self.cpu_per_cpu),
        }


def _run_powermetrics(timeout_sec: int | None = None) -> str:
    """Run powermetrics once. Uses short-lived cache to avoid hammering on fast refresh."""
    try:
        from config import POWERMETRICS_CACHE_TTL_SEC, POWERMETRICS_TIMEOUT_SEC
        ttl = POWERMETRICS_CACHE_TTL_SEC
        default_timeout = POWERMETRICS_TIMEOUT_SEC
    except ImportError:
        ttl = 2
        default_timeout = 8
    timeout_sec = timeout_sec if timeout_sec is not None else default_timeout
    now = time.time()
    global _powermetrics_cache
    if _powermetrics_cache is not None and (now - _powermetrics_cache[0]) < ttl:
        return _powermetrics_cache[1]
    raw = _run_powermetrics_impl(timeout_sec)
    if raw:
        _powermetrics_cache = (now, raw)
    return raw


def _run_powermetrics_impl(timeout_sec: int) -> str:
    """Run powermetrics once. Tries Apple Silicon samplers first, then Intel SMC."""
    for samplers in ["thermal,cpu_power,gpu_power,ane_power", "thermal,cpu_power,gpu_power", "smc"]:
        try:
            out = subprocess.run(
                [
                    "powermetrics",
                    "--samplers", samplers,
                    "-i", "1000",
                    "-n", "1",
                ],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            if out.returncode == 0 and (out.stdout or "").strip():
                return out.stdout or ""
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            continue
    return ""


def _parse_powermetrics(
    stdout: str,
) -> tuple[dict[str, float], dict[str, int], dict[str, float], str | None, bool]:
    """Parse powermetrics text. Returns (temps, fans, power_W, thermal_pressure, has_hw_data)."""
    temperatures: dict[str, float] = {}
    fan_speeds: dict[str, int] = {}
    power_estimates: dict[str, float] = {}
    thermal_pressure: str | None = None
    has_hw = False

    # ----- Apple Silicon: thermal pressure ("Current pressure level: Nominal") -----
    m_pressure = re.search(
        r"(?:current\s+)?pressure\s+level\s*:\s*(\w+)|thermal\s+pressure[^\n]*?:\s*(\w+)",
        stdout,
        re.I,
    )
    if m_pressure:
        level = (m_pressure.group(1) or m_pressure.group(2) or "").strip()
        if level in ("Nominal", "Moderate", "Heavy", "Critical", "Serious"):
            thermal_pressure = level
            has_hw = True

    # ----- Apple Silicon: power in mW ("CPU Power: 291 mW") -----
    for m in re.finditer(r"(\w+)\s+Power\s*:\s*([\d.]+)\s*m?W", stdout, re.I):
        name = m.group(1).strip()
        try:
            mw = float(m.group(2))
            power_estimates[name] = mw / 1000.0  # store in Watts
            has_hw = True
        except ValueError:
            pass
    # "Combined Power (CPU + GPU + ANE): 292 mW"
    m_combined = re.search(r"Combined\s+Power[^\n]*?:\s*([\d.]+)\s*m?W", stdout, re.I)
    if m_combined:
        try:
            power_estimates["Combined"] = float(m_combined.group(1)) / 1000.0
            has_hw = True
        except ValueError:
            pass

    # ----- Apple Silicon: power in W ("X power: 2.34 W") -----
    for m in re.finditer(r"([\w\s]+)\s+power\s*:\s*([\d.]+)\s*W(?!\w)", stdout, re.I):
        name = m.group(1).strip().replace(" ", "_")
        if name in ("Combined", "Total"):
            continue
        try:
            power_estimates[name] = float(m.group(2))
            has_hw = True
        except ValueError:
            pass

    # ----- Intel SMC: temperatures -----
    for m in re.finditer(r"([\w\s]+(?:die|package|thermal)\s*temperature)\s*:\s*([\d.]+)\s*C", stdout, re.I):
        name = m.group(1).strip().replace(" ", "_")
        try:
            temperatures[name] = float(m.group(2))
            has_hw = True
        except ValueError:
            pass
    for m in re.finditer(r"(?:Temperature|temp)[^\n]*?:\s*([\d.]+)\s*C", stdout, re.I):
        key = f"temp_{len(temperatures)}"
        try:
            temperatures[key] = float(m.group(1))
            has_hw = True
        except ValueError:
            pass

    # ----- Intel SMC: fan speeds -----
    for m in re.finditer(r"Fan\s*(\d*)\s*speed\s*:\s*(\d+)\s*rpm", stdout, re.I):
        label = m.group(1) or "0"
        name = f"fan_{label}" if label.isdigit() else "fan_0"
        try:
            fan_speeds[name] = int(m.group(2))
            has_hw = True
        except ValueError:
            pass

    return temperatures, fan_speeds, power_estimates, thermal_pressure, has_hw


def _run_external_temp_fan_tools(
    timeout_sec: int | None = None,
) -> tuple[dict[str, float], dict[str, int]]:
    """
    Try optional CLI tools that report temperature and/or fan speed.
    Returns (temperatures, fan_speeds) to merge into main metrics.
    - istats (Ruby gem): gem install iStats  →  istats / istats extra
    - osx-cpu-temp (Intel, Homebrew): brew install osx-cpu-temp  →  °C and -f for fan
    """
    try:
        from config import EXTERNAL_TOOLS_TIMEOUT_SEC
        timeout_sec = timeout_sec if timeout_sec is not None else EXTERNAL_TOOLS_TIMEOUT_SEC
    except ImportError:
        timeout_sec = timeout_sec if timeout_sec is not None else 3
    temps: dict[str, float] = {}
    fans: dict[str, int] = {}

    # ----- iStats (Ruby gem: gem install iStats) -----
    for cmd in (["istats", "extra"], ["istats"]):
        try:
            out = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            if out.returncode != 0:
                continue
            text = (out.stdout or "") + (out.stderr or "")
            # e.g. "CPU temp: 45.2°C" or "CPU Temperature: 52 °C"
            for m in re.finditer(r"(?:CPU\s+)?(?:temp(?:erature)?|Temp)\s*[:\s]+([\d.]+)\s*[°º]?\s*C", text, re.I):
                try:
                    temps["CPU"] = float(m.group(1))
                    break
                except ValueError:
                    pass
            # e.g. "Fan 1: 2345 rpm" or "Fan speed: 1200 RPM"
            for m in re.finditer(r"Fan\s*(\d*)\s*(?::|speed\s*[:\s]+)\s*([\d.]+)\s*rpm", text, re.I):
                try:
                    label = (m.group(1) or "0").strip()
                    name = f"fan_{label}" if label.isdigit() else "fan_0"
                    fans[name] = int(float(m.group(2)))
                except (ValueError, IndexError):
                    pass
            # Other sensors: "GPU temp: 50°C", "Battery: 32°C"
            for m in re.finditer(r"(GPU|Battery|Ambient|Enclosure|PCH|SSD)\s*(?:_)?(?:temp(?:erature)?)?\s*[:\s]+\s*([\d.]+)\s*[°º]?\s*C", text, re.I):
                try:
                    temps[m.group(1).strip()] = float(m.group(2))
                except (ValueError, IndexError):
                    pass
            if temps or fans:
                return temps, fans
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    # ----- osx-cpu-temp (Homebrew, often Intel) -----
    try:
        out = subprocess.run(
            ["osx-cpu-temp"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if out.returncode == 0 and out.stdout:
            m = re.search(r"([\d.]+)\s*[°º]?\s*C", out.stdout)
            if m:
                temps["CPU"] = float(m.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    try:
        out = subprocess.run(
            ["osx-cpu-temp", "-f"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if out.returncode == 0 and out.stdout:
            m = re.search(r"(\d+)\s*rpm", out.stdout, re.I)
            if m:
                fans["fan_0"] = int(m.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return temps, fans


def collect() -> MacMetrics:
    """Collect current system metrics. Safe to call from any thread."""
    m = MacMetrics()
    m.timestamp = time.time()

    if platform.system() != "Darwin":
        m.error = "This tool is for macOS only."
        return m

    try:
        import psutil
    except ImportError:
        m.error = "Install psutil: pip install psutil"
        return m

    # CPU
    m.cpu_percent = psutil.cpu_percent(interval=0.1)
    m.cpu_count = psutil.cpu_count() or 0

    # Memory
    vmem = psutil.virtual_memory()
    m.memory_total_gb = vmem.total / (1024**3)
    m.memory_used_gb = vmem.used / (1024**3)
    m.memory_percent = vmem.percent

    # Swap
    try:
        swap = psutil.swap_memory()
        m.swap_total_gb = swap.total / (1024**3)
        m.swap_used_gb = swap.used / (1024**3)
        m.swap_percent = swap.percent
    except Exception:
        pass

    # Disk (root)
    try:
        disk = psutil.disk_usage("/")
        m.disk_total_gb = disk.total / (1024**3)
        m.disk_used_gb = disk.used / (1024**3)
        m.disk_percent = disk.percent
    except Exception:
        pass

    # Disk I/O (cumulative bytes; dashboard can compute rate from history)
    try:
        io = psutil.disk_io_counters()
        if io is not None:
            m.disk_read_bytes = getattr(io, "read_bytes", 0) or 0
            m.disk_write_bytes = getattr(io, "write_bytes", 0) or 0
    except Exception:
        pass

    # Uptime
    try:
        m.uptime_sec = time.time() - psutil.boot_time()
    except Exception:
        pass

    # Battery
    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            m.battery_percent = bat.percent
            m.battery_plugged = bat.power_plugged
    except Exception:
        pass

    # Thermal / fan / power via powermetrics (requires sudo on Apple Silicon / Intel SMC)
    raw = _run_powermetrics()
    temps, fans, power, thermal_pressure, has_hw = _parse_powermetrics(raw)
    m.temperatures = temps
    m.fan_speeds = fans
    m.power_estimates = power
    m.thermal_pressure = thermal_pressure
    m.smc_available = has_hw

    # Optional: merge in temperature/fan from external tools if installed
    extra_temps, extra_fans = _run_external_temp_fan_tools()
    for k, v in extra_temps.items():
        if k not in m.temperatures:
            m.temperatures[k] = v
    for k, v in extra_fans.items():
        if k not in m.fan_speeds:
            m.fan_speeds[k] = v
    if extra_temps or extra_fans:
        m.smc_available = True

    return m


def collect_full() -> MacMetrics:
    """Collect using all collectors; returns MacMetrics with processes, network, disk_mounts, etc."""
    m = collect()
    try:
        from config import DISK_MOUNTS_MAX, PROCESS_TOP_N
    except ImportError:
        DISK_MOUNTS_MAX = 20
        PROCESS_TOP_N = 20
    try:
        from collectors.psutil_collector import PsutilCollector
        from collectors.powermetrics_collector import PowermetricsCollector
        from collectors.external_collector import ExternalToolsCollector
        from collectors.network_collector import NetworkCollector
        from collectors.process_collector import ProcessCollector
    except ImportError:
        return m
    if m.error:
        return m
    pc = PsutilCollector(disk_mounts_max=DISK_MOUNTS_MAX)
    res = pc.collect_safe()
    if res.success and res.data:
        m.load_average = res.data.get("load_average") or {}
        m.disk_mounts = res.data.get("disk_mounts") or []
        m.system_info = res.data.get("system_info") or {}
        m.cpu_per_cpu = res.data.get("cpu_per_cpu") or []
    nc = NetworkCollector(per_interface=True)
    res = nc.collect_safe()
    if res.success and res.data:
        m.network = res.data.get("network") or {}
        m.network_per_interface = res.data.get("network_per_interface") or []
    proc = ProcessCollector(top_n=PROCESS_TOP_N)
    res = proc.collect_safe()
    if res.success and res.data:
        m.processes = res.data.get("processes") or []
    return m


def main() -> None:
    """Print current metrics once using rich."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
    except ImportError:
        # Fallback without rich
        m = collect()
        print("CPU %:", m.cpu_percent)
        print("Memory %:", m.memory_percent)
        print("Temperatures:", m.temperatures)
        print("Fans:", m.fan_speeds)
        return

    m = collect()
    if m.error:
        print(m.error, file=sys.stderr)
        sys.exit(1)

    console = Console()

    # Overview table
    table = Table(title="Mac System Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("CPU usage", f"{m.cpu_percent:.1f}% ({m.cpu_count} cores)")
    table.add_row("Memory", f"{m.memory_used_gb:.2f} / {m.memory_total_gb:.2f} GB ({m.memory_percent:.1f}%)")
    if m.swap_total_gb > 0:
        table.add_row("Swap", f"{m.swap_used_gb:.2f} / {m.swap_total_gb:.2f} GB ({m.swap_percent:.1f}%)")
    table.add_row("Disk (/)", f"{m.disk_used_gb:.2f} / {m.disk_total_gb:.2f} GB ({m.disk_percent:.1f}%)")
    if m.disk_read_bytes or m.disk_write_bytes:
        table.add_row("Disk I/O", f"Read {m.disk_read_bytes / (1024**2):.1f} MB / Write {m.disk_write_bytes / (1024**2):.1f} MB (cumulative)")
    if m.uptime_sec > 0:
        days, rest = divmod(int(m.uptime_sec), 86400)
        hours, rest = divmod(rest, 3600)
        mins, _ = divmod(rest, 60)
        table.add_row("Uptime", f"{days}d {hours}h {mins}m" if days else f"{hours}h {mins}m")
    if m.battery_percent is not None:
        plug = "plugged in" if m.battery_plugged else "on battery"
        table.add_row("Battery", f"{m.battery_percent:.0f}% ({plug})")
    if m.thermal_pressure:
        table.add_row("Thermal pressure", m.thermal_pressure)
    console.print(Panel(table, title="Overview"))

    if m.temperatures:
        t_table = Table(title="Temperatures")
        t_table.add_column("Sensor", style="cyan")
        t_table.add_column("°C", style="yellow")
        for name, val in sorted(m.temperatures.items()):
            t_table.add_row(name, f"{val:.1f}")
        console.print(Panel(t_table))

    if m.fan_speeds:
        f_table = Table(title="Fan speeds")
        f_table.add_column("Fan", style="cyan")
        f_table.add_column("RPM", style="yellow")
        for name, rpm in sorted(m.fan_speeds.items()):
            f_table.add_row(name, str(rpm))
        console.print(Panel(f_table))

    if m.power_estimates:
        p_table = Table(title="Power (estimated)")
        p_table.add_column("Subsystem", style="cyan")
        p_table.add_column("W", style="yellow")
        for name, w in sorted(m.power_estimates.items()):
            p_table.add_row(name, f"{w:.2f}")
        console.print(Panel(p_table))

    if not m.smc_available and not m.temperatures and not m.fan_speeds and not m.thermal_pressure:
        console.print(
            "[dim]Thermal pressure + power: sudo .venv/bin/python metrics.py[/dim]"
        )
        console.print(
            "[dim]Temperature + fan (optional): install iStats (gem install iStats) or "
            "osx-cpu-temp (brew install osx-cpu-temp). See README.[/dim]"
        )


if __name__ == "__main__":
    main()
