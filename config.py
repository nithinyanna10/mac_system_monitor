"""
Central configuration for Mac System Monitor.
Supports defaults, optional config file (YAML), and environment overrides.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from utils import env_bool, env_float, env_int, env_str

# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    "dashboard": {
        "refresh_min_sec": 1,
        "refresh_max_sec": 60,
        "refresh_default_sec": 3,
        "history_max_points": 300,
        "theme": "dark",
        "page_title": "Mac System Monitor",
        "sidebar_collapsed": False,
    },
    "metrics": {
        "powermetrics_timeout_sec": 8,
        "external_tools_timeout_sec": 3,
        "powermetrics_cache_ttl_sec": 2,
        "process_top_n": 20,
        "disk_mounts_max": 20,
        "network_per_interface": True,
    },
    "alerts": {
        "cpu_percent": 90.0,
        "memory_percent": 90.0,
        "disk_percent": 95.0,
        "battery_percent": 10.0,
        "thermal_critical": True,
        "enabled": True,
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8765,
        "cors_origins": ["*"],
    },
    "persistence": {
        "enabled": False,
        "path": "~/.mac_system_monitor/history.json",
        "max_points": 10000,
        "save_interval_sec": 60,
    },
    "ui": {
        "thermal_pressure_order": ["Nominal", "Moderate", "Serious", "Heavy", "Critical"],
        "chart_height": 400,
        "process_table_page_size": 25,
    },
}

# -----------------------------------------------------------------------------
# Config file loading (optional YAML)
# -----------------------------------------------------------------------------

_config_overrides: dict[str, Any] = {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config_file(path: str | Path | None = None) -> bool:
    """Load optional YAML config. Returns True if loaded."""
    if path is None:
        for p in (
            Path(os.getcwd()) / "config.yaml",
            Path(os.getcwd()) / "config.yml",
            Path(__file__).parent / "config.yaml",
            Path.home() / ".mac_system_monitor" / "config.yaml",
        ):
            if p.exists():
                path = p
                break
    if path is None:
        return False
    path = Path(path)
    if not path.exists():
        return False
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            global _config_overrides
            _config_overrides = _deep_merge(_config_overrides, data)
            return True
    except Exception:
        pass
    return False


def get(key_path: str, default: Any = None) -> Any:
    """Get config value by dot path, e.g. 'dashboard.refresh_default_sec'."""
    merged = _deep_merge(DEFAULTS, _config_overrides)
    keys = key_path.split(".")
    for k in keys:
        if isinstance(merged, dict) and k in merged:
            merged = merged[k]
        else:
            return default
    return merged


# -----------------------------------------------------------------------------
# Environment overrides (take precedence over file)
# -----------------------------------------------------------------------------

def _env_overrides() -> dict[str, Any]:
    return {
        "dashboard.refresh_default_sec": env_int("MSM_REFRESH_SEC", 0),
        "dashboard.history_max_points": env_int("MSM_HISTORY_MAX", 0),
        "metrics.powermetrics_timeout_sec": env_int("MSM_POWERMETRICS_TIMEOUT", 0),
        "alerts.cpu_percent": env_float("MSM_ALERT_CPU", 0),
        "alerts.memory_percent": env_float("MSM_ALERT_MEMORY", 0),
        "api.port": env_int("MSM_API_PORT", 0),
        "persistence.enabled": env_bool("MSM_PERSISTENCE", False),
    }


def _apply_env() -> None:
    e = _env_overrides()
    for path, value in e.items():
        if value == 0 or value is False:
            continue
        keys = path.split(".")
        d = _config_overrides
        for i, k in enumerate(keys[:-1]):
            if k not in d:
                d[k] = {}
            if not isinstance(d[k], dict):
                break
            d = d[k]
        if isinstance(d, dict) and keys[-1]:
            d[keys[-1]] = value


# Apply env on import
_apply_env()

# -----------------------------------------------------------------------------
# Convenience constants (for backward compat and quick access)
# -----------------------------------------------------------------------------

REFRESH_MIN_SEC = int(get("dashboard.refresh_min_sec", 1))
REFRESH_MAX_SEC = int(get("dashboard.refresh_max_sec", 60))
REFRESH_DEFAULT_SEC = int(get("dashboard.refresh_default_sec", 3))
HISTORY_MAX_POINTS = int(get("dashboard.history_max_points", 300))

POWERMETRICS_TIMEOUT_SEC = int(get("metrics.powermetrics_timeout_sec", 8))
EXTERNAL_TOOLS_TIMEOUT_SEC = int(get("metrics.external_tools_timeout_sec", 3))
POWERMETRICS_CACHE_TTL_SEC = int(get("metrics.powermetrics_cache_ttl_sec", 2))
PROCESS_TOP_N = int(get("metrics.process_top_n", 20))
DISK_MOUNTS_MAX = int(get("metrics.disk_mounts_max", 20))

THERMAL_PRESSURE_ORDER = tuple(get("ui.thermal_pressure_order", ["Nominal", "Moderate", "Serious", "Heavy", "Critical"]))
ALERT_CPU_PERCENT = float(get("alerts.cpu_percent", 90.0))
ALERT_MEMORY_PERCENT = float(get("alerts.memory_percent", 90.0))
ALERT_DISK_PERCENT = float(get("alerts.disk_percent", 95.0))
ALERT_BATTERY_PERCENT = float(get("alerts.battery_percent", 10.0))
ALERT_THERMAL_CRITICAL = bool(get("alerts.thermal_critical", True))
ALERTS_ENABLED = bool(get("alerts.enabled", True))

CHART_HEIGHT = int(get("ui.chart_height", 400))
PROCESS_TABLE_PAGE_SIZE = int(get("ui.process_table_page_size", 25))

API_HOST = str(get("api.host", "0.0.0.0"))
API_PORT = int(get("api.port", 8765))
PERSISTENCE_ENABLED = bool(get("persistence.enabled", False))
PERSISTENCE_PATH = str(get("persistence.path", "~/.mac_system_monitor/history.json"))
PERSISTENCE_MAX_POINTS = int(get("persistence.max_points", 10000))
PERSISTENCE_SAVE_INTERVAL_SEC = int(get("persistence.save_interval_sec", 60))
