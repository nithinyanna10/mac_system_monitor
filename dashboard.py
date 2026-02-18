"""
Production-grade Streamlit dashboard for Mac system metrics.
Tabs: Overview | CPU | Memory | Disk | Network | Processes | Thermal & Power | History | Alerts | Settings | About.
"""
from __future__ import annotations

import json
import time
from io import StringIO

import streamlit as st

from config import (
    ALERT_BATTERY_PERCENT,
    ALERT_CPU_PERCENT,
    ALERT_DISK_PERCENT,
    ALERT_MEMORY_PERCENT,
    ALERTS_ENABLED,
    CHART_HEIGHT,
    HISTORY_MAX_POINTS,
    PROCESS_TABLE_PAGE_SIZE,
    REFRESH_DEFAULT_SEC,
    REFRESH_MAX_SEC,
    REFRESH_MIN_SEC,
)
from metrics import MacMetrics, collect, collect_full
from utils import format_bytes, format_uptime


def _init_session_state() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "paused" not in st.session_state:
        st.session_state.paused = False
    if "last_error" not in st.session_state:
        st.session_state.last_error = None
    if "last_success" not in st.session_state:
        st.session_state.last_success = None
    if "alert_engine" not in st.session_state:
        try:
            from alerts import AlertEngine
            st.session_state.alert_engine = AlertEngine()
        except ImportError:
            st.session_state.alert_engine = None


def _maybe_append_history(m: MacMetrics) -> None:
    if m.error:
        return
    h = st.session_state.history
    h.append(m.to_dict())
    while len(h) > HISTORY_MAX_POINTS:
        h.pop(0)


def _metric_card(label: str, value: str, delta: str | None, alert: bool) -> None:
    st.metric(label, value, delta)
    if alert:
        st.markdown("<span style='color:#ff6b6b;font-size:0.75rem;'>⚠ High</span>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------

def _render_overview(m: MacMetrics) -> None:
    if m.error:
        st.error(m.error)
        return
    st.subheader("Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        _metric_card("CPU", f"{m.cpu_percent:.1f}%", f"{m.cpu_count} cores", m.cpu_percent >= ALERT_CPU_PERCENT)
    with col2:
        _metric_card("Memory", f"{m.memory_percent:.1f}%", f"{m.memory_used_gb:.1f} / {m.memory_total_gb:.1f} GB", m.memory_percent >= ALERT_MEMORY_PERCENT)
    with col3:
        _metric_card("Disk (/)", f"{m.disk_percent:.1f}%", f"{m.disk_used_gb:.1f} / {m.disk_total_gb:.1f} GB", m.disk_percent >= ALERT_DISK_PERCENT)
    with col4:
        if m.battery_percent is not None:
            plug = "🔌" if m.battery_plugged else "🔋"
            low = not m.battery_plugged and m.battery_percent <= ALERT_BATTERY_PERCENT
            _metric_card("Battery", f"{m.battery_percent:.0f}%", plug, low)
        else:
            st.metric("Battery", "—", "N/A")
    with col5:
        st.metric("Thermal", m.thermal_pressure or "—", "Apple Silicon" if m.thermal_pressure else "")

    st.subheader("System")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Swap", f"{m.swap_percent:.1f}%" if m.swap_total_gb > 0 else "—", f"{m.swap_used_gb:.1f} / {m.swap_total_gb:.1f} GB" if m.swap_total_gb > 0 else "N/A")
    with c2:
        st.metric("Disk I/O (cumulative)", f"R {m.disk_read_bytes / (1024**2):.0f} MB", f"W {m.disk_write_bytes / (1024**2):.0f} MB")
    with c3:
        st.metric("Uptime", format_uptime(m.uptime_sec), "")
    with c4:
        st.metric("Cores", str(m.cpu_count), "")

    if m.system_info:
        with st.expander("System info"):
            st.json(m.system_info)


# -----------------------------------------------------------------------------
# CPU tab
# -----------------------------------------------------------------------------

def _render_cpu_tab(m: MacMetrics) -> None:
    st.subheader("CPU")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Usage", f"{m.cpu_percent:.1f}%", "")
    with col2:
        st.metric("Cores", str(m.cpu_count), "")
    with col3:
        load = m.load_average
        if load:
            st.metric("Load (1/5/15)", f"{load.get('load_1', 0):.2f} / {load.get('load_5', 0):.2f} / {load.get('load_15', 0):.2f}", "")
        else:
            st.metric("Load", "—", "")

    history = st.session_state.history
    if len(history) >= 2:
        import pandas as pd
        import plotly.graph_objects as go
        df = pd.DataFrame(history)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.sort_values("timestamp")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=df["cpu_percent"], name="CPU %", line=dict(color="#00d4aa")))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=CHART_HEIGHT, margin=dict(t=20))
        fig.update_yaxes(title_text="%", range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

    if m.cpu_per_cpu:
        st.markdown("**Per-CPU usage**")
        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Bar(x=[f"CPU {i}" for i in range(len(m.cpu_per_cpu))], y=m.cpu_per_cpu, marker_color="#00d4aa")])
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(t=20))
        fig.update_yaxes(title_text="%", range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)


