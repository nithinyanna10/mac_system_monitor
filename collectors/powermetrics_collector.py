"""
Powermetrics collector: thermal pressure, power (Apple Silicon), temps & fans (Intel SMC).
"""
from __future__ import annotations

import re
import subprocess
import time
from typing import Any

from collectors.base import BaseCollector, CollectorResult


_powermetrics_cache: tuple[float, str] | None = None
_CACHE_TTL = 2
_TIMEOUT = 8


def _run_powermetrics(timeout_sec: int = _TIMEOUT, cache_ttl: float = _CACHE_TTL) -> str:
    global _powermetrics_cache
    now = time.time()
    if _powermetrics_cache is not None and (now - _powermetrics_cache[0]) < cache_ttl:
        return _powermetrics_cache[1]
    raw = _run_powermetrics_impl(timeout_sec)
    if raw:
        _powermetrics_cache = (now, raw)
    return raw


def _run_powermetrics_impl(timeout_sec: int) -> str:
    for samplers in [
        "thermal,cpu_power,gpu_power,ane_power",
        "thermal,cpu_power,gpu_power",
        "smc",
    ]:
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
) -> tuple[dict[str, float], dict[str, int], dict[str, float], str | None]:
    temperatures: dict[str, float] = {}
    fan_speeds: dict[str, int] = {}
    power_estimates: dict[str, float] = {}
    thermal_pressure: str | None = None

    m_pressure = re.search(
        r"(?:current\s+)?pressure\s+level\s*:\s*(\w+)|thermal\s+pressure[^\n]*?:\s*(\w+)",
        stdout, re.I,
    )
    if m_pressure:
        level = (m_pressure.group(1) or m_pressure.group(2) or "").strip()
        if level in ("Nominal", "Moderate", "Heavy", "Critical", "Serious"):
            thermal_pressure = level

    for m in re.finditer(r"(\w+)\s+Power\s*:\s*([\d.]+)\s*m?W", stdout, re.I):
        try:
            power_estimates[m.group(1).strip()] = float(m.group(2)) / 1000.0
        except ValueError:
            pass
    m_combined = re.search(r"Combined\s+Power[^\n]*?:\s*([\d.]+)\s*m?W", stdout, re.I)
    if m_combined:
        try:
            power_estimates["Combined"] = float(m_combined.group(1)) / 1000.0
        except ValueError:
            pass

    for m in re.finditer(r"([\w\s]+)\s+power\s*:\s*([\d.]+)\s*W(?!\w)", stdout, re.I):
        name = m.group(1).strip().replace(" ", "_")
        if name not in ("Combined", "Total"):
            try:
                power_estimates[name] = float(m.group(2))
            except ValueError:
                pass

    for m in re.finditer(r"([\w\s]+(?:die|package|thermal)\s*temperature)\s*:\s*([\d.]+)\s*C", stdout, re.I):
        name = m.group(1).strip().replace(" ", "_")
        try:
            temperatures[name] = float(m.group(2))
        except ValueError:
            pass
    for m in re.finditer(r"(?:Temperature|temp)[^\n]*?:\s*([\d.]+)\s*C", stdout, re.I):
        try:
            temperatures[f"temp_{len(temperatures)}"] = float(m.group(1))
        except ValueError:
            pass

    for m in re.finditer(r"Fan\s*(\d*)\s*speed\s*:\s*(\d+)\s*rpm", stdout, re.I):
        label = m.group(1) or "0"
        name = f"fan_{label}" if label.isdigit() else "fan_0"
        try:
            fan_speeds[name] = int(m.group(2))
        except ValueError:
            pass

    return temperatures, fan_speeds, power_estimates, thermal_pressure


class PowermetricsCollector(BaseCollector):
    name = "powermetrics"

    def __init__(self, timeout_sec: int = _TIMEOUT, cache_ttl: float = _CACHE_TTL) -> None:
        self.timeout_sec = timeout_sec
        self.cache_ttl = cache_ttl

    def collect(self) -> CollectorResult:
        raw = _run_powermetrics(timeout_sec=self.timeout_sec, cache_ttl=self.cache_ttl)
        if not raw:
            return CollectorResult(success=True, data={
                "temperatures": {},
                "fan_speeds": {},
                "power_estimates": {},
                "thermal_pressure": None,
                "smc_available": False,
            })
        temps, fans, power, pressure = _parse_powermetrics(raw)
        return CollectorResult(success=True, data={
            "temperatures": temps,
            "fan_speeds": fans,
            "power_estimates": power,
            "thermal_pressure": pressure,
            "smc_available": bool(temps or fans or power or pressure),
        })
