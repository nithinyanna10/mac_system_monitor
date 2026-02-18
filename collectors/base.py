"""
Base collector interface: all metric collectors implement this.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CollectorResult:
    """Result from a single collector: success flag, optional error, and data dict."""
    success: bool = True
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def merge_into(self, target: dict[str, Any]) -> None:
        """Deep-merge data into target. Lists and dicts are merged; scalars overwrite."""
        for k, v in self.data.items():
            if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                for kk, vv in v.items():
                    target[k][kk] = vv
            else:
                target[k] = v


class BaseCollector(ABC):
    """Abstract base for all metric collectors."""

    name: str = "base"

    @abstractmethod
    def collect(self) -> CollectorResult:
        """Run collection and return result. Should not raise; return CollectorResult(success=False, error="...") on failure."""
        ...

    def collect_safe(self) -> CollectorResult:
        """Wrapper that catches exceptions and returns failed result."""
        try:
            return self.collect()
        except Exception as e:
            return CollectorResult(success=False, error=str(e), data={})