# -----------------------------------------------------------------------------
# Memory tab
# -----------------------------------------------------------------------------

def _render_memory_tab(m: MacMetrics) -> None:
    import plotly.graph_objects as go
    st.subheader("Memory")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Used", f"{m.memory_used_gb:.2f} GB", f"{m.memory_percent:.1f}%")
    with col2:
        st.metric("Total", f"{m.memory_total_gb:.2f} GB", "")
    with col3:
        st.metric("Swap used", f"{m.swap_used_gb:.2f} GB", f"{m.swap_percent:.1f}%" if m.swap_total_gb > 0 else "—")
    with col4:
        st.metric("Swap total", f"{m.swap_total_gb:.2f} GB", "")

    history = st.session_state.history
    if len(history) >= 2:
        import pandas as pd
        df = pd.DataFrame(history)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=df["memory_percent"], name="Memory %", line=dict(color="#6c5ce7")))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=CHART_HEIGHT, margin=dict(t=20))
        fig.update_yaxes(title_text="%", range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

    # Memory gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=m.memory_percent,
        number={"suffix": "%"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#6c5ce7"}, "steps": [{"range": [0, 60], "color": "rgba(0,0,0,0.2)"}, {"range": [60, 90], "color": "rgba(253, 121, 168, 0.3)"}, {"range": [90, 100], "color": "rgba(255, 107, 107, 0.5)"}]},
        title={"text": "Memory usage"},
    ))
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=280)
    st.plotly_chart(fig, use_container_width=True)


# -----------------------------------------------------------------------------
# Disk tab
# -----------------------------------------------------------------------------

def _render_disk_tab(m: MacMetrics) -> None:
    st.subheader("Disk (root)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Used", f"{m.disk_used_gb:.1f} GB", f"{m.disk_percent:.1f}%")
    with col2:
        st.metric("Total", f"{m.disk_total_gb:.1f} GB", "")
    with col3:
        st.metric("I/O cumulative", f"R {m.disk_read_bytes / (1024**2):.0f} MB", f"W {m.disk_write_bytes / (1024**2):.0f} MB")

    if m.disk_mounts:
        st.subheader("All mounts")
        import pandas as pd
        tbl = pd.DataFrame(m.disk_mounts)
        if not tbl.empty:
            st.dataframe(tbl, use_container_width=True, hide_index=True)

    history = st.session_state.history
    if len(history) >= 2 and "disk_read_bytes" in history[0]:
        import pandas as pd
        import plotly.graph_objects as go
        df = pd.DataFrame(history)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.sort_values("timestamp")
        dt = df["timestamp"].diff().clip(lower=1e-6)
        df = df.copy()
        df["read_mb_s"] = (df["disk_read_bytes"].diff() / (1024**2)) / dt
        df["write_mb_s"] = (df["disk_write_bytes"].diff() / (1024**2)) / dt
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=df["read_mb_s"], name="Read MB/s", line=dict(color="#00d4aa")))
        fig.add_trace(go.Scatter(x=df["time"], y=df["write_mb_s"], name="Write MB/s", line=dict(color="#fd79a8")))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=CHART_HEIGHT)
        st.plotly_chart(fig, use_container_width=True)


