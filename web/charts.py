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
