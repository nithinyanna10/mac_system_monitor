"""
Shared utilities: formatting, uptime, bytes, thermal pressure ordering.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str | int = "INFO",
    log_file: str | Path | None = None,
    format_string: str = LOG_FORMAT,
    date_format: str = LOG_DATE_FORMAT,
) -> None:
    """Configure root logger and optional file handler."""
    log_level = getattr(logging, level.upper(), logging.INFO) if isinstance(level, str) else level
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(
        level=log_level,
        format=format_string,
        datefmt=date_format,
        handlers=handlers,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# -----------------------------------------------------------------------------
# Formatting
# -----------------------------------------------------------------------------

def format_bytes(n: int | float) -> str:
    """Human-readable bytes (e.g. 1.5 GB)."""
    if n < 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def format_bytes_per_sec(n: float) -> str:
    """Human-readable throughput (e.g. 12.3 MB/s)."""
    return f"{format_bytes(int(n)).rstrip(' B')}/s"


def format_uptime(seconds: float) -> str:
    """Human-readable uptime (e.g. 2d 5h 30m)."""
    if seconds <= 0:
        return "—"
    s = int(seconds)
    days, s = divmod(s, 86400)
    hours, s = divmod(s, 3600)
    mins, s = divmod(s, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours}h")
    if mins or parts:
        parts.append(f"{mins}m")
    return " ".join(parts) if parts else "0m"


def format_percent(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def format_temperature(celsius: float) -> str:
    return f"{celsius:.1f}°C"


def format_rpm(rpm: int) -> str:
    return f"{rpm} RPM"


def format_watts(w: float) -> str:
    return f"{w:.2f} W"


# -----------------------------------------------------------------------------
# Thermal pressure
# -----------------------------------------------------------------------------

THERMAL_PRESSURE_ORDER = ("Nominal", "Moderate", "Serious", "Heavy", "Critical")


def thermal_pressure_level(level: str | None) -> int:
    """Return numeric level for ordering (higher = worse). -1 if unknown."""
    if not level:
        return -1
    level = level.strip()
    for i, name in enumerate(THERMAL_PRESSURE_ORDER):
        if name.lower() == level.lower():
            return i
    return -1


def is_thermal_critical(level: str | None) -> bool:
    return thermal_pressure_level(level) >= 3  # Heavy or Critical


# -----------------------------------------------------------------------------
# Config / env helpers
# -----------------------------------------------------------------------------

def env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


def env_int(key: str, default: int = 0) -> int:
    try:
        return int(os.environ.get(key, default))
    except ValueError:
        return default


def env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(os.environ.get(key, default))
    except ValueError:
        return default


def env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


# -----------------------------------------------------------------------------
# Safe math
# -----------------------------------------------------------------------------

def safe_percent(used: float, total: float) -> float:
    """Return (used/total)*100, or 0 if total <= 0."""
    if total <= 0:
        return 0.0
    return min(100.0, max(0.0, (used / total) * 100.0))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
