"""This site's own measurements over time, appended to data/history.json after each run.

Only measurements with no published history of their own are tracked (sources that publish
a dated series are charted from that series). A value is recorded only on a day its source
was actually fetched, dated by that fetch, so a monthly source contributes a point a month;
an old value is never re-recorded under a later date.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping

HISTORY = "history.json"


def _share(part: float, whole: float) -> float | None:
    return round(100 * part / whole, 1) if whole else None


TRACKED: dict[str, tuple[str, Callable[[dict], float | None]]] = {
    "tranco_aaaa": ("tranco_aaaa", lambda p: p["percentage"]),
    "cloud_hostnames": ("cloud_endpoints", lambda p: _share(sum(x["with_ipv6"] for x in p["providers"]),
                                                            sum(x["checked"] for x in p["providers"]))),
    "nist_web": ("nist_usgv6", lambda p: _share(p["totals"]["web"].get("operational", 0), p["domains"])),
}


def load(data_dir: Path) -> list[dict]:
    path = Path(data_dir) / HISTORY
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text())
    except ValueError as exc:
        raise ValueError(f"{HISTORY} is not valid JSON: {exc}") from exc
    if not isinstance(entries, list) or not all(isinstance(e, dict) and "date" in e and "values" in e for e in entries):
        raise ValueError(f"{HISTORY} has an unexpected shape")
    return entries


def _value(data_dir: Path, manifest: dict, sources: Mapping, key: str, pick, today: str):
    entry, src = manifest.get(key, {}), sources.get(key)
    if (src is None or entry.get("status") != "ok" or entry.get("schema", 1) != src.schema
            or not str(entry.get("last_success", "")).startswith(today)):  # not fetched today: nothing new
        return None
    file = Path(data_dir) / f"{key}.json"
    if not file.exists():
        return None
    try:
        return pick(json.loads(file.read_text()))
    except (KeyError, TypeError, ValueError):
        return None


def record(data_dir: Path, manifest: dict, sources: Mapping, now: datetime) -> dict | None:
    today = now.date().isoformat()
    values = {name: v for name, (key, pick) in TRACKED.items()
              if (v := _value(data_dir, manifest, sources, key, pick, today)) is not None}
    if not values:
        return None
    entries = [h for h in load(data_dir) if h["date"] != today]  # raises on a corrupt file: never overwrite it
    entries.append({"date": today, "values": values})
    entries.sort(key=lambda h: h["date"])
    path = Path(data_dir) / HISTORY
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries, indent=1) + "\n")
    os.replace(tmp, path)
    return {"date": today, "values": values}
