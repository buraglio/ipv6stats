"""Read collected JSON and hand pages Datum objects that carry provenance."""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable

import collect.sources  # noqa: F401  (registers sources)
from collect import manifest as manifest_file
from collect.registry import DAY, SOURCES

STALE_FACTOR = 2


@dataclass(frozen=True)
class Datum:
    value: Any
    sources: tuple[str, ...]
    fetched_at: datetime  # oldest input's last successful fetch
    stale: bool


def combine(value: Any, inputs: Iterable[Datum]) -> Datum:
    inputs = list(inputs)
    if not inputs:
        raise ValueError("combine() needs at least one input")
    return Datum(value, tuple(sorted({s for d in inputs for s in d.sources})),
                 min(d.fetched_at for d in inputs), any(d.stale for d in inputs))


def field(d: Datum | None, key: str) -> Datum | None:
    """A Datum for one key of a dict-valued Datum, keeping its provenance."""
    if d is None or not isinstance(d.value, dict) or d.value.get(key) is None:
        return None
    return replace(d, value=d.value[key])


class Data:
    def __init__(self, data_dir: Path, now: datetime):
        self.data_dir = Path(data_dir)
        self.now = now
        self.manifest = manifest_file.load(self.data_dir)
        self._payloads: dict[str, dict | None] = {}

    def payload(self, key: str) -> dict | None:
        if key not in SOURCES:
            raise KeyError(f"unknown source: {key}")
        if key not in self._payloads:
            path = self.data_dir / f"{key}.json"
            ok = self.manifest.get(key, {}).get("last_success") and self._current_format(key) and path.exists()
            self._payloads[key] = json.loads(path.read_text()) if ok else None
        return self._payloads[key]

    def _current_format(self, key: str) -> bool:
        """False for JSON written by an older parser; it is unavailable until re-fetched."""
        return self.manifest.get(key, {}).get("schema", 1) == SOURCES[key].schema

    def fetched_at(self, key: str) -> datetime:
        return datetime.fromisoformat(self.manifest[key]["last_success"])

    def is_stale(self, key: str) -> bool:
        limit = timedelta(seconds=STALE_FACTOR * SOURCES[key].ttl_seconds)
        return self.now - self.fetched_at(key) > limit

    def datum(self, key: str, pick: Callable[[dict], Any]) -> Datum | None:
        payload = self.payload(key)
        if payload is None:
            return None
        try:
            value = pick(payload)
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"{key}.json is missing an expected field: {exc!r}") from exc
        if value is None:
            return None
        return Datum(value, (key,), self.fetched_at(key), self.is_stale(key))

    def status_rows(self) -> list[dict]:
        rows = []
        for key, src in SOURCES.items():
            entry = self.manifest.get(key, {})
            rows.append({
                "key": key, "title": src.title, "url": src.url,
                "status": ("outdated format" if entry.get("last_success") and not self._current_format(key)
                           else entry.get("status", "never run")),
                "error": entry.get("error"),
                "last_success": entry.get("last_success"), "last_attempt": entry.get("last_attempt"),
                "ttl_days": src.ttl_seconds // DAY,
                "stale": bool(entry.get("last_success")) and self.is_stale(key),
            })
        return rows
