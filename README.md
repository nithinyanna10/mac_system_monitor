# Mac System Monitor

Production-grade system monitor for macOS: live metrics, time-series history, Plotly charts, REST API, and pluggable collectors. View CPU, memory, disk, swap, network, processes, battery, thermal pressure, temperatures, fan speeds, and power (Apple Silicon / Intel) in a dark-themed Streamlit dashboard or via CLI/API.

## Features

- **Dashboard (11 tabs):** Overview, CPU, Memory, Disk, Network, Processes, Thermal & Power, History, Alerts, Settings, About. Pause/resume, configurable refresh (1–60 s), clear history, export JSON.
- **Collectors:** Psutil (CPU, memory, swap, disk mounts, I/O, battery, load, system info), Powermetrics (thermal, power), External tools (iStats, osx-cpu-temp), Network (per-interface), Process (top N).
- **Metrics:** `collect()` for core metrics; `collect_full()` adds processes, network, disk mounts, load average, per-CPU. Serialization via `to_dict()` for history and export.
- **Config:** YAML file (optional), env overrides (`MSM_REFRESH_SEC`, `MSM_ALERT_CPU`, etc.), central defaults. See `config.yaml.example`.
- **Alerts:** Configurable thresholds (CPU, memory, disk, battery, thermal), event log, cooldown. See Alerts tab.
- **API:** FastAPI — `GET /health`, `GET /metrics?full=1`, `GET /metrics/prometheus`. Run with `python cli.py api` or `uvicorn api:app`.
- **CLI:** `python cli.py collect` (rich or `--json`, `--full`, `--watch`), `cli.py dashboard`, `cli.py api`, `cli.py validate-config`.
- **Persistence:** Optional JSON history (config). Chart helpers and architecture docs in `docs/`.
- **Tests:** pytest for config, metrics, models, utils, alerts, collectors (29 tests).

## Setup

```bash
cd mac_system_monitor
python3 -m venv .venv
source .venv/bin/activate   # on macOS/Linux
pip install -r requirements.txt
```

(To use the venv later: `source .venv/bin/activate` from the project folder.)

## Terminal (one-shot)

```bash
python metrics.py
```

Shows CPU, memory, swap, disk, disk I/O, uptime, battery, thermal pressure, and (when available) temperatures, fan speeds, and power in the terminal.

## Live dashboard

```bash
streamlit run dashboard.py
```

Opens a browser with:

- **Overview:** Current metrics, swap, disk I/O, uptime; download JSON.
- **History & Charts:** Plotly time-series (CPU, memory, disk %, battery %; disk I/O rate).
- **Thermal & Power:** Temperatures, fans, power (W), thermal pressure.
- **About:** Short description.

Use the sidebar to set refresh interval (1–60 s), pause updates, refresh now, or clear history.

## Thermal pressure and power (Apple Silicon)

On **Apple Silicon** Macs, `powermetrics` uses the `thermal` and `cpu_power` samplers (not SMC). You must run with **sudo** to see thermal pressure and power:

- **Terminal:** `sudo .venv/bin/python metrics.py`  
  (Use the venv Python so `psutil`/`rich` are available.)
- **Dashboard:** `sudo .venv/bin/streamlit run dashboard.py`

You’ll see **thermal pressure** (Nominal / Moderate / Serious / Critical) and **power** (CPU, GPU, ANE in watts). Apple Silicon does not expose raw CPU temperature or fan RPM via powermetrics.

On **Intel** Macs, temperature and fan speed can come from the SMC sampler when you run with sudo.

## Temperature and fan speed (optional tools)

**Apple Silicon:** `powermetrics` does **not** expose raw CPU temperature or fan RPM. To get them, install one of these; this project will auto-detect and use them if present:

| Tool | Install | Notes |
|------|--------|--------|
| **iStats** | `gem install iStats` | Ruby gem. Run `istats` or `istats extra` once to allow sensor access. Gives CPU temp and fan RPM. |
| **osx-cpu-temp** | `brew install osx-cpu-temp` | Often works on Intel; some Apple Silicon support. Gives CPU temp; `-f` for fan. |

After installing (e.g. `gem install iStats`), run `python metrics.py` or the dashboard as usual—no sudo needed for these tools. The script will merge their readings into the same overview.

**Intel Macs:** With sudo, `powermetrics --samplers smc` can provide temperature and fan; alternatively use iStats or osx-cpu-temp above.

## Requirements

- macOS (Darwin)
- Python 3.9+
- **Core:** `psutil` (CPU, memory, disk, battery, swap, disk I/O, uptime)
- **Terminal:** `rich` (pretty tables)
- **Dashboard:** `streamlit`, `plotly`, `pandas`

## Development

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Optional: set alert thresholds and history size in `config.py`.

## Project layout

```
mac_system_monitor/
├── config.py             # YAML + env config, defaults
├── config.yaml.example   # Example config file
├── metrics.py            # MacMetrics, collect(), collect_full()
├── models.py             # ProcessInfo, NetworkStats, DiskMount, AlertRule, etc.
├── utils.py              # Formatting, logging, env helpers
├── dashboard.py          # Streamlit app (11 tabs)
├── chart_helpers.py      # Reusable Plotly chart builders
├── alerts.py             # Alert engine (rules + events)
├── persistence.py        # Optional history persistence
├── api.py                # FastAPI (metrics, health, Prometheus)
├── cli.py                # CLI: collect, dashboard, api, validate-config
├── requirements.txt
├── requirements-dev.txt
├── .streamlit/config.toml
├── collectors/
│   ├── base.py           # BaseCollector, CollectorResult
│   ├── psutil_collector.py
│   ├── powermetrics_collector.py
│   ├── external_collector.py
│   ├── network_collector.py
│   └── process_collector.py
├── docs/
│   └── ARCHITECTURE.md
└── tests/
    ├── test_config.py
    ├── test_metrics.py
    ├── test_models.py
    ├── test_utils.py
    ├── test_alerts.py
    └── test_collectors.py
```
