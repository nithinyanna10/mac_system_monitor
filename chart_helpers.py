"""
Reusable Plotly chart builders for the dashboard.
Consistent dark theme, colors, and layout.
"""
from __future__ import annotations

from typing import Any

# Theme
THEME = "plotly_dark"
PAPER_BG = "rgba(0,0,0,0)"
PLOT_BG = "rgba(0,0,0,0)"
COLORS = {
    "cpu": "#00d4aa",
    "memory": "#6c5ce7",
    "disk": "#fd79a8",
    "battery": "#fdcb6e",
    "network_sent": "#00d4aa",
    "network_recv": "#6c5ce7",
    "read": "#00d4aa",
    "write": "#fd79a8",
}


def _layout(height: int = 400, title: str | None = None, showlegend: bool = True, **kwargs: Any) -> dict:
    base = {
        "template": THEME,
        "paper_bgcolor": PAPER_BG,
        "plot_bgcolor": PLOT_BG,
        "height": height,
        "margin": {"t": 40 if title else 20, "b": 40, "l": 50, "r": 30},
        "showlegend": showlegend,
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02} if showlegend else {},
    }
    if title:
        base["title"] = {"text": title}
    base.update(kwargs)
    return base


def line_chart(
    x: list,
    y: list,
    name: str = "series",
    color: str | None = None,
    height: int = 400,
    yaxis_title: str = "",
    yaxis_range: tuple[float, float] | None = None,
) -> "Any":
    """Single line chart."""
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, name=name, line=dict(color=color or COLORS["cpu"])))
    fig.update_layout(**_layout(height=height))
    fig.update_yaxes(title_text=yaxis_title, range=yaxis_range)
    return fig


def multi_line_chart(
    x: list,
    series: list[tuple[str, list, str | None]],
    height: int = 400,
    yaxis_title: str = "",
) -> "Any":
    """Multiple lines on one chart."""
    import plotly.graph_objects as go
    fig = go.Figure()
    for name, y_vals, color in series:
        fig.add_trace(go.Scatter(x=x, y=y_vals, name=name, line=dict(color=color or COLORS["cpu"])))
    fig.update_layout(**_layout(height=height))
    fig.update_yaxes(title_text=yaxis_title)
    return fig


def subplots_2x2(
    titles: tuple[str, str, str, str],
    x: list,
    y1: list,
    y2: list,
    y3: list,
    y4: list,
    names: tuple[str, str, str, str] = ("CPU", "Memory", "Disk", "Battery"),
    colors: tuple[str, str, str, str] = (COLORS["cpu"], COLORS["memory"], COLORS["disk"], COLORS["battery"]),
    height: int = 500,
) -> "Any":
    """2x2 subplot layout."""
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=titles,
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )
    fig.add_trace(go.Scatter(x=x, y=y1, name=names[0], line=dict(color=colors[0])), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=y2, name=names[1], line=dict(color=colors[1])), row=1, col=2)
    fig.add_trace(go.Scatter(x=x, y=y3, name=names[2], line=dict(color=colors[2])), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=y4, name=names[3], line=dict(color=colors[3])), row=2, col=2)
    fig.update_layout(**_layout(height=height))
    for i in range(1, 5):
        fig.update_yaxes(title_text="%", row=(i - 1) // 2 + 1, col=(i - 1) % 2 + 1)
    return fig


def gauge(value: float, title: str = "Value", suffix: str = "%", range_min: float = 0, range_max: float = 100) -> "Any":
    """Gauge indicator."""
    import plotly.graph_objects as go
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix},
        gauge={
            "axis": {"range": [range_min, range_max]},
            "bar": {"color": COLORS["memory"]},
            "steps": [
                {"range": [range_min, (range_max - range_min) * 0.6 + range_min], "color": "rgba(0,0,0,0.2)"},
                {"range": [(range_max - range_min) * 0.6 + range_min, (range_max - range_min) * 0.9 + range_min], "color": "rgba(253, 121, 168, 0.3)"},
                {"range": [(range_max - range_min) * 0.9 + range_min, range_max], "color": "rgba(255, 107, 107, 0.5)"},
            ],
        },
        title={"text": title},
    ))
    fig.update_layout(**_layout(height=280))
    return fig


def bar_chart(labels: list[str], values: list[float], color: str = COLORS["cpu"], height: int = 300) -> "Any":
    """Horizontal or vertical bar chart."""
    import plotly.graph_objects as go
    fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color=color)])
    fig.update_layout(**_layout(height=height))
    return fig


def table_from_dict(data: dict[str, Any]) -> "Any":
    """Plotly table from dict (keys = header, values = row)."""
    import plotly.graph_objects as go
    fig = go.Figure(data=[go.Table(
        header=dict(values=list(data.keys()), fill_color="rgba(26, 29, 36, 1)", align="left"),
        cells=dict(values=[[str(v)] for v in data.values()], fill_color="rgba(14, 17, 23, 1)", align="left"),
    )])
    fig.update_layout(**_layout(height=min(400, 50 + len(data) * 30)))
    return fig