# -----------------------------------------------------------------------------
# Network tab
# -----------------------------------------------------------------------------

def _render_network_tab(m: MacMetrics) -> None:
    st.subheader("Network")
    net = m.network
    if not net:
        st.info("No network stats. Ensure collect_full() is used.")
        return
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Bytes sent", format_bytes(net.get("bytes_sent", 0)), "")
    with col2:
        st.metric("Bytes recv", format_bytes(net.get("bytes_recv", 0)), "")
    with col3:
        st.metric("Packets sent", str(net.get("packets_sent", 0)), "")
    with col4:
        st.metric("Packets recv", str(net.get("packets_recv", 0)), "")

    if m.network_per_interface:
        st.subheader("Per interface")
        import pandas as pd
        st.dataframe(pd.DataFrame(m.network_per_interface), use_container_width=True, hide_index=True)

    history = st.session_state.history
    if len(history) >= 2 and "network" in history[0] and history[0]["network"]:
        import pandas as pd
        import plotly.graph_objects as go
        df = pd.DataFrame(history)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        sent = df["network"].apply(lambda x: x.get("bytes_sent", 0) if isinstance(x, dict) else 0)
        recv = df["network"].apply(lambda x: x.get("bytes_recv", 0) if isinstance(x, dict) else 0)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=sent, name="Bytes sent", line=dict(color="#00d4aa")))
        fig.add_trace(go.Scatter(x=df["time"], y=recv, name="Bytes recv", line=dict(color="#6c5ce7")))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=CHART_HEIGHT)
        st.plotly_chart(fig, use_container_width=True)


# -----------------------------------------------------------------------------
# Processes tab
# -----------------------------------------------------------------------------

def _render_processes_tab(m: MacMetrics) -> None:
    st.subheader("Top processes")
    procs = m.processes
    if not procs:
        st.info("No process list. Ensure collect_full() is used.")
        return
    import pandas as pd
    df = pd.DataFrame(procs)
    sort_col = st.selectbox("Sort by", ["cpu_percent", "memory_percent", "memory_rss_mb", "pid"], index=0)
    ascending = sort_col == "pid"
    df = df.sort_values(sort_col, ascending=ascending)
    search = st.text_input("Filter by name", "")
    if search:
        df = df[df["name"].str.contains(search, case=False, na=False)]
    page_size = PROCESS_TABLE_PAGE_SIZE
    total = len(df)
    page = st.number_input("Page", min_value=0, max_value=max(0, (total - 1) // page_size), value=0, step=1)
    start = page * page_size
    end = min(start + page_size, total)
    st.dataframe(df.iloc[start:end], use_container_width=True, hide_index=True)
    st.caption(f"Showing {start+1}-{end} of {total}")


# -----------------------------------------------------------------------------
# Thermal & Power
# -----------------------------------------------------------------------------

def _render_thermal_power(m: MacMetrics) -> None:
    st.subheader("Thermal & Power")
    if m.error:
        st.error(m.error)
        return
    if m.temperatures:
        st.markdown("**Temperatures (°C)**")
        cols = st.columns(min(len(m.temperatures), 4))
        for i, (name, val) in enumerate(sorted(m.temperatures.items())):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), f"{val:.1f}", "°C")
    if m.fan_speeds:
        st.markdown("**Fan speeds (RPM)**")
        cols = st.columns(min(len(m.fan_speeds), 4))
        for i, (name, rpm) in enumerate(sorted(m.fan_speeds.items())):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), str(rpm), "RPM")
    if m.power_estimates:
        st.markdown("**Power (estimated W)**")
        cols = st.columns(min(len(m.power_estimates), 4))
        for i, (name, w) in enumerate(sorted(m.power_estimates.items())):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), f"{w:.2f}", "W")
    if m.thermal_pressure:
        st.markdown("**Thermal pressure** (Apple Silicon)")
        st.info(m.thermal_pressure)
    if not m.smc_available and not m.temperatures and not m.fan_speeds and not m.thermal_pressure:
        st.info("Run with sudo for thermal/power. Optional: iStats or osx-cpu-temp. See README.")


