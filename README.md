# Mac System Monitor

View temperature, fan speed, CPU, memory, disk, battery, and power metrics on your Mac.

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

Shows CPU, memory, disk, battery, and (when available) temperatures and fan speeds in the terminal.

## Live dashboard

```bash
streamlit run dashboard.py
```

Opens a browser with auto-refreshing metrics. Use the sidebar to set refresh interval (1–30 seconds).

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
- `psutil` – CPU, memory, disk, battery
- `rich` – pretty terminal output (metrics.py)
- `streamlit` – web dashboard (dashboard.py)
