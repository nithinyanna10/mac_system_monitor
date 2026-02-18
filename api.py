"""
REST API for Mac System Monitor: metrics and health endpoints.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    FastAPI = None  # type: ignore

from metrics import collect, collect_full

_metrics_cache: tuple[float, dict] | None = None
_CACHE_TTL = 2.0


def _get_metrics(full: bool = False) -> dict:
    global _metrics_cache
    now = time.time()
    if _metrics_cache is not None and (now - _metrics_cache[0]) < _CACHE_TTL:
        return _metrics_cache[1]
    fn = collect_full if full else collect
    m = fn()
    data = m.to_dict()
    _metrics_cache = (now, data)
    return data


@asynccontextmanager
async def lifespan(app):
    yield
    # shutdown
    pass


def create_app() -> "FastAPI":
    if FastAPI is None:
        raise ImportError("Install fastapi and uvicorn: pip install fastapi uvicorn")
    app = FastAPI(
        title="Mac System Monitor API",
        description="Metrics and health endpoints",
        version="1.0.0",
        lifespan=lifespan,
    )
    try:
        from config import API_HOST, API_PORT
        origins = []  # config later
    except ImportError:
        origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "timestamp": time.time()}

    @app.get("/metrics")
    def metrics(full: bool = False) -> dict:
        return _get_metrics(full=full)

    @app.get("/metrics/prometheus")
    def prometheus() -> str:
        """Prometheus-style text export (basic)."""
        data = _get_metrics(full=False)
        lines = [
            "# HELP msm_cpu_percent CPU usage percent",
            "# TYPE msm_cpu_percent gauge",
            f"msm_cpu_percent {data.get('cpu_percent', 0)}",
            "# HELP msm_memory_percent Memory usage percent",
            "# TYPE msm_memory_percent gauge",
            f"msm_memory_percent {data.get('memory_percent', 0)}",
            "# HELP msm_disk_percent Disk usage percent",
            "# TYPE msm_disk_percent gauge",
            f"msm_disk_percent {data.get('disk_percent', 0)}",
        ]
        if data.get("battery_percent") is not None:
            lines.append("# HELP msm_battery_percent Battery percent")
            lines.append("# TYPE msm_battery_percent gauge")
            lines.append(f"msm_battery_percent {data['battery_percent']}")
        return "\n".join(lines) + "\n"

    return app


app = create_app() if FastAPI else None


if __name__ == "__main__":
    import uvicorn
    try:
        from config import API_HOST, API_PORT
    except ImportError:
        API_HOST, API_PORT = "0.0.0.0", 8765
    uvicorn.run("api:app", host=API_HOST, port=API_PORT, reload=False)
