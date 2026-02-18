# Mac System Monitor — Architecture

## Overview

The project is structured for production use: configurable, testable, and extensible. It runs on **macOS only** and aggregates metrics from multiple sources (psutil, powermetrics, optional CLI tools).

## Components

### 1. Config (`config.py`)

- **Defaults:** All tunables (refresh interval, history size, timeouts, alert thresholds, API port) live in a single `DEFAULTS` dict.
- **Config file:** Optional YAML (`config.yaml` or `config.yml`) in cwd or `~/.mac_system_monitor/`. Nested keys (e.g. `dashboard.refresh_default_sec`) override defaults.
- **Environment:** Env vars (e.g. `MSM_REFRESH_SEC`, `MSM_ALERT_CPU`, `MSM_API_PORT`) override file and defaults.
- **Backward compat:** Top-level constants (e.g. `REFRESH_DEFAULT_SEC`, `ALERT_CPU_PERCENT`) are exported for existing code.

### 2. Metrics & Models

- **`metrics.py`:** Core `MacMetrics` dataclass and `collect()`. Gathers CPU, memory, swap, disk, battery, uptime, disk I/O, and (via powermetrics + optional tools) temperatures, fans, power, thermal pressure. `collect_full()` additionally runs collectors for processes, network, disk mounts, load average, system info.
- **`models.py`:** Data classes for richer structures: `ProcessInfo`, `NetworkStats`, `DiskMount`, `BatteryDetail`, `AlertRule`, `AlertEvent`, `SystemInfo`, `LoadAverage`. Each has `to_dict()` for JSON/serialization.

### 3. Collectors (`collectors/`)

Pluggable metric sources, each implementing `BaseCollector`:

- **PsutilCollector:** CPU (including per-CPU), memory, swap, disk usage (root + all mounts), disk I/O counters, uptime, battery, load average, system info.
- **PowermetricsCollector:** Thermal pressure, power (W), temperatures, fan speeds (Apple Silicon / Intel SMC). Uses a short-lived cache to avoid calling powermetrics every second.
- **ExternalToolsCollector:** Optional iStats / osx-cpu-temp for temperature and fan when powermetrics doesn’t provide them.
- **NetworkCollector:** System-wide and per-interface bytes/packets (psutil).
- **ProcessCollector:** Top N processes by CPU/memory (psutil).

Collectors return a `CollectorResult(success, error, data)`. The dashboard and `collect_full()` merge these into `MacMetrics` and its `to_dict()`.

### 4. Dashboard (`dashboard.py`)

Streamlit app with a single refresh loop and multiple tabs:

- **Overview:** High-level metrics (CPU, memory, disk, battery, thermal), swap, disk I/O, uptime, system info expander, JSON download.
- **CPU:** Usage over time, load average, per-CPU bar chart.
- **Memory:** Used/total/swap, time-series, gauge.
- **Disk:** Root usage, all mounts table, disk I/O rate over time.
- **Network:** Bytes sent/recv, per-interface table, optional time-series.
- **Processes:** Sortable/filterable table (from `collect_full()`).
- **Thermal & Power:** Temperatures, fans, power (W), thermal pressure.
- **History:** Multi-series charts (CPU, memory, disk, battery, disk I/O rate).
- **Alerts:** Alert engine evaluation, recent events list.
- **Settings:** Config summary, export JSON, clear history.

Session state holds `history`, `paused`, `last_error`, `last_success`, and optional `alert_engine`. History is capped at `HISTORY_MAX_POINTS`.

### 5. Alerts (`alerts.py`)

- **AlertEngine:** Holds a list of `AlertRule` (metric, operator, value, severity, cooldown). `evaluate(metrics_dict)` runs rules and appends `AlertEvent`s; cooldown prevents spam.
- **Built-in thresholds:** CPU, memory, disk, battery (when unplugged), thermal critical are defined in config; the dashboard can show events from the engine.

### 6. Persistence (`persistence.py`)

- **HistoryPersistence:** Optional append-only buffer with periodic save to JSON. Used for long-term history (e.g. 24h at 1-min resolution) when enabled in config. Dashboard can be extended to load/save from it.

### 7. API (`api.py`)

- **FastAPI** app: `GET /health`, `GET /metrics` (optional `?full=1`), `GET /metrics/prometheus` (basic Prometheus text). Metrics are cached for a short TTL. CORS and host/port come from config.

### 8. CLI (`cli.py`)

- **collect:** One-shot rich output (same as `python metrics.py`), or `--json` / `--pretty`, or `--full` (processes, network, mounts), or `--watch` with `--interval`.
- **dashboard:** Run Streamlit (`streamlit run dashboard.py`).
- **api:** Run uvicorn for the FastAPI app.
- **validate-config:** Print loaded config and a few key values.

### 9. Utils (`utils.py`)

- Logging setup, `format_bytes`, `format_uptime`, `format_percent`, thermal pressure level/ordering, env helpers, `safe_percent`, `clamp`.

### 10. Chart helpers (`chart_helpers.py`)

- Reusable Plotly builders (line, multi-line, subplots, gauge, bar) with a consistent dark theme and color palette. Can be used by the dashboard for future charts.

## Data flow

1. **Collection:** `collect()` runs psutil + powermetrics + external tools and fills `MacMetrics`. `collect_full()` additionally runs PsutilCollector (extra fields), NetworkCollector, ProcessCollector and merges into the same `MacMetrics`.
2. **Dashboard:** Each refresh calls `collect_full()`, appends to `history` (if not paused), evaluates alerts, and renders the active tab from `last_success` and `history`.
3. **API:** On request, metrics are read from a small TTL cache (same `collect()` or `collect_full()`).
4. **Export:** `MacMetrics.to_dict()` is used for JSON download and for alert evaluation.

## Dependencies

- **Required:** psutil, streamlit, plotly, pandas (dashboard), pyyaml (config file).
- **Optional:** rich (CLI), fastapi + uvicorn (API).

## Testing

- **tests/:** pytest for config, metrics, models, utils, alerts, collectors. Collectors are skipped or guarded for non-Darwin / missing psutil where needed.
- Run: `pytest tests/ -v`

## Extending

- **New metric source:** Add a collector in `collectors/`, implement `collect()` returning `CollectorResult`, then call it from `collect_full()` and map its `data` into `MacMetrics` (and `to_dict()` if you add new fields).
- **New dashboard tab:** Add a `_render_*_tab(m)` in `dashboard.py` and a new tab in `main()`.
- **New alert rule type:** Extend `AlertRule` / `AlertEngine.evaluate()` and optionally add UI in the Alerts tab.
- **Persistence:** Enable in config and wire `HistoryPersistence` into the dashboard’s history load/save.
