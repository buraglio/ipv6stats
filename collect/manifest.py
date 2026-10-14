"""data/manifest.json: per-source status, timestamps and re-fetch interval."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

MANIFEST = "manifest.json"
# Scheduled runs start a few minutes apart from night to night; without this,
# a daily source last fetched at 00:07 would not be due again at 00:05.
GRACE = timedelta(hours=1)


def load(data_dir: Path) -> dict:
    path = Path(data_dir) / MANIFEST
    return json.loads(path.read_text()) if path.exists() else {}


def save(data_dir: Path, manifest: dict) -> None:
    path = Path(data_dir) / MANIFEST
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def is_due(entry: dict | None, ttl_seconds: int, now: datetime) -> bool:
    if not entry or not entry.get("last_success"):
        return True
    last = datetime.fromisoformat(entry["last_success"])
    return now - last >= timedelta(seconds=ttl_seconds) - GRACE
