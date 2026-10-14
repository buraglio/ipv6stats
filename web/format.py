"""Jinja filters for displaying Datum values and their provenance."""
from __future__ import annotations

from collect.registry import SOURCES
from web.data import Datum


def format_value(value, fmt: str) -> str:
    if fmt == "int":
        return f"{int(round(value)):,}"
    if fmt == "signed_int":
        return f"{int(round(value)):+,}"
    if fmt == "pct":
        return f"{value:.1f}%"
    if fmt == "pct_points":
        return f"{value:+.1f} points"
    if fmt == "text":
        return str(value)
    raise ValueError(f"unknown format: {fmt}")


def provenance_text(d: Datum) -> str:
    titles = ", ".join(SOURCES[key].title for key in d.sources)
    return f"Source: {titles} · as of {d.fetched_at.date().isoformat()}"


def date_only(iso: str | None) -> str:
    return iso[:10] if iso else "never"
