"""Registry of the data sources collected by the daily pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

DAY = 86_400
MONTH = 30 * DAY


@dataclass(frozen=True)
class Context:
    """Everything a fetch function may use. Injected so tests run offline."""

    session: Any  # requests.Session, or tests.fakes.FakeSession
    env: Mapping[str, str]
    now: datetime
    has_aaaa: Callable[[str], bool | None]  # None = lookup failed
    has_a: Callable[[str], bool | None] = lambda name: True  # None = lookup failed


@dataclass(frozen=True)
class Source:
    key: str
    ttl_seconds: int
    fetch: Callable[[Context], dict[str, Any]]
    title: str
    url: str
    requires_env: tuple[str, ...] = ()
    schema: int = 1  # bump when the payload's shape changes, so stored JSON is re-fetched


SOURCES: dict[str, Source] = {}


def source(key: str, ttl_seconds: int, *, title: str, url: str, requires_env: tuple[str, ...] = (),
           schema: int = 1):
    """Register a fetch function. The JSON is written to data/<key>.json."""

    def register(fn):
        if key in SOURCES:
            raise ValueError(f"duplicate source key: {key}")
        SOURCES[key] = Source(key, ttl_seconds, fn, title, url, requires_env, schema)
        return fn

    return register
