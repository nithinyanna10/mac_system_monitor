"""
External CLI tools collector: iStats, osx-cpu-temp for temperature and fan.
"""
from __future__ import annotations

import re
import subprocess
from typing import Any

from collectors.base import BaseCollector, CollectorResult


class ExternalToolsCollector(BaseCollector):
    name = "external_tools"

    def __init__(self, timeout_sec: int = 3) -> None:
        self.timeout_sec = timeout_sec

    def collect(self) -> CollectorResult:
        temps: dict[str, float] = {}
        fans: dict[str, int] = {}

        for cmd in (["istats", "extra"], ["istats"]):
            try:
                out = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec,
                )
                if out.returncode != 0:
                    continue
                text = (out.stdout or "") + (out.stderr or "")
                for m in re.finditer(
                    r"(?:CPU\s+)?(?:temp(?:erature)?|Temp)\s*[:\s]+([\d.]+)\s*[°º]?\s*C", text, re.I
                ):
                    try:
                        temps["CPU"] = float(m.group(1))
                        break
                    except ValueError:
                        pass
                for m in re.finditer(
                    r"Fan\s*(\d*)\s*(?::|speed\s*[:\s]+)\s*([\d.]+)\s*rpm", text, re.I
                ):
                    try:
                        label = (m.group(1) or "0").strip()
                        name = f"fan_{label}" if label.isdigit() else "fan_0"
                        fans[name] = int(float(m.group(2)))
                    except (ValueError, IndexError):
                        pass
                for m in re.finditer(
                    r"(GPU|Battery|Ambient|Enclosure|PCH|SSD)\s*(?:_)?(?:temp(?:erature)?)?\s*[:\s]+\s*([\d.]+)\s*[°º]?\s*C",
                    text, re.I,
                ):
                    try:
                        temps[m.group(1).strip()] = float(m.group(2))
                    except (ValueError, IndexError):
                        pass
                if temps or fans:
                    return CollectorResult(success=True, data={
                        "temperatures_extra": temps,
                        "fan_speeds_extra": fans,
                    })
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        try:
            out = subprocess.run(
                ["osx-cpu-temp"],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
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
                timeout=self.timeout_sec,
            )
            if out.returncode == 0 and out.stdout:
                m = re.search(r"(\d+)\s*rpm", out.stdout, re.I)
                if m:
                    fans["fan_0"] = int(m.group(1))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return CollectorResult(success=True, data={
            "temperatures_extra": temps,
            "fan_speeds_extra": fans,
        })
