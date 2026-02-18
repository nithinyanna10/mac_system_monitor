"""
Optional persistence: save/load metric history to JSON for long-term storage.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from utils import get_logger

logger = get_logger(__name__)


class HistoryPersistence:
    """Append-only history buffer with periodic save to JSON."""

    def __init__(
        self,
        path: str | Path,
        max_points: int = 10000,
        save_interval_sec: float = 60.0,
    ) -> None:
        self.path = Path(path).expanduser()
        self.max_points = max_points
        self.save_interval_sec = save_interval_sec
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_save = 0.0

    def append(self, point: dict[str, Any]) -> None:
        with self._lock:
            self._buffer.append(point)
            while len(self._buffer) > self.max_points:
                self._buffer.pop(0)
            if time.time() - self._last_save >= self.save_interval_sec:
                self._save_unsafe()

    def _save_unsafe(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"history": self._buffer}, f, indent=0)
            self._last_save = time.time()
        except Exception as e:
            logger.warning("Failed to save history: %s", e)

    def save(self) -> None:
        with self._lock:
            self._save_unsafe()

    def load(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self.path.exists():
                return []
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                hist = data.get("history", [])
                if isinstance(hist, list):
                    self._buffer = hist[-self.max_points:]
                    return list(self._buffer)
            except Exception as e:
                logger.warning("Failed to load history: %s", e)
            return []

    def get_buffer(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._save_unsafe()
