"""Daily snapshots of headline values, appended to data/history.json after each run.

Sources whose values change slowly are recorded as they stand that day; a source that
failed or is in an outdated format is left out of that day's entry.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Mapping

HISTORY = "history.json"
TRACKED = {
    "apnic_world_capable": ("apnic", ("world", "capable")),
    "cloudflare_ipv6": ("cloudflare_ip_version", ("latest_ipv6",)),
    "tranco_aaaa": ("tranco_aaaa", ("percentage",)),
    "isoc_top_sites": ("isoc_pulse", ("websites_ipv6", "latest", "value")),
}


def load(data_dir: Path) -> list[dict]:
    path = Path(data_dir) / HISTORY
    return json.loads(path.read_text()) if path.exists() else []


def _value(data_dir: Path, manifest: dict, sources: Mapping, key: str, path: tuple):
    entry, src = manifest.get(key, {}), sources.get(key)
    if src is None or entry.get("status") != "ok" or entry.get("schema", 1) != src.schema:
        return None
    file = Path(data_dir) / f"{key}.json"
    if not file.exists():
        return None
    value = json.loads(file.read_text())
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def record(data_dir: Path, manifest: dict, sources: Mapping, now: datetime) -> dict | None:
    values = {name: v for name, (key, path) in TRACKED.items()
              if (v := _value(data_dir, manifest, sources, key, path)) is not None}
    if not values:
        return None
    today = {"date": now.date().isoformat(), "values": values}
    entries = [h for h in load(data_dir) if h["date"] != today["date"]] + [today]
    entries.sort(key=lambda h: h["date"])
    (Path(data_dir) / HISTORY).write_text(json.dumps(entries, indent=1) + "\n")
    return today
