"""
Streamlit dashboard for Mac system metrics: temperature, fan speed, CPU, memory, etc.
"""
from __future__ import annotations

import time

import streamlit as st

from metrics import MacMetrics, collect


def render_metrics(m: MacMetrics) -> None:
    if m.error:
        st.error(m.error)
        return

    st.subheader("Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("CPU", f"{m.cpu_percent:.1f}%", f"{m.cpu_count} cores")
    with col2:
        st.metric("Memory", f"{m.memory_percent:.1f}%", f"{m.memory_used_gb:.1f} / {m.memory_total_gb:.1f} GB")
    with col3:
        st.metric("Disk (/)", f"{m.disk_percent:.1f}%", f"{m.disk_used_gb:.1f} / {m.disk_total_gb:.1f} GB")
    with col4:
        if m.battery_percent is not None:
            plug = "🔌" if m.battery_plugged else "🔋"
            st.metric("Battery", f"{m.battery_percent:.0f}%", plug)
        else:
            st.metric("Battery", "—", "N/A")
    with col5:
        st.metric("Thermal pressure", m.thermal_pressure or "—", "Apple Silicon" if m.thermal_pressure else "")

    if m.temperatures:
        st.subheader("Temperatures (°C)")
        cols = st.columns(min(len(m.temperatures), 4))
        for i, (name, val) in enumerate(sorted(m.temperatures.items())):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), f"{val:.1f}", "°C")

    if m.fan_speeds:
        st.subheader("Fan speeds (RPM)")
        cols = st.columns(min(len(m.fan_speeds), 4))
        for i, (name, rpm) in enumerate(sorted(m.fan_speeds.items())):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), str(rpm), "RPM")

    if m.power_estimates:
        st.subheader("Power (estimated W)")
        cols = st.columns(min(len(m.power_estimates), 4))
        for i, (name, w) in enumerate(sorted(m.power_estimates.items())):
            cols[i % len(cols)].metric(name.replace("_", " ").title(), f"{w:.2f}", "W")

    if not m.smc_available and not m.temperatures and not m.fan_speeds and not m.thermal_pressure:
        st.info(
            "**Thermal pressure & power:** run with sudo: `sudo .venv/bin/streamlit run dashboard.py`  \n"
            "**Temperature & fan:** install one of: **iStats** (`gem install iStats`) or **osx-cpu-temp** (`brew install osx-cpu-temp`). See README."
        )


def main() -> None:
    st.set_page_config(page_title="Mac System Metrics", layout="wide")
    st.title("Mac System Metrics")

    refresh = st.sidebar.slider("Refresh every (seconds)", 1, 30, 3)
    if st.sidebar.button("Refresh now"):
        st.rerun()

    m = collect()
    render_metrics(m)

    time.sleep(refresh)
    st.rerun()


if __name__ == "__main__":
    main()
