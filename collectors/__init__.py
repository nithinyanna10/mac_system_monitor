"""
Collectors package: pluggable metric sources.
"""
from __future__ import annotations

from collectors.base import BaseCollector, CollectorResult
from collectors.psutil_collector import PsutilCollector
from collectors.powermetrics_collector import PowermetricsCollector
from collectors.external_collector import ExternalToolsCollector
from collectors.network_collector import NetworkCollector
from collectors.process_collector import ProcessCollector

__all__ = [
    "BaseCollector",
    "CollectorResult",
    "PsutilCollector",
    "PowermetricsCollector",
    "ExternalToolsCollector",
    "NetworkCollector",
    "ProcessCollector",
]
