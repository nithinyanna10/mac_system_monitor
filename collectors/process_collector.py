"""
Process list collector: top N by CPU and memory.
"""
from __future__ import annotations

from typing import Any

try:
    import psutil
except ImportError:
    psutil = None

from collectors.base import BaseCollector, CollectorResult
from models import ProcessInfo


class ProcessCollector(BaseCollector):
    name = "process"

    def __init__(self, top_n: int = 20) -> None:
        self.top_n = max(1, min(200, top_n))

    def collect(self) -> CollectorResult:
        if psutil is None:
            return CollectorResult(success=False, error="psutil not installed", data={})

        procs: list[dict[str, Any]] = []
        try:
            for p in psutil.process_iter(
                attrs=["pid", "name", "memory_percent", "memory_info", "status", "username", "create_time", "num_threads", "exe"]
            ):
                try:
                    pinfo = p.info
                    mem_info = pinfo.get("memory_info") or pinfo.get("memory_full_info")
                    rss = 0.0
                    if mem_info:
                        rss = (getattr(mem_info, "rss", 0) or 0) / (1024 * 1024)
                    cpu = 0.0
                    try:
                        cpu = p.cpu_percent(interval=0)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    proc = ProcessInfo(
                        pid=pinfo.get("pid", 0),
                        name=(pinfo.get("name") or "")[:80],
                        cpu_percent=float(cpu),
                        memory_percent=float(pinfo.get("memory_percent") or 0),
                        memory_rss_mb=rss,
                        status=(pinfo.get("status") or "?"),
                        username=(pinfo.get("username") or ""),
                        create_time=float(pinfo.get("create_time") or 0),
                        num_threads=int(pinfo.get("num_threads") or 0),
                        exe=(pinfo.get("exe") or "")[:200],
                    )
                    procs.append(proc.to_dict())
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                    continue
        except Exception:
            pass

        # Sort by CPU then memory, take top_n
        procs.sort(key=lambda x: (x["cpu_percent"], x["memory_percent"]), reverse=True)
        procs = procs[: self.top_n]
        return CollectorResult(success=True, data={"processes": procs})