# -----------------------------------------------------------------------------
# History
# -----------------------------------------------------------------------------

def _render_history_charts() -> None:
    st.subheader("History & Charts")
    history = st.session_state.history
    if len(history) < 2:
        st.info("Collecting data… Let the dashboard run for a bit.")
        return
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    df = pd.DataFrame(history)
    df["time"] = pd.to_datetime(df["timestamp"], unit="s")
    df = df.sort_values("timestamp")
    fig = make_subplots(rows=2, cols=2, subplot_titles=("CPU %", "Memory %", "Disk %", "Battery %"), vertical_spacing=0.12, horizontal_spacing=0.08)
    fig.add_trace(go.Scatter(x=df["time"], y=df["cpu_percent"], name="CPU", line=dict(color="#00d4aa")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["memory_percent"], name="Memory", line=dict(color="#6c5ce7")), row=1, col=2)
    fig.add_trace(go.Scatter(x=df["time"], y=df["disk_percent"], name="Disk", line=dict(color="#fd79a8")), row=2, col=1)
    battery = df["battery_percent"].dropna()
    if not battery.empty:
        fig.add_trace(go.Scatter(x=df.loc[battery.index, "time"], y=battery, name="Battery", line=dict(color="#fdcb6e")), row=2, col=2)
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500, margin=dict(t=40), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)
    if "disk_read_bytes" in df.columns and len(df) >= 2:
        df2 = df.copy()
        dt = df2["timestamp"].diff().clip(lower=1e-6)
        df2["disk_read_mb_s"] = (df2["disk_read_bytes"].diff() / (1024**2)) / dt
        df2["disk_write_mb_s"] = (df2["disk_write_bytes"].diff() / (1024**2)) / dt
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df2["time"], y=df2["disk_read_mb_s"], name="Read MB/s", line=dict(color="#00d4aa")))
        fig2.add_trace(go.Scatter(x=df2["time"], y=df2["disk_write_mb_s"], name="Write MB/s", line=dict(color="#fd79a8")))
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280)
        st.plotly_chart(fig2, use_container_width=True)


# -----------------------------------------------------------------------------
# Alerts tab
# -----------------------------------------------------------------------------

def _render_alerts_tab(m: MacMetrics) -> None:
    st.subheader("Alerts")
    engine = st.session_state.alert_engine
    if engine is None:
        st.warning("Alert engine not available.")
        return
    metrics_dict = m.to_dict()
    new_events = engine.evaluate(metrics_dict)
    if new_events:
        for e in new_events:
            st.warning(f"[{e.severity.value}] {e.rule_name}: {e.message}")

    events = engine.get_events(limit=50)
    st.markdown("**Recent events**")
    if events:
        for e in reversed(events):
            st.caption(f"{time.strftime('%H:%M:%S', time.localtime(e.timestamp))} — {e.rule_name}: {e.message}")
    else:
        st.caption("No alert events yet.")

    with st.expander("Add rule (demo)"):
        st.caption("Predefined thresholds are in config. Custom rules can be added here.")
        st.info("CPU ≥ 90%, Memory ≥ 90%, Disk ≥ 95%, Battery ≤ 10% (unplugged), Thermal critical.")


