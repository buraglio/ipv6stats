"""Hand-maintained reference data (reference/*.toml), validated when loaded."""
from __future__ import annotations

import tomllib
from datetime import date, datetime
from pathlib import Path

CLOUD_FILE = Path(__file__).resolve().parent.parent / "reference" / "cloud_providers.toml"
REQUIRED = ("key", "name", "last_reviewed")
LIST_FIELDS = ("limitations", "recent_progress", "special_features", "notes", "service")
MAX_AGE_DAYS = 180


def load_cloud_providers(path: Path = CLOUD_FILE) -> list[dict]:
    providers = tomllib.loads(Path(path).read_text(encoding="utf-8")).get("provider", [])
    seen = set()
    for p in providers:
        for field in REQUIRED:
            if not p.get(field):
                raise ValueError(f"{path.name}: provider {p.get('key', '?')} is missing {field}")
        try:
            date.fromisoformat(p["last_reviewed"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path.name}: {p['key']} has an invalid last_reviewed {p['last_reviewed']!r}") from exc
        if p["key"] in seen:
            raise ValueError(f"{path.name}: duplicate provider key {p['key']}")
        seen.add(p["key"])
        for field in LIST_FIELDS:
            p.setdefault(field, [])
    return providers


def stale_reviews(providers: list[dict], now: datetime, max_age_days: int = MAX_AGE_DAYS) -> list[str]:
    warnings = []
    for p in providers:
        age = (now.date() - date.fromisoformat(p["last_reviewed"])).days
        if age > max_age_days:
            warnings.append(f"cloud_providers.toml: {p['name']} last reviewed {p['last_reviewed']} ({age} days ago)")
    return warnings
