"""Offline stand-ins for HTTP and DNS used by collector tests."""
import json
from datetime import datetime, timezone

import requests

from collect.registry import Context


class FakeResponse:
    def __init__(self, status_code=200, text="", content=None, json_data=None):
        self.status_code = status_code
        self.text = text if json_data is None else json.dumps(json_data)
        self.content = content if content is not None else self.text.encode("utf-8")

    @property
    def ok(self):
        return self.status_code < 400

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return json.loads(self.text)


class FakeSession:
    """Answers GETs from a {url_prefix: FakeResponse} table and records calls."""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        for prefix, response in self.routes.items():
            if url.startswith(prefix):
                return response
        raise requests.ConnectionError(f"no fake route for {url}")


def make_ctx(routes=None, env=None, now=None, aaaa=None, a=None) -> Context:
    names = set(aaaa or ())
    v4_names = None if a is None else set(a)
    return Context(
        session=FakeSession(routes),
        env=env or {},
        now=now or datetime(2026, 10, 14, 0, 5, tzinfo=timezone.utc),
        has_aaaa=lambda name: name in names,
        has_a=(lambda name: True) if v4_names is None else (lambda name: name in v4_names),
    )
