"""
Network I/O collector: system-wide and per-interface stats via psutil.
"""
from __future__ import annotations

from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

from collectors.base import BaseCollector, CollectorResult
from models import NetworkStats


class NetworkCollector(BaseCollector):
    name = "network"

    def __init__(self, per_interface: bool = True) -> None:
        self.per_interface = per_interface

    def collect(self) -> CollectorResult:
        if psutil is None:
            return CollectorResult(success=False, error="psutil not installed", data={})

        data: dict[str, Any] = {}
        try:
            net = psutil.net_io_counters()
            if net:
                data["network"] = NetworkStats(
                    bytes_sent=net.bytes_sent,
                    bytes_recv=net.bytes_recv,
                    packets_sent=net.packets_sent,
                    packets_recv=net.packets_recv,
                    errin=net.errin,
                    errout=net.errout,
                    dropin=net.dropin,
                    dropout=net.dropout,
                ).to_dict()
            else:
                data["network"] = NetworkStats().to_dict()
        except Exception:
            data["network"] = NetworkStats().to_dict()

        if self.per_interface:
            try:
                per_if: list[dict[str, Any]] = []
                for name, counters in psutil.net_if_stats().items():
                    try:
                        io = psutil.net_io_counters(pernic=True).get(name)
                        if io:
                            per_if.append({
                                "interface": name,
                                "bytes_sent": io.bytes_sent,
                                "bytes_recv": io.bytes_recv,
                                "isup": getattr(counters, "isup", True),
                            })
                    except (KeyError, AttributeError):
                        continue
                data["network_per_interface"] = per_if[:50]
            except Exception:
                data["network_per_interface"] = []

        return CollectorResult(success=True, data=data)