# -----------------------------------------------------------------------------
# Settings tab
# -----------------------------------------------------------------------------

def _render_settings_tab(m: MacMetrics) -> None:
    st.subheader("Settings")
    try:
        from config import get, load_config_file
        loaded = load_config_file()
        st.write("Config file loaded:", loaded)
        st.json({
            "dashboard.refresh_default_sec": get("dashboard.refresh_default_sec"),
            "dashboard.history_max_points": get("dashboard.history_max_points"),
            "alerts.cpu_percent": get("alerts.cpu_percent"),
            "alerts.memory_percent": get("alerts.memory_percent"),
        })
    except Exception as e:
        st.warning(str(e))
    st.divider()
    st.markdown("**Export**")
    buf = StringIO()
    json.dump(m.to_dict(), buf, indent=2)
    st.download_button("Download current metrics (JSON)", buf.getvalue(), file_name="mac_metrics.json", mime="application/json")
    if st.button("Clear all history (this session)"):
        st.session_state.history = []
        st.rerun()


# -----------------------------------------------------------------------------
# About
# -----------------------------------------------------------------------------

def _render_about() -> None:
    st.subheader("About")
    st.markdown("""
    **Mac System Monitor** — Production dashboard for macOS.

    - **Overview:** CPU, memory, disk, battery, swap, disk I/O, uptime, system info.
    - **CPU:** Usage over time, load average, per-CPU.
    - **Memory:** Used/total, swap, gauge, history.
    - **Disk:** Root + all mounts, I/O rate.
    - **Network:** Bytes in/out, per-interface, history.
    - **Processes:** Top N, sort, filter.
    - **Thermal & Power:** Temperatures, fans, power (W), thermal pressure.
    - **History:** Time-series charts.
    - **Alerts:** Threshold events.
    - **Settings:** Config, export, clear history.
    """)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Mac System Monitor", layout="wide", initial_sidebar_state="expanded")
    _init_session_state()

    with st.sidebar:
        st.title("⚙️ Controls")
        refresh = st.slider("Refresh every (seconds)", REFRESH_MIN_SEC, REFRESH_MAX_SEC, REFRESH_DEFAULT_SEC)
        st.session_state.paused = st.checkbox("Pause updates", value=st.session_state.paused)
        if st.button("Refresh now"):
            st.rerun()
        st.divider()
        if st.button("Clear history"):
            st.session_state.history = []
            st.rerun()
        st.caption(f"History: {len(st.session_state.history)} points")

    m = collect_full()
    if m.error:
        st.session_state.last_error = m.error
        m = st.session_state.last_success
    else:
        st.session_state.last_error = None
        st.session_state.last_success = m
        if not st.session_state.paused:
            _maybe_append_history(m)

    if st.session_state.last_error:
        st.error(f"Collection error: {st.session_state.last_error}. Showing last successful snapshot.")

    if m is None:
        st.warning("No metrics yet. Run on macOS with psutil installed.")
        return

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        "Overview", "CPU", "Memory", "Disk", "Network", "Processes", "Thermal & Power", "History", "Alerts", "Settings", "About",
    ])
    with tab1:
        _render_overview(m)
        buf = StringIO()
        json.dump(m.to_dict(), buf, indent=2)
        st.download_button("Download JSON", buf.getvalue(), file_name="mac_metrics.json", mime="application/json")
    with tab2:
        _render_cpu_tab(m)
    with tab3:
        _render_memory_tab(m)
    with tab4:
        _render_disk_tab(m)
    with tab5:
        _render_network_tab(m)
    with tab6:
        _render_processes_tab(m)
    with tab7:
        _render_thermal_power(m)
    with tab8:
        _render_history_charts()
    with tab9:
        _render_alerts_tab(m)
    with tab10:
        _render_settings_tab(m)
    with tab11:
        _render_about()

    if not st.session_state.paused:
        time.sleep(refresh)
        st.rerun()


if __name__ == "__main__":
    main()
