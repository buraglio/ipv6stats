"""Plotly figures rendered as HTML fragments. plotly.min.js is loaded once by base.html."""
from __future__ import annotations

import plotly.graph_objects as go
from markupsafe import Markup

from web.data import Datum

BUTTONS_Y = 1.02  # range buttons just above the plot, right-aligned
RANGE_BUTTONS = [
    dict(count=6, label="6m", step="month", stepmode="backward"),
    dict(count=1, label="1y", step="year", stepmode="backward"),
    dict(count=2, label="2y", step="year", stepmode="backward"),
    dict(count=5, label="5y", step="year", stepmode="backward"),
    dict(step="all", label="All"),
]


def line_chart(d: Datum | None, *, x: str, y: str, title: str, y_title: str) -> Markup | None:
    if d is None:
        return None
    fig = go.Figure(go.Scatter(x=[p[x] for p in d.value], y=[p[y] for p in d.value],
                               mode="lines", line=dict(width=2)))
    fig.update_layout(
        title=title, height=340, showlegend=False, yaxis_title=y_title,
        margin=dict(l=56, r=16, t=48, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(type="date", rangeselector=dict(buttons=RANGE_BUTTONS, x=1, xanchor="right", y=BUTTONS_Y)),
    )
    return Markup(fig.to_html(full_html=False, include_plotlyjs=False,
                              config={"displaylogo": False, "responsive": True}))


TOPOJSON_DIR = "static/topojson/"
CONFIG = {"displaylogo": False, "responsive": True}
PERCENT_RANGE = [0, 100]


def _html(fig: go.Figure, **extra_config) -> Markup:
    return Markup(fig.to_html(full_html=False, include_plotlyjs=False, config={**CONFIG, **extra_config}))


def _layout(fig: go.Figure, title: str, y_title: str) -> None:
    fig.update_layout(title=title, height=340, yaxis_title=y_title, margin=dict(l=56, r=16, t=48, b=40),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")


def bar_chart(d: Datum | None, *, x: str, y: str, title: str, y_title: str) -> Markup | None:
    if d is None:
        return None
    fig = go.Figure(go.Bar(x=[p[x] for p in d.value], y=[p[y] for p in d.value]))
    _layout(fig, title, y_title)
    fig.update_layout(showlegend=False)
    return _html(fig)


def multi_line_chart(d: Datum | None, *, title: str, y_title: str, x_type: str = "date") -> Markup | None:
    if d is None:
        return None
    fig = go.Figure([go.Scatter(x=[p["x"] for p in s["points"]], y=[p["y"] for p in s["points"]],
                                mode="lines", name=s["name"]) for s in d.value])
    _layout(fig, title, y_title)
    xaxis = dict(type=x_type)
    if x_type == "date":
        xaxis["rangeselector"] = dict(buttons=RANGE_BUTTONS, x=1, xanchor="right", y=BUTTONS_Y)
    fig.update_layout(xaxis=xaxis, legend=dict(orientation="h"))
    return _html(fig)


def choropleth(d: Datum | None, *, title: str, topojson_url: str) -> Markup | None:
    if d is None:
        return None
    fig = go.Figure(go.Choropleth(
        locations=[p["iso3"] for p in d.value], z=[p["capable"] for p in d.value],
        text=[p["name"] for p in d.value], locationmode="ISO-3", colorscale="Blues",
        zmin=PERCENT_RANGE[0], zmax=PERCENT_RANGE[1], colorbar=dict(title="%"),
        hovertemplate="%{text}: %{z:.1f}%<extra></extra>"))
    fig.update_layout(title=title, height=460, margin=dict(l=0, r=0, t=48, b=0),
                      paper_bgcolor="rgba(0,0,0,0)",
                      geo=dict(showframe=False, projection_type="natural earth", bgcolor="rgba(0,0,0,0)"))
    return _html(fig, topojsonURL=topojson_url)
