# Static Site Plan 1: Foundation + Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily GitHub Actions pipeline that collects real IPv6 data into JSON and publishes a static Overview page to GitHub Pages (preview at `buraglio.github.io/ipv6stats/`).

**Architecture:** `collect/` holds data sources registered with `@source(...)`. `collect/run.py` fetches the sources that are due, writes `data/<key>.json`, and keeps `data/manifest.json` with each source's status. `web/` reads only that JSON and renders Jinja2 templates plus Plotly charts into `dist/`. The only interface between the two is the JSON. A workflow runs both daily, stores the data on a `data` branch, and deploys `dist/` to Pages. The Streamlit app (`app.py`, `data_sources.py`, etc.) is **not touched** in this plan.

**Tech Stack:** Python 3.12, uv, requests, dnspython, Jinja2, Plotly (Python, for figures; its bundled `plotly.min.js` is served from the site), pytest, GitHub Actions (`astral-sh/setup-uv`, `actions/upload-pages-artifact`, `actions/deploy-pages`).

**Spec:** `docs/superpowers/specs/2026-10-14-static-site-migration-design.md` (read **Amendment 1** at the end; it overrides earlier sections).

## Global Constraints

- Branch: all work on `static-site`. Do not modify `app.py`, `data_sources.py`, `visualization.py`, `components.py`, `utils.py`, `data_manager.py`, `page_modules/`, `cloud_data.py`, `ipv6stats.service`, `start_ipv6stats.sh`.
- `web/` must never be named `site/` (clashes with Python's stdlib `site` module).
- A collector either returns parsed data or raises. No fallback or hard-coded values in `collect/`. The string `"fallback"` must not appear in `collect/`.
- No statistic (e.g. `49%`, `228,789`) may appear as a literal in `collect/`, `web/` Python string literals, or `web/templates/` outside a `{% call reference(...) %}` block.
- Every number shown on a page goes through a `Datum` (`value`, `sources`, `fetched_at`, `stale`).
- Re-fetch intervals: `bgp_v6_table` daily (`DAY`); all other Plan 1 sources `MONTH` (30 days).
- Failure threshold: the run exits non-zero if **more than 25%** of attempted sources fail.
- Stale: a source's last success is older than **2×** its re-fetch interval.
- APNIC rankings count only economies with **≥ 100,000 samples** (`MIN_SAMPLES = 100_000`).
- Schedule: `cron: "0 0 * * *"` (UTC). Footer text: `Data refreshed daily at 00:00 UTC · Last build: <YYYY-MM-DD HH:MM UTC>`.
- All internal links and asset URLs are relative (the preview is served under `/ipv6stats/`).
- Third-party requests from pages: only `https://ipv6.army/images/v6.png` (logo). `plotly.min.js` is served from `static/`.

## Review Focus

1. **A source answers HTTP 200 but its format changed** (APNIC HTML, Cloudflare JSON, delegation files). The parser must raise so the last good data stays. Tests: each source's `test_*_rejects_changed_format` in Tasks 3–7.
2. **First run ever, with an empty or missing data dir** (no `data` branch yet). The build must succeed and show "— source unavailable". Test: `test_empty_data_dir_still_builds` (Task 10).
3. **`CLOUDFLARE_API_KEY` missing or blank in CI.** The source is "not configured", not a failure, and the consensus averages the remaining sources. Tests: `test_blank_env_value_counts_as_missing` (Task 2), `test_consensus_skips_missing_component` (Task 8).
4. **Stale data presented as current.** It must show "⚠ stale since <date>". Test: `test_stale_source_is_marked` (Task 10).
5. **Site served under a subpath** (`/ipv6stats/`). No root-absolute links. Test: `test_internal_links_are_relative_and_resolve` (Task 9).

---

## File Structure

```
.python-version                     # 3.12
pyproject.toml                      # + jinja2, dnspython, python-dotenv, pytest; uv package=false
.gitignore                          # + data/, dist/, .pytest_cache/
collect/
  __init__.py
  registry.py                       # Context, Source, SOURCES, @source, DAY, MONTH
  http.py                           # make_session()
  dns.py                            # dns_has_aaaa()
  manifest.py                       # load(), save(), is_due()
  run.py                            # run(), exceeds_threshold(), main()
  sources/
    __init__.py                     # imports every source module (registers them)
    apnic.py                        # key "apnic"
    bgp.py                          # key "bgp_v6_table"
    cloudflare.py                   # key "cloudflare_ip_version" (needs CLOUDFLARE_API_KEY)
    tranco.py                       # key "tranco_aaaa"
    rir.py                          # keys "lacnic_delegations", "afrinic_delegations"
    isoc.py                         # key "isoc_pulse" (opt-in, needs ISOC_PULSE_API_KEY)
web/
  __init__.py
  data.py                           # Datum, combine(), Data
  derive.py                         # consensus and other derived values
  format.py                         # Jinja filters: format_value, provenance_text, date_only
  charts.py                         # line_chart()
  build.py                          # Page, PAGES, LEGACY_PAGES, build(), check_reference_dates(), main()
  pages/
    __init__.py
    overview.py                     # context(data)
  templates/
    base.html  macros.html  overview.html
  static/
    site.css  theme.js  legacy-redirect.js
tests/
  __init__.py
  fakes.py                          # FakeResponse, FakeSession, make_ctx()
  sample_data.py                    # NOW, FETCHED, PAYLOADS, write_sample_data()
  fixtures/apnic/ipv6.html          # recorded real page
  fixtures/bgp/bgp-active.txt       # recorded real file (one line in 24)
  test_registry.py  test_run.py  test_apnic.py  test_bgp.py  test_cloudflare.py
  test_tranco.py  test_rir.py  test_data.py  test_derive.py  test_build.py
  test_overview.py  test_no_static_stats.py
.github/workflows/publish.yml
README.md                           # + "Static site (GitHub Pages)" section
```

---

### Task 1: Project setup and source registry

**Files:**
- Modify: `pyproject.toml` (whole file)
- Create: `.python-version`, `collect/__init__.py`, `collect/registry.py`, `collect/http.py`, `tests/__init__.py`, `tests/fakes.py`, `tests/test_registry.py`
- Modify: `.gitignore` (append)

**Interfaces:**
- Produces: `collect.registry.Context(session, env, now, has_aaaa)`, `Source(key, ttl_seconds, fetch, title, url, requires_env)`, `SOURCES: dict[str, Source]`, `source(key, ttl_seconds, *, title, url, requires_env=())`, `DAY = 86_400`, `MONTH = 2_592_000`; `collect.http.make_session() -> requests.Session`; `tests.fakes.FakeResponse`, `FakeSession(routes: dict[str, FakeResponse])`, `make_ctx(routes=None, env=None, now=None, aaaa=None) -> Context`.

- [ ] **Step 1: Make sure uv is installed**

Run: `uv --version || brew install uv`
Expected: prints a uv version.

- [ ] **Step 2: Replace `pyproject.toml`**

```toml
[project]
name = "ipv6stats"
version = "1.0.0"
description = "IPv6 Statistics Dashboard - global IPv6 adoption metrics"
requires-python = ">=3.11"
dependencies = [
    "folium>=0.20.0",
    "streamlit-folium>=0.25.1",
    "streamlit>=1.48.1",
    "trafilatura>=2.0.0",
    "requests>=2.32.4",
    "pandas>=2.3.1",
    "numpy>=2.3.2",
    "plotly>=6.3.0",
    "python-dotenv>=1.0.0",
    "jinja2>=3.1.4",
    "dnspython>=2.6.1",
]

[dependency-groups]
dev = ["pytest>=8.3"]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
```

(Streamlit dependencies stay until the switch-over plan; the container still runs the old app.)

- [ ] **Step 3: Pin Python and ignore generated directories**

`.python-version`:
```
3.12
```

Append to `.gitignore`:
```
# Static site pipeline
data/
dist/
.pytest_cache/
```

- [ ] **Step 4: Lock and install**

Run: `uv lock && uv sync`
Expected: `uv.lock` updated; environment created in `.venv/`.

- [ ] **Step 5: Write the failing test** — `tests/__init__.py` (empty file) and `tests/test_registry.py`:

```python
import pytest

from collect.registry import DAY, SOURCES, source


def test_source_registers_and_returns_function():
    @source("test_registry_example", DAY, title="Example", url="https://example.net/")
    def fetch(ctx):
        return {"ok": True}

    try:
        src = SOURCES["test_registry_example"]
        assert src.fetch is fetch
        assert src.ttl_seconds == DAY
        assert src.title == "Example"
        assert src.url == "https://example.net/"
        assert src.requires_env == ()
    finally:
        del SOURCES["test_registry_example"]


def test_duplicate_key_rejected():
    @source("test_registry_dup", DAY, title="Dup", url="https://example.net/")
    def first(ctx):
        return {}

    try:
        with pytest.raises(ValueError, match="duplicate source key"):
            @source("test_registry_dup", DAY, title="Dup", url="https://example.net/")
            def second(ctx):
                return {}
    finally:
        del SOURCES["test_registry_dup"]
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'collect'`.

- [ ] **Step 7: Implement** — `collect/__init__.py` (empty file), then `collect/registry.py`:

```python
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
    has_aaaa: Callable[[str], bool]


@dataclass(frozen=True)
class Source:
    key: str
    ttl_seconds: int
    fetch: Callable[[Context], dict[str, Any]]
    title: str
    url: str
    requires_env: tuple[str, ...] = ()


SOURCES: dict[str, Source] = {}


def source(key: str, ttl_seconds: int, *, title: str, url: str, requires_env: tuple[str, ...] = ()):
    """Register a fetch function. The JSON is written to data/<key>.json."""

    def register(fn):
        if key in SOURCES:
            raise ValueError(f"duplicate source key: {key}")
        SOURCES[key] = Source(key, ttl_seconds, fn, title, url, requires_env)
        return fn

    return register
```

`collect/http.py`:

```python
"""Shared HTTP session for collectors."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "ipv6stats/2.0 (+https://stats.ipv6.army)"


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    retry = Retry(total=2, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
```

`tests/fakes.py`:

```python
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


def make_ctx(routes=None, env=None, now=None, aaaa=None) -> Context:
    names = set(aaaa or ())
    return Context(
        session=FakeSession(routes),
        env=env or {},
        now=now or datetime(2026, 10, 14, 0, 5, tzinfo=timezone.utc),
        has_aaaa=lambda name: name in names,
    )
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/test_registry.py -v`
Expected: 2 passed.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock .python-version .gitignore collect/ tests/
git commit -m "Add collector registry and test fakes for static site pipeline"
```

---

### Task 2: Manifest and collection runner

**Files:**
- Create: `collect/manifest.py`, `collect/run.py`, `collect/dns.py`, `collect/sources/__init__.py`, `tests/test_run.py`

**Interfaces:**
- Consumes: `Context`, `Source`, `SOURCES`, `DAY` (Task 1); `make_ctx` (Task 1).
- Produces: `collect.manifest.load(data_dir: Path) -> dict`, `save(data_dir: Path, manifest: dict) -> None`, `is_due(entry: dict | None, ttl_seconds: int, now: datetime) -> bool`, `GRACE = timedelta(hours=1)`; `collect.run.RunResult(attempted, failed, skipped, not_configured)`, `run(sources, data_dir, ctx, force=False, only=None) -> RunResult`, `exceeds_threshold(result) -> bool`, `FAILURE_THRESHOLD = 0.25`, `main(argv=None) -> int`; `collect.dns.dns_has_aaaa(name: str) -> bool`.
- Manifest entry fields: `ttl_seconds`, `status` (`"ok" | "error" | "not_configured"`), `error` (str or None), `last_attempt`, `last_success` (ISO 8601 with `+00:00`).

- [ ] **Step 1: Write the failing tests** — `tests/test_run.py`:

```python
import json
from datetime import datetime, timedelta, timezone

from collect.manifest import load
from collect.registry import DAY, Source
from collect.run import RunResult, exceeds_threshold, run
from tests.fakes import make_ctx

NOW = datetime(2026, 10, 14, 0, 5, tzinfo=timezone.utc)


def stub(key, fn, ttl=DAY, requires_env=()):
    return Source(key, ttl, fn, "Stub", "https://example.net/", requires_env)


def never_called(ctx):
    raise AssertionError("fetch should not have been called")


def test_successful_fetch_writes_payload_and_manifest(tmp_path):
    result = run({"a": stub("a", lambda c: {"x": 1})}, tmp_path, make_ctx(now=NOW))

    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 1}
    entry = load(tmp_path)["a"]
    assert entry["status"] == "ok"
    assert entry["error"] is None
    assert entry["last_success"] == NOW.isoformat(timespec="seconds")
    assert entry["ttl_seconds"] == DAY
    assert result.attempted == ["a"] and result.failed == []


def test_failed_fetch_keeps_previous_payload(tmp_path):
    earlier = NOW - timedelta(days=2)
    run({"a": stub("a", lambda c: {"x": 1})}, tmp_path, make_ctx(now=earlier))

    def boom(ctx):
        raise RuntimeError("boom")

    result = run({"a": stub("a", boom)}, tmp_path, make_ctx(now=NOW))

    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 1}
    entry = load(tmp_path)["a"]
    assert entry["status"] == "error"
    assert "boom" in entry["error"]
    assert entry["last_success"] == earlier.isoformat(timespec="seconds")
    assert entry["last_attempt"] == NOW.isoformat(timespec="seconds")
    assert result.failed == ["a"]


def test_empty_payload_is_a_failure(tmp_path):
    result = run({"a": stub("a", lambda c: {})}, tmp_path, make_ctx(now=NOW))
    assert result.failed == ["a"]
    assert not (tmp_path / "a.json").exists()


def test_unserializable_payload_is_a_failure_and_writes_nothing(tmp_path):
    result = run({"a": stub("a", lambda c: {"x": object()})}, tmp_path, make_ctx(now=NOW))
    assert result.failed == ["a"]
    assert not (tmp_path / "a.json").exists()


def test_missing_env_is_not_configured(tmp_path):
    sources = {"a": stub("a", never_called, requires_env=("TOKEN",))}
    result = run(sources, tmp_path, make_ctx(env={}, now=NOW))
    assert result.not_configured == ["a"]
    assert result.attempted == []
    entry = load(tmp_path)["a"]
    assert entry["status"] == "not_configured"
    assert "TOKEN" in entry["error"]


def test_blank_env_value_counts_as_missing(tmp_path):
    sources = {"a": stub("a", never_called, requires_env=("TOKEN",))}
    result = run(sources, tmp_path, make_ctx(env={"TOKEN": "  "}, now=NOW))
    assert result.not_configured == ["a"]


def test_source_not_due_is_skipped_unless_forced(tmp_path):
    run({"a": stub("a", lambda c: {"x": 1}, ttl=30 * DAY)}, tmp_path, make_ctx(now=NOW))
    later = make_ctx(now=NOW + timedelta(days=1))

    skipped = run({"a": stub("a", never_called, ttl=30 * DAY)}, tmp_path, later)
    assert skipped.skipped == ["a"]

    forced = run({"a": stub("a", lambda c: {"x": 2}, ttl=30 * DAY)}, tmp_path, later, force=True)
    assert forced.attempted == ["a"]
    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 2}


def test_daily_source_runs_again_the_next_night(tmp_path):
    # Yesterday's run finished at 00:07; tonight's starts at 00:05 (23h58m later).
    yesterday = make_ctx(now=NOW - timedelta(days=1) + timedelta(minutes=2))
    run({"a": stub("a", lambda c: {"x": 1})}, tmp_path, yesterday)
    result = run({"a": stub("a", lambda c: {"x": 2})}, tmp_path, make_ctx(now=NOW))
    assert result.attempted == ["a"]


def test_only_limits_sources(tmp_path):
    sources = {"a": stub("a", lambda c: {"x": 1}), "b": stub("b", never_called)}
    result = run(sources, tmp_path, make_ctx(now=NOW), only={"a"})
    assert result.attempted == ["a"]
    assert "b" not in load(tmp_path)


def test_failure_threshold():
    assert not exceeds_threshold(RunResult(attempted=["a", "b", "c", "d"], failed=["a"]))
    assert exceeds_threshold(RunResult(attempted=["a", "b", "c", "d"], failed=["a", "b"]))
    assert not exceeds_threshold(RunResult())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_run.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'collect.manifest'`.

- [ ] **Step 3: Implement** — `collect/manifest.py`:

```python
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
```

`collect/dns.py`:

```python
"""AAAA lookups for collectors that measure IPv6 deployment themselves."""
import dns.exception
import dns.resolver

_resolver = dns.resolver.Resolver()
_resolver.lifetime = 5.0


def dns_has_aaaa(name: str) -> bool:
    try:
        return len(_resolver.resolve(name, "AAAA")) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        return False
```

`collect/sources/__init__.py`:

```python
"""Importing this package registers every source with collect.registry."""
```

`collect/run.py`:

```python
"""Fetch every due source and write data/<key>.json plus data/manifest.json.

Usage: python -m collect.run [--data-dir data] [--force] [--only KEY ...]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from collect import manifest as manifest_file
from collect.registry import SOURCES, Context, Source

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 0.25
MAX_WORKERS = 3


@dataclass
class RunResult:
    attempted: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    not_configured: list[str] = field(default_factory=list)


def exceeds_threshold(result: RunResult) -> bool:
    if not result.attempted:
        return False
    return len(result.failed) / len(result.attempted) > FAILURE_THRESHOLD


def _write_payload(path: Path, payload: object) -> None:
    if not isinstance(payload, dict) or not payload:
        raise ValueError("fetch returned an empty or non-dict payload")
    text = json.dumps(payload, indent=1, sort_keys=True) + "\n"  # fails before touching the file
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def run(sources: Mapping[str, Source], data_dir: Path, ctx: Context, force: bool = False,
        only: set[str] | None = None) -> RunResult:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = manifest_file.load(data_dir)
    now_iso = ctx.now.isoformat(timespec="seconds")
    result = RunResult()
    due: list[Source] = []

    for key, src in sources.items():
        if only and key not in only:
            continue
        entry = manifest.setdefault(key, {})
        entry["ttl_seconds"] = src.ttl_seconds
        missing = [name for name in src.requires_env if not ctx.env.get(name, "").strip()]
        if missing:
            entry.update(status="not_configured", error=f"set {', '.join(missing)} to enable")
            result.not_configured.append(key)
        elif force or manifest_file.is_due(entry, src.ttl_seconds, ctx.now):
            due.append(src)
        else:
            result.skipped.append(key)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(src.fetch, ctx): src for src in due}
        for future in as_completed(futures):
            src = futures[future]
            entry = manifest[src.key]
            entry["last_attempt"] = now_iso
            result.attempted.append(src.key)
            try:
                _write_payload(data_dir / f"{src.key}.json", future.result())
                entry.update(status="ok", error=None, last_success=now_iso)
            except Exception as exc:  # any failure keeps the previous JSON
                logger.exception("source %s failed", src.key)
                entry.update(status="error", error=f"{type(exc).__name__}: {exc}"[:500])
                result.failed.append(src.key)

    result.attempted.sort()
    result.failed.sort()
    manifest_file.save(data_dir, manifest)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--force", action="store_true", help="re-fetch every source")
    parser.add_argument("--only", action="append", metavar="KEY", help="fetch only these sources")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    import collect.sources  # noqa: F401  (registers sources)
    from collect.dns import dns_has_aaaa
    from collect.http import make_session

    ctx = Context(session=make_session(), env=os.environ, now=datetime.now(timezone.utc),
                  has_aaaa=dns_has_aaaa)
    result = run(SOURCES, Path(args.data_dir), ctx, force=args.force,
                 only=set(args.only) if args.only else None)

    for key in result.failed:
        print(f"::warning::source {key} failed; keeping its previous data")
    print(f"attempted={len(result.attempted)} failed={len(result.failed)} "
          f"skipped={len(result.skipped)} not_configured={len(result.not_configured)}")
    if exceeds_threshold(result):
        print(f"::error::{len(result.failed)} of {len(result.attempted)} sources failed; not publishing")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_run.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add collect/ tests/test_run.py
git commit -m "Add collection runner with manifest, last-good data and failure threshold"
```

---

### Task 3: APNIC source

**Files:**
- Create: `collect/sources/apnic.py`, `tests/fixtures/apnic/ipv6.html`, `tests/test_apnic.py`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Consumes: `source`, `MONTH`, `Context` (Task 1); `make_ctx`, `FakeResponse` (Task 1).
- Produces: source key `"apnic"`; `collect.sources.apnic.parse(page: str, min_economies: int = MIN_ECONOMIES) -> dict`; `URL`. Payload:
  `{"world": Row, "regions": [Row], "economies": [Row sorted by code], "url": str}` where `Row = {"code": str, "name": str, "capable": float, "preferred": float, "samples": int}`.

- [ ] **Step 1: Record the fixture**

Run: `mkdir -p tests/fixtures/apnic && curl -s https://stats.labs.apnic.net/ipv6/ -o tests/fixtures/apnic/ipv6.html && wc -c tests/fixtures/apnic/ipv6.html`
Expected: roughly 70 KB.

- [ ] **Step 2: Write the failing tests** — `tests/test_apnic.py`:

```python
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import apnic
from tests.fakes import FakeResponse, make_ctx

FIXTURE = Path(__file__).parent / "fixtures" / "apnic" / "ipv6.html"

# Three rows in the page's real format: world, a region, an economy.
SAMPLE = r"""
["<a href=\"/ipv6/XA\">XA</a>","<a href=\"/ipv6/XA\">World</a>",{v: 43.65, f:'x'}, {v: 41.02, f: 'x'},972331706]
["<a href=\"/ipv6/XE\">XE</a>","<a href=\"/ipv6/XE\">Europe</a>",{v: 36.87, f:'x'}, {v: 35.72, f: 'x'},134455991]
["<a href=\"/ipv6/CI\">CI</a>","<a href=\"/ipv6/CI\">C&ocirc;te d&#39;Ivoire</a>, <a href=\"/ipv6/XB\">Africa</a>",{v: 1.50, f:'x'}, {v: 1.25, f: 'x'},123456]
["<a href=\"/ipv6/XA\">XA</a>","<a href=\"/ipv6/XA\">World</a>",{v: 99.99, f:'x'}, {v: 99.99, f: 'x'},1]
"""


def test_parse_sample_rows():
    parsed = apnic.parse(SAMPLE, min_economies=1)
    assert parsed["world"] == {"code": "XA", "name": "World", "capable": 43.65,
                               "preferred": 41.02, "samples": 972331706}
    assert [r["name"] for r in parsed["regions"]] == ["Europe"]
    assert parsed["economies"] == [{"code": "CI", "name": "Côte d'Ivoire", "capable": 1.5,
                                    "preferred": 1.25, "samples": 123456}]
    assert parsed["url"] == apnic.URL


def test_parse_recorded_page():
    parsed = apnic.parse(FIXTURE.read_text(encoding="utf-8"))
    assert parsed["world"]["name"] == "World"
    assert 0 < parsed["world"]["capable"] < 100
    assert len(parsed["economies"]) >= 100
    assert "US" in {r["code"] for r in parsed["economies"]}
    assert "Europe" in {r["name"] for r in parsed["regions"]}


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="APNIC page format changed"):
        apnic.parse("<html><body>redesigned</body></html>")


def test_fetch_uses_page():
    ctx = make_ctx(routes={apnic.URL: FakeResponse(text=FIXTURE.read_text(encoding="utf-8"))})
    assert SOURCES["apnic"].fetch(ctx)["world"]["code"] == "XA"


def test_fetch_http_error_raises():
    ctx = make_ctx(routes={apnic.URL: FakeResponse(status_code=503)})
    with pytest.raises(Exception, match="503"):
        SOURCES["apnic"].fetch(ctx)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_apnic.py -v`
Expected: FAIL with `ImportError: cannot import name 'apnic'`.

- [ ] **Step 4: Implement** — `collect/sources/apnic.py`:

```python
"""APNIC Labs IPv6 capability measurement for the world, regions and economies."""
import html
import re

from collect.registry import MONTH, Context, source

URL = "https://stats.labs.apnic.net/ipv6/"
# Rows in the page's embedded chart data look like:
#   ["<a href=\"/ipv6/US\">US</a>","<a href=\"/ipv6/US\">United States of America</a>, <a ...>Americas</a>",
#    {v: 61.90, f:'61.90%'}, {v: 59.85, f: '59.85%'},97679957]
# Fields: code, name (+ parent regions for economies), IPv6-capable, IPv6-preferred, samples.
ROW = re.compile(
    r'\["<a href=\\"/ipv6/([A-Z]{2})\\">[^"]*</a>","(.*?)",'
    r"\{v:\s*([\d.]+)[^}]*\},\s*\{v:\s*([\d.]+)[^}]*\},(\d+)\]"
)
LINK_TEXT = re.compile(r">([^<]+)</a>")
WORLD = "XA"
MIN_ECONOMIES = 100  # fewer means the page layout changed


def parse(page: str, min_economies: int = MIN_ECONOMIES) -> dict:
    world, regions, economies, seen = None, [], [], set()
    for match in ROW.finditer(page):
        code, names, capable, preferred, samples = match.groups()
        if code in seen:  # the page repeats rows in several tables; keep the first
            continue
        seen.add(code)
        links = LINK_TEXT.findall(names)
        row = {"code": code, "name": html.unescape(links[0]) if links else code,
               "capable": float(capable), "preferred": float(preferred), "samples": int(samples)}
        if code == WORLD:
            world = row
        elif len(links) == 1:  # regions list only themselves; economies also list parents
            regions.append(row)
        else:
            economies.append(row)
    if world is None or len(economies) < min_economies:
        raise ValueError(f"APNIC page format changed: world={'found' if world else 'missing'}, "
                         f"economies={len(economies)}")
    return {"world": world, "regions": regions,
            "economies": sorted(economies, key=lambda r: r["code"]), "url": URL}


@source("apnic", MONTH, title="APNIC Labs IPv6 measurement", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=30)
    response.raise_for_status()
    return parse(response.text)
```

Replace `collect/sources/__init__.py` with:

```python
"""Importing this package registers every source with collect.registry."""
from collect.sources import apnic  # noqa: F401
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_apnic.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add collect/sources/ tests/test_apnic.py tests/fixtures/apnic/
git commit -m "Add APNIC source for world, regional and per-economy IPv6 capability"
```

---

### Task 4: Potaroo BGP table source

**Files:**
- Create: `collect/sources/bgp.py`, `tests/fixtures/bgp/bgp-active.txt`, `tests/test_bgp.py`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Consumes: `source`, `DAY`, `Context`; `make_ctx`, `FakeResponse`.
- Produces: source key `"bgp_v6_table"` (TTL `DAY`); `collect.sources.bgp.parse(text: str, min_days: int = MIN_DAYS) -> dict`; `URL`, `PAGE`. Payload:
  `{"daily": [{"date": "YYYY-MM-DD", "prefixes": int}] (ascending), "current": int, "current_at": ISO str, "url": PAGE}`.

- [ ] **Step 1: Record the fixture (one sample per day, last ~800 days)**

Run: `mkdir -p tests/fixtures/bgp && curl -s https://bgp.potaroo.net/v6/as2.0/bgp-active.txt | awk 'NR % 24 == 0' | tail -n 800 > tests/fixtures/bgp/bgp-active.txt && wc -l tests/fixtures/bgp/bgp-active.txt`
Expected: `800 tests/fixtures/bgp/bgp-active.txt`.

- [ ] **Step 2: Write the failing tests** — `tests/test_bgp.py`:

```python
from pathlib import Path

import pytest

from collect.registry import DAY, SOURCES
from collect.sources import bgp
from tests.fakes import FakeResponse, make_ctx

FIXTURE = Path(__file__).parent / "fixtures" / "bgp" / "bgp-active.txt"

# 1791936000 = 2026-10-14T00:00Z, 1791979200 = 2026-10-14T12:00Z, 1792022400 = 2026-10-15T00:00Z
SAMPLE = """1791979200 258100
1791936000 258000
not a data line
1792022400 258600
"""


def test_parse_keeps_last_sample_per_day_even_out_of_order():
    parsed = bgp.parse(SAMPLE, min_days=1)
    assert parsed["daily"] == [{"date": "2026-10-14", "prefixes": 258100},
                               {"date": "2026-10-15", "prefixes": 258600}]
    assert parsed["current"] == 258600
    assert parsed["current_at"] == "2026-10-15T00:00:00+00:00"
    assert parsed["url"] == bgp.PAGE


def test_parse_recorded_file():
    lines = [line.split() for line in FIXTURE.read_text().splitlines() if line.strip()]
    newest = max(lines, key=lambda parts: int(parts[0]))
    parsed = bgp.parse(FIXTURE.read_text())
    assert len(parsed["daily"]) >= 365
    assert parsed["current"] == int(newest[1])


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="Potaroo"):
        bgp.parse("<html>moved</html>")


def test_registered_daily():
    assert SOURCES["bgp_v6_table"].ttl_seconds == DAY


def test_fetch():
    ctx = make_ctx(routes={bgp.URL: FakeResponse(text=FIXTURE.read_text())})
    assert SOURCES["bgp_v6_table"].fetch(ctx)["current"] > 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_bgp.py -v`
Expected: FAIL with `ImportError: cannot import name 'bgp'`.

- [ ] **Step 4: Implement** — `collect/sources/bgp.py`:

```python
"""IPv6 BGP table size history from Geoff Huston's Potaroo reports."""
from datetime import datetime, timezone

from collect.registry import DAY, Context, source

URL = "https://bgp.potaroo.net/v6/as2.0/bgp-active.txt"  # "<unix time> <active entries>" hourly
PAGE = "https://bgp.potaroo.net/v6/as2.0/index.html"
MIN_DAYS = 365


def parse(text: str, min_days: int = MIN_DAYS) -> dict:
    latest_per_day: dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        ts, count = int(parts[0]), int(parts[1])
        day = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
        if day not in latest_per_day or ts > latest_per_day[day][0]:
            latest_per_day[day] = (ts, count)
    if len(latest_per_day) < min_days:
        raise ValueError(f"Potaroo file format changed: only {len(latest_per_day)} days parsed")
    daily = [{"date": day, "prefixes": count} for day, (_, count) in sorted(latest_per_day.items())]
    last_ts, last_count = latest_per_day[daily[-1]["date"]]
    return {"daily": daily, "current": last_count,
            "current_at": datetime.fromtimestamp(last_ts, timezone.utc).isoformat(timespec="seconds"),
            "url": PAGE}


@source("bgp_v6_table", DAY, title="Potaroo IPv6 BGP table report", url=PAGE)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)
```

Replace the import line in `collect/sources/__init__.py` with:

```python
from collect.sources import apnic, bgp  # noqa: F401
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_bgp.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add collect/sources/ tests/test_bgp.py tests/fixtures/bgp/
git commit -m "Add Potaroo IPv6 BGP table history source"
```

---

### Task 5: Cloudflare Radar IP-version source

**Files:**
- Create: `collect/sources/cloudflare.py`, `tests/test_cloudflare.py`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Consumes: `source`, `MONTH`, `Context`; `make_ctx`, `FakeResponse`.
- Produces: source key `"cloudflare_ip_version"` with `requires_env=("CLOUDFLARE_API_KEY",)`; `collect.sources.cloudflare.parse(body: dict) -> dict`; `API`, `PAGE`. Payload:
  `{"series": [{"t": str, "ipv6": float}], "latest_ipv6": float, "latest_ipv4": float, "url": PAGE}`.

- [ ] **Step 1: Write the failing tests** — `tests/test_cloudflare.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import cloudflare
from tests.fakes import FakeResponse, make_ctx

BODY = {
    "success": True,
    "result": {
        "serie_0": {
            "timestamps": ["2026-10-06T00:00:00Z", "2026-10-13T00:00:00Z"],
            "IPv4": ["62.1", "61.6"],
            "IPv6": ["37.9", "38.4"],
        }
    },
}


def test_parse_serie_0():
    assert cloudflare.parse(BODY) == {
        "series": [{"t": "2026-10-06T00:00:00Z", "ipv6": 37.9}, {"t": "2026-10-13T00:00:00Z", "ipv6": 38.4}],
        "latest_ipv6": 38.4,
        "latest_ipv4": 61.6,
        "url": cloudflare.PAGE,
    }


def test_parse_legacy_main_shape():
    body = {"success": True, "result": {"main": BODY["result"]["serie_0"]}}
    assert cloudflare.parse(body)["latest_ipv6"] == 38.4


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="unexpected Cloudflare response"):
        cloudflare.parse({"success": True, "result": {"something_else": {}}})


def test_rejects_api_error():
    with pytest.raises(ValueError, match="Cloudflare API error"):
        cloudflare.parse({"success": False, "errors": [{"message": "bad token"}]})


def test_requires_api_key():
    assert SOURCES["cloudflare_ip_version"].requires_env == ("CLOUDFLARE_API_KEY",)


def test_fetch_sends_bearer_token():
    ctx = make_ctx(routes={cloudflare.API: FakeResponse(json_data=BODY)}, env={"CLOUDFLARE_API_KEY": " tok "})
    assert SOURCES["cloudflare_ip_version"].fetch(ctx)["latest_ipv6"] == 38.4
    url, kwargs = ctx.session.calls[0]
    assert kwargs["headers"] == {"Authorization": "Bearer tok"}


def test_fetch_http_error_includes_body():
    ctx = make_ctx(routes={cloudflare.API: FakeResponse(status_code=400, text="dateRange invalid")},
                   env={"CLOUDFLARE_API_KEY": "tok"})
    with pytest.raises(ValueError, match="400.*dateRange invalid"):
        SOURCES["cloudflare_ip_version"].fetch(ctx)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cloudflare.py -v`
Expected: FAIL with `ImportError: cannot import name 'cloudflare'`.

- [ ] **Step 3: Implement** — `collect/sources/cloudflare.py`:

```python
"""Cloudflare Radar: share of HTTP requests over IPv6, 52 weeks of history."""
from collect.registry import MONTH, Context, source

API = "https://api.cloudflare.com/client/v4/radar/http/timeseries_groups/ip_version?dateRange=52w"
PAGE = "https://radar.cloudflare.com/adoption-and-usage"


def parse(body: dict) -> dict:
    if not body.get("success"):
        raise ValueError(f"Cloudflare API error: {body.get('errors')}")
    result = body.get("result") or {}
    # Current shape is result.serie_0; older responses used result.main or top level.
    series = result.get("serie_0") or result.get("main") or (result if "IPv6" in result else None)
    if not series:
        raise ValueError(f"unexpected Cloudflare response keys: {sorted(result)}")
    stamps, ipv6, ipv4 = series["timestamps"], series["IPv6"], series["IPv4"]
    if not ipv6 or len(stamps) != len(ipv6):
        raise ValueError("unexpected Cloudflare response: empty or mismatched series")
    return {
        "series": [{"t": t, "ipv6": round(float(v), 2)} for t, v in zip(stamps, ipv6)],
        "latest_ipv6": round(float(ipv6[-1]), 2),
        "latest_ipv4": round(float(ipv4[-1]), 2),
        "url": PAGE,
    }


@source("cloudflare_ip_version", MONTH, title="Cloudflare Radar HTTP traffic by IP version",
        url=PAGE, requires_env=("CLOUDFLARE_API_KEY",))
def fetch(ctx: Context) -> dict:
    token = ctx.env["CLOUDFLARE_API_KEY"].strip()
    response = ctx.session.get(API, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if not response.ok:
        raise ValueError(f"Cloudflare API HTTP {response.status_code}: {response.text[:300]}")
    return parse(response.json())
```

Replace the import line in `collect/sources/__init__.py` with:

```python
from collect.sources import apnic, bgp, cloudflare  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cloudflare.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add collect/sources/ tests/test_cloudflare.py
git commit -m "Add Cloudflare Radar IP-version source"
```

---

### Task 6: Tranco top-1000 AAAA measurement source

**Files:**
- Create: `collect/sources/tranco.py`, `tests/test_tranco.py`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Consumes: `source`, `MONTH`, `Context` (its `has_aaaa`); `make_ctx(aaaa=...)`, `FakeResponse`.
- Produces: source key `"tranco_aaaa"`; `top_domains(zip_bytes: bytes, n: int) -> list[str]`, `has_ipv6(domain: str, has_aaaa) -> bool`, `measure(domains: list[str], has_aaaa) -> dict`; `LIST_URL`, `TOP_N = 1000`, `SHOW_N = 100`. Payload:
  `{"checked": int, "with_aaaa": int, "percentage": float (1 dp), "top": [{"rank": int, "domain": str, "aaaa": bool}] (first 100), "list_url": "https://tranco-list.eu/"}`.

- [ ] **Step 1: Write the failing tests** — `tests/test_tranco.py`:

```python
import io
import zipfile

import pytest

from collect.registry import SOURCES
from collect.sources import tranco
from tests.fakes import FakeResponse, make_ctx


def make_zip(rows):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("top-1m.csv", "".join(f"{rank},{domain}\n" for rank, domain in rows))
    return buffer.getvalue()


def test_top_domains_reads_first_n():
    data = make_zip([(1, "google.com"), (2, "example.org"), (3, "www.foo.net")])
    assert tranco.top_domains(data, 2) == ["google.com", "example.org"]


def test_has_ipv6_checks_apex_then_www():
    names = {"google.com", "www.example.org"}
    has = names.__contains__
    assert tranco.has_ipv6("google.com", has)
    assert tranco.has_ipv6("example.org", has)
    assert not tranco.has_ipv6("www.foo.net", has)  # no "www.www.foo.net" lookup


def test_measure_counts_and_rounds():
    result = tranco.measure(["google.com", "example.org", "www.foo.net"],
                            {"google.com", "www.example.org"}.__contains__)
    assert result["checked"] == 3
    assert result["with_aaaa"] == 2
    assert result["percentage"] == 66.7
    assert result["top"][2] == {"rank": 3, "domain": "www.foo.net", "aaaa": False}


def test_measure_rejects_zero_as_broken_dns():
    with pytest.raises(ValueError, match="DNS"):
        tranco.measure(["a.com", "b.com"], lambda name: False)


def test_rejects_changed_format():
    # A list shorter than TOP_N means the download is not the real list.
    ctx = make_ctx(routes={tranco.LIST_URL: FakeResponse(content=make_zip([(1, "a.com")]))}, aaaa={"a.com"})
    with pytest.raises(ValueError, match="only 1 domains"):
        SOURCES["tranco_aaaa"].fetch(ctx)


def test_fetch_full_list(monkeypatch):
    monkeypatch.setattr(tranco, "TOP_N", 3)
    rows = [(1, "google.com"), (2, "example.org"), (3, "www.foo.net"), (4, "ignored.com")]
    ctx = make_ctx(routes={tranco.LIST_URL: FakeResponse(content=make_zip(rows))},
                   aaaa={"google.com", "www.example.org", "ignored.com"})
    assert SOURCES["tranco_aaaa"].fetch(ctx)["with_aaaa"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tranco.py -v`
Expected: FAIL with `ImportError: cannot import name 'tranco'`.

- [ ] **Step 3: Implement** — `collect/sources/tranco.py`:

```python
"""Share of the Tranco top sites that publish AAAA records (apex or www), measured by us."""
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from collect.registry import MONTH, Context, source

LIST_URL = "https://tranco-list.eu/top-1m.csv.zip"
HOME = "https://tranco-list.eu/"
TOP_N = 1000
SHOW_N = 100
WORKERS = 32


def top_domains(zip_bytes: bytes, n: int) -> list[str]:
    domains: list[str] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                _, _, domain = line.strip().partition(",")
                if domain:
                    domains.append(domain)
                if len(domains) == n:
                    break
    return domains


def has_ipv6(domain: str, has_aaaa: Callable[[str], bool]) -> bool:
    if has_aaaa(domain):
        return True
    return not domain.startswith("www.") and has_aaaa(f"www.{domain}")


def measure(domains: list[str], has_aaaa: Callable[[str], bool]) -> dict:
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        flags = list(pool.map(lambda d: has_ipv6(d, has_aaaa), domains))
    with_aaaa = sum(flags)
    if with_aaaa == 0:
        raise ValueError("no domain has an AAAA record; DNS resolution is probably broken")
    return {
        "checked": len(domains),
        "with_aaaa": with_aaaa,
        "percentage": round(100 * with_aaaa / len(domains), 1),
        "top": [{"rank": i + 1, "domain": d, "aaaa": f}
                for i, (d, f) in enumerate(zip(domains[:SHOW_N], flags))],
        "list_url": HOME,
    }


@source("tranco_aaaa", MONTH, title="Tranco top sites, AAAA lookups (measured)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(LIST_URL, timeout=120)
    response.raise_for_status()
    domains = top_domains(response.content, TOP_N)
    if len(domains) < TOP_N:
        raise ValueError(f"Tranco list has only {len(domains)} domains")
    return measure(domains, ctx.has_aaaa)
```

Replace the import line in `collect/sources/__init__.py` with:

```python
from collect.sources import apnic, bgp, cloudflare, tranco  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tranco.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add collect/sources/ tests/test_tranco.py
git commit -m "Add Tranco top-1000 AAAA measurement source"
```

---

### Task 7: LACNIC/AFRINIC delegation sources and opt-in ISOC Pulse source

**Files:**
- Create: `collect/sources/rir.py`, `collect/sources/isoc.py`, `tests/test_rir.py`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Consumes: `source`, `MONTH`, `Context`; `make_ctx`, `FakeResponse`.
- Produces: source keys `"lacnic_delegations"`, `"afrinic_delegations"`, `"isoc_pulse"` (`requires_env=("ISOC_PULSE_API_KEY",)`); `collect.sources.rir.parse_delegations(text: str, registry: str, url: str) -> dict`; `LACNIC_URL`, `AFRINIC_URL`. Payload:
  `{"file_date": "YYYY-MM-DD", "total_blocks_32": float, "countries": int, "top_countries": [{"code": str, "blocks_32": float, "share": float}] (top 10), "url": str}`.

- [ ] **Step 1: Write the failing tests** — `tests/test_rir.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import rir
from tests.fakes import FakeResponse, make_ctx

SAMPLE = """# comment line
2|lacnic|20261013|50084|19870101|20261013|-0300
lacnic|*|ipv6|*|13570|summary
lacnic|MX|ipv6|2001:1200::|32|20030110|allocated
lacnic|MX|ipv6|2001:1201::|44|20190404|assigned
lacnic|BR|ipv6|2804::|29|20100101|allocated
lacnic|BR|ipv6|2804:8::|32|20100101|reserved
lacnic|GT|ipv4|2.152.0.0|1024|20260714|allocated
"""


def test_parse_counts_32_equivalents():
    parsed = rir.parse_delegations(SAMPLE, "lacnic", rir.LACNIC_URL)
    assert parsed["file_date"] == "2026-10-13"
    assert parsed["total_blocks_32"] == 9.0  # 8 (/29) + 1 (/32) + 1/4096 (/44)
    assert parsed["countries"] == 2
    assert parsed["top_countries"][0] == {"code": "BR", "blocks_32": 8.0, "share": 88.89}
    assert parsed["top_countries"][1]["code"] == "MX"
    assert parsed["url"] == rir.LACNIC_URL


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="lacnic delegation file format changed"):
        rir.parse_delegations("<html>not found</html>", "lacnic", rir.LACNIC_URL)


def test_fetch_afrinic():
    text = "2|afrinic|20261014|10025|00000000|20261014|00000\nafrinic|ZA|ipv6|2c0f::|32|20100101|allocated\n"
    ctx = make_ctx(routes={rir.AFRINIC_URL: FakeResponse(text=text)})
    parsed = SOURCES["afrinic_delegations"].fetch(ctx)
    assert parsed["file_date"] == "2026-10-14"
    assert parsed["countries"] == 1


def test_isoc_is_opt_in():
    assert SOURCES["isoc_pulse"].requires_env == ("ISOC_PULSE_API_KEY",)


def test_isoc_with_key_reports_missing_client():
    with pytest.raises(NotImplementedError, match="ISOC Pulse API client"):
        SOURCES["isoc_pulse"].fetch(make_ctx(env={"ISOC_PULSE_API_KEY": "k"}))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_rir.py -v`
Expected: FAIL with `ImportError: cannot import name 'rir'`.

- [ ] **Step 3: Implement** — `collect/sources/rir.py`:

```python
"""IPv6 allocations from the LACNIC and AFRINIC delegation files, in /32 equivalents."""
from collect.registry import MONTH, Context, source

LACNIC_URL = "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest"
AFRINIC_URL = "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest"
UNIT = 32
COUNTED = {"allocated", "assigned"}
TOP_N = 10


def parse_delegations(text: str, registry: str, url: str) -> dict:
    # Header: version|registry|serial(YYYYMMDD)|records|startdate|enddate|UTCoffset
    # Records: registry|cc|type|start|value|date|status
    file_date, per_country, total = None, {}, 0.0
    for line in text.splitlines():
        parts = line.strip().split("|")
        if file_date is None and len(parts) >= 3 and parts[1] == registry and parts[0][:1].isdigit():
            serial = parts[2]
            file_date = f"{serial[:4]}-{serial[4:6]}-{serial[6:8]}"
            continue
        if (len(parts) < 7 or parts[0] != registry or parts[2] != "ipv6"
                or parts[1] == "*" or parts[6] not in COUNTED):
            continue
        blocks = 2.0 ** (UNIT - int(parts[4]))
        per_country[parts[1]] = per_country.get(parts[1], 0.0) + blocks
        total += blocks
    if file_date is None or not per_country:
        raise ValueError(f"{registry} delegation file format changed")
    top = sorted(per_country.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    return {
        "file_date": file_date,
        "total_blocks_32": round(total, 2),
        "countries": len(per_country),
        "top_countries": [{"code": cc, "blocks_32": round(b, 2), "share": round(100 * b / total, 2)}
                          for cc, b in top],
        "url": url,
    }


def _fetch(ctx: Context, registry: str, url: str) -> dict:
    response = ctx.session.get(url, timeout=60)
    response.raise_for_status()
    return parse_delegations(response.text, registry, url)


@source("lacnic_delegations", MONTH, title="LACNIC delegation file", url=LACNIC_URL)
def fetch_lacnic(ctx: Context) -> dict:
    return _fetch(ctx, "lacnic", LACNIC_URL)


@source("afrinic_delegations", MONTH, title="AFRINIC delegation file", url=AFRINIC_URL)
def fetch_afrinic(ctx: Context) -> dict:
    return _fetch(ctx, "afrinic", AFRINIC_URL)
```

`collect/sources/isoc.py`:

```python
"""Internet Society Pulse (opt-in). Needs an account and API key.

Without ISOC_PULSE_API_KEY the runner marks this source "not configured" and never
calls fetch(). The API client is written once the owner has a key (spec Amendment 1,
Follow-ups).
"""
from collect.registry import MONTH, Context, source


@source("isoc_pulse", MONTH, title="Internet Society Pulse API (opt-in)",
        url="https://pulse.internetsociety.org/en/api/", requires_env=("ISOC_PULSE_API_KEY",))
def fetch(ctx: Context) -> dict:
    raise NotImplementedError("ISOC Pulse API client not written yet; see spec Amendment 1, Follow-ups")
```

Replace the import line in `collect/sources/__init__.py` with:

```python
from collect.sources import apnic, bgp, cloudflare, isoc, rir, tranco  # noqa: F401
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_rir.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add collect/sources/ tests/test_rir.py
git commit -m "Add LACNIC/AFRINIC delegation sources and opt-in ISOC Pulse source"
```

---

### Task 8: Datum, data loading and derived values

**Files:**
- Create: `web/__init__.py`, `web/data.py`, `web/derive.py`, `tests/sample_data.py`, `tests/test_data.py`, `tests/test_derive.py`

**Interfaces:**
- Consumes: `collect.manifest.load/save`, `SOURCES`, `DAY` (Tasks 1–2); all source keys and payload shapes (Tasks 3–7).
- Produces:
  - `web.data.Datum(value, sources: tuple[str, ...], fetched_at: datetime, stale: bool)`; `combine(value, inputs) -> Datum`; `Data(data_dir: Path, now: datetime)` with `.payload(key) -> dict | None`, `.datum(key, pick) -> Datum | None`, `.is_stale(key) -> bool`, `.status_rows() -> list[dict]` (keys: `key, title, url, status, error, last_success, last_attempt, ttl_days, stale`); `STALE_FACTOR = 2`.
  - `web.derive`: `MIN_SAMPLES = 100_000`; `consensus_components(data) -> list[tuple[str, Datum | None]]`; `consensus(components) -> Datum | None`; `bgp_current(data)`, `bgp_change(data, days: int)`, `economies_above(data, threshold: float)`, `economies_considered(data)`, `top_economy(data)`, `economy(data, code: str)`, `regions(data)`, each `-> Datum | None`.
  - `tests.sample_data`: `NOW`, `FETCHED`, `PAYLOADS`, `write_sample_data(data_dir, omit=(), last_success=None) -> Path`.

- [ ] **Step 1: Write the sample data helper** — `tests/sample_data.py`:

```python
"""A complete, realistic data directory for web tests."""
import json
from datetime import datetime, timezone
from pathlib import Path

import collect.sources  # noqa: F401  (registers sources)
from collect.manifest import save
from collect.registry import SOURCES

NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)
FETCHED = "2026-10-14T00:05:00+00:00"

PAYLOADS = {
    "apnic": {
        "world": {"code": "XA", "name": "World", "capable": 43.6, "preferred": 41.0, "samples": 972331706},
        "regions": [
            {"code": "XC", "name": "Americas", "capable": 51.0, "preferred": 49.6, "samples": 171761189},
            {"code": "XE", "name": "Europe", "capable": 36.9, "preferred": 35.7, "samples": 134455991},
            {"code": "XG", "name": "Unclassified", "capable": 1.9, "preferred": 1.7, "samples": 16151},
        ],
        "economies": [
            {"code": "BL", "name": "Saint Barthelemy", "capable": 97.1, "preferred": 90.0, "samples": 2000},
            {"code": "DE", "name": "Germany", "capable": 49.5, "preferred": 48.0, "samples": 30000000},
            {"code": "FR", "name": "France", "capable": 85.6, "preferred": 80.0, "samples": 20000000},
            {"code": "US", "name": "United States of America", "capable": 61.9, "preferred": 59.9,
             "samples": 97679957},
        ],
        "url": "https://stats.labs.apnic.net/ipv6/",
    },
    "bgp_v6_table": {
        "daily": [
            {"date": "2025-10-01", "prefixes": 230000},
            {"date": "2025-10-14", "prefixes": 231000},
            {"date": "2026-09-14", "prefixes": 255000},
            {"date": "2026-10-14", "prefixes": 258009},
        ],
        "current": 258009,
        "current_at": "2026-10-14T00:00:00+00:00",
        "url": "https://bgp.potaroo.net/v6/as2.0/index.html",
    },
    "cloudflare_ip_version": {
        "series": [{"t": "2026-10-06T00:00:00Z", "ipv6": 37.9}, {"t": "2026-10-13T00:00:00Z", "ipv6": 38.4}],
        "latest_ipv6": 38.4,
        "latest_ipv4": 61.6,
        "url": "https://radar.cloudflare.com/adoption-and-usage",
    },
    "tranco_aaaa": {
        "checked": 1000, "with_aaaa": 612, "percentage": 61.2,
        "top": [{"rank": 1, "domain": "google.com", "aaaa": True}],
        "list_url": "https://tranco-list.eu/",
    },
    "lacnic_delegations": {
        "file_date": "2026-10-13", "total_blocks_32": 31250.0, "countries": 33,
        "top_countries": [{"code": "BR", "blocks_32": 20000.0, "share": 64.0}],
        "url": "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
    },
    "afrinic_delegations": {
        "file_date": "2026-10-14", "total_blocks_32": 11300.0, "countries": 54,
        "top_countries": [{"code": "ZA", "blocks_32": 2500.0, "share": 22.1}],
        "url": "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest",
    },
}


def write_sample_data(data_dir: Path, omit=(), last_success=None) -> Path:
    """Write PAYLOADS and a manifest. Keys in `omit` are recorded as failed;
    `last_success` maps key -> ISO time to override FETCHED (for staleness)."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    overrides = last_success or {}
    manifest = {}
    for key, src in SOURCES.items():
        if key.startswith("test_"):
            continue
        entry = {"ttl_seconds": src.ttl_seconds, "last_attempt": FETCHED}
        if key not in PAYLOADS and src.requires_env:
            entry.update(status="not_configured", error=f"set {', '.join(src.requires_env)} to enable")
        elif key in omit or key not in PAYLOADS:
            entry.update(status="error", error="ConnectionError: sample failure")
        else:
            (data_dir / f"{key}.json").write_text(json.dumps(PAYLOADS[key]))
            entry.update(status="ok", error=None, last_success=overrides.get(key, FETCHED))
        manifest[key] = entry
    save(data_dir, manifest)
    return data_dir
```

- [ ] **Step 2: Write the failing tests** — `tests/test_data.py`:

```python
from datetime import datetime, timezone

import pytest

from tests.sample_data import NOW, write_sample_data
from web.data import Data, Datum, combine


def test_datum_carries_provenance(tmp_path):
    data = Data(write_sample_data(tmp_path), NOW)
    d = data.datum("apnic", lambda p: p["world"]["capable"])
    assert d == Datum(43.6, ("apnic",), datetime(2026, 10, 14, 0, 5, tzinfo=timezone.utc), False)


def test_failed_source_gives_none(tmp_path):
    data = Data(write_sample_data(tmp_path, omit=("apnic",)), NOW)
    assert data.datum("apnic", lambda p: p["world"]["capable"]) is None


def test_pick_returning_none_gives_none(tmp_path):
    data = Data(write_sample_data(tmp_path), NOW)
    assert data.datum("apnic", lambda p: None) is None


def test_unknown_source_raises(tmp_path):
    data = Data(write_sample_data(tmp_path), NOW)
    with pytest.raises(KeyError, match="unknown source"):
        data.datum("apnicc", lambda p: p)


def test_shape_mismatch_raises(tmp_path):
    data = Data(write_sample_data(tmp_path), NOW)
    with pytest.raises(ValueError, match="apnic.json"):
        data.datum("apnic", lambda p: p["no_such_field"])


def test_stale_after_twice_the_interval(tmp_path):
    data = Data(write_sample_data(tmp_path, last_success={"bgp_v6_table": "2026-10-11T00:05:00+00:00"}), NOW)
    assert data.datum("bgp_v6_table", lambda p: p["current"]).stale
    assert not data.datum("apnic", lambda p: p["world"]).stale


def test_combine_merges_provenance():
    old = datetime(2026, 10, 1, tzinfo=timezone.utc)
    new = datetime(2026, 10, 14, tzinfo=timezone.utc)
    merged = combine(5, [Datum(1, ("b",), new, False), Datum(2, ("a",), old, True)])
    assert merged == Datum(5, ("a", "b"), old, True)


def test_status_rows(tmp_path):
    rows = {r["key"]: r for r in Data(write_sample_data(tmp_path), NOW).status_rows()}
    assert rows["isoc_pulse"]["status"] == "not_configured"
    assert "ISOC_PULSE_API_KEY" in rows["isoc_pulse"]["error"]
    assert rows["bgp_v6_table"]["ttl_days"] == 1
    assert rows["apnic"]["ttl_days"] == 30
    assert rows["apnic"]["status"] == "ok"


def test_missing_data_dir_has_no_data(tmp_path):
    data = Data(tmp_path / "does-not-exist", NOW)
    assert data.datum("apnic", lambda p: p) is None
    assert all(r["status"] == "never run" for r in data.status_rows())
```

`tests/test_derive.py`:

```python
from tests.sample_data import NOW, write_sample_data
from web import derive
from web.data import Data


def data(tmp_path, **kwargs):
    return Data(write_sample_data(tmp_path, **kwargs), NOW)


def test_consensus_of_three_sources(tmp_path):
    d = derive.consensus(derive.consensus_components(data(tmp_path)))
    assert d.value == 47.7  # (43.6 + 38.4 + 61.2) / 3
    assert d.sources == ("apnic", "cloudflare_ip_version", "tranco_aaaa")


def test_consensus_skips_missing_component(tmp_path):
    components = derive.consensus_components(data(tmp_path, omit=("cloudflare_ip_version",)))
    assert [d is None for _, d in components] == [False, True, False]
    assert derive.consensus(components).value == 52.4  # (43.6 + 61.2) / 2


def test_consensus_none_without_sources(tmp_path):
    d = data(tmp_path, omit=("apnic", "cloudflare_ip_version", "tranco_aaaa"))
    assert derive.consensus(derive.consensus_components(d)) is None


def test_bgp_values(tmp_path):
    d = data(tmp_path)
    assert derive.bgp_current(d).value == 258009
    assert derive.bgp_change(d, 365).value == 27009  # vs 2025-10-14
    assert derive.bgp_change(d, 30).value == 3009    # vs 2026-09-14
    assert derive.bgp_change(d, 4000) is None        # not enough history


def test_economy_rankings_ignore_small_samples(tmp_path):
    d = data(tmp_path)
    assert derive.economies_above(d, 50).value == 2   # FR, US; BL has too few samples
    assert derive.economies_considered(d).value == 3  # DE, FR, US
    assert derive.top_economy(d).value["name"] == "France"
    assert derive.economy(d, "US").value["capable"] == 61.9
    assert derive.economy(d, "ZZ") is None


def test_regions_sorted_without_unclassified(tmp_path):
    assert [r["name"] for r in derive.regions(data(tmp_path)).value] == ["Americas", "Europe"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_data.py tests/test_derive.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'web'`.

- [ ] **Step 4: Implement** — `web/__init__.py` (empty file), `web/data.py`:

```python
"""Read collected JSON and hand pages Datum objects that carry provenance."""
from __future__ import annotations

import json
from dataclasses import dataclass
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
            ok = self.manifest.get(key, {}).get("last_success") and path.exists()
            self._payloads[key] = json.loads(path.read_text()) if ok else None
        return self._payloads[key]

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
                "status": entry.get("status", "never run"), "error": entry.get("error"),
                "last_success": entry.get("last_success"), "last_attempt": entry.get("last_attempt"),
                "ttl_days": src.ttl_seconds // DAY,
                "stale": bool(entry.get("last_success")) and self.is_stale(key),
            })
        return rows
```

`web/derive.py`:

```python
"""Values computed at build time from collected data. Each returns a Datum or None."""
from __future__ import annotations

from datetime import date, timedelta

from web.data import Data, Datum, combine

MIN_SAMPLES = 100_000  # APNIC economies with fewer samples are left out of rankings
UNCLASSIFIED = "Unclassified"

CONSENSUS_INPUTS = (
    ("APNIC: users IPv6-capable", "apnic", lambda p: p["world"]["capable"]),
    ("Cloudflare: HTTP requests over IPv6", "cloudflare_ip_version", lambda p: p["latest_ipv6"]),
    ("Tranco top 1000: sites with AAAA", "tranco_aaaa", lambda p: p["percentage"]),
)


def consensus_components(data: Data) -> list[tuple[str, Datum | None]]:
    return [(label, data.datum(key, pick)) for label, key, pick in CONSENSUS_INPUTS]


def consensus(components: list[tuple[str, Datum | None]]) -> Datum | None:
    present = [d for _, d in components if d is not None]
    if not present:
        return None
    return combine(round(sum(d.value for d in present) / len(present), 1), present)


def bgp_current(data: Data) -> Datum | None:
    return data.datum("bgp_v6_table", lambda p: p["current"])


def bgp_change(data: Data, days: int) -> Datum | None:
    def pick(p):
        cutoff = date.fromisoformat(p["daily"][-1]["date"]) - timedelta(days=days)
        earlier = [d for d in p["daily"] if date.fromisoformat(d["date"]) <= cutoff]
        return p["current"] - earlier[-1]["prefixes"] if earlier else None

    return data.datum("bgp_v6_table", pick)


def _ranked(p: dict) -> list[dict]:
    return [e for e in p["economies"] if e["samples"] >= MIN_SAMPLES]


def economies_above(data: Data, threshold: float) -> Datum | None:
    return data.datum("apnic", lambda p: sum(1 for e in _ranked(p) if e["capable"] >= threshold))


def economies_considered(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: len(_ranked(p)))


def top_economy(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: max(_ranked(p), key=lambda e: e["capable"], default=None))


def economy(data: Data, code: str) -> Datum | None:
    return data.datum("apnic", lambda p: next((e for e in p["economies"] if e["code"] == code), None))


def regions(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: sorted(
        (r for r in p["regions"] if r["name"] != UNCLASSIFIED), key=lambda r: r["capable"], reverse=True))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_data.py tests/test_derive.py -v`
Expected: 15 passed.

- [ ] **Step 6: Commit**

```bash
git add web/ tests/sample_data.py tests/test_data.py tests/test_derive.py
git commit -m "Add Datum loading with provenance and staleness, plus derived values"
```

---

### Task 9: Site build, templates and static assets

**Files:**
- Create: `web/format.py`, `web/charts.py`, `web/build.py`, `web/pages/__init__.py`, `web/pages/overview.py` (minimal; replaced in Task 10), `web/templates/base.html`, `web/templates/macros.html`, `web/templates/overview.html` (minimal; replaced in Task 10), `web/static/site.css`, `web/static/theme.js`, `web/static/legacy-redirect.js`, `tests/test_build.py`

**Interfaces:**
- Consumes: `Data`, `Datum`, `derive.*` (Task 8); `SOURCES` (Task 1); `tests.sample_data` (Task 8).
- Produces: `web.format.format_value(value, fmt: str) -> str` (fmt ∈ `"int"`, `"signed_int"`, `"pct"`, `"pct_points"`, `"text"`), `provenance_text(d: Datum) -> str`, `date_only(iso: str | None) -> str`; `web.charts.line_chart(d: Datum | None, *, x: str, y: str, title: str, y_title: str) -> Markup | None`; `web.build.Page(slug, title, context)`, `PAGES`, `LEGACY_PAGES: dict[str, str]`, `build(data_dir: Path, out_dir: Path, now: datetime) -> list[str]` (returns warnings), `check_reference_dates(templates_dir: Path, now: datetime, max_age_days: int = 180) -> list[str]`, `main(argv=None) -> int`. Templates: macros `metric(label, d, fmt, note=None)`, `provenance(d)`, `unavailable()`, `reference(reviewed)`, `freshness_table(rows)`; base template variables `base`, `pages`, `current`, `page_title`, `built_at`, optional `legacy_pages`.

- [ ] **Step 1: Write the failing tests** — `tests/test_build.py`:

```python
import re
from datetime import datetime, timezone

from tests.sample_data import NOW, write_sample_data
from web.build import build, check_reference_dates

LINK = re.compile(r'(?:href|src)="([^"]*)"')


def built(tmp_path):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data"), out, NOW)
    return out


def test_build_writes_pages_and_assets(tmp_path):
    out = built(tmp_path)
    for rel in ["index.html", "overview/index.html", "static/site.css", "static/theme.js",
                "static/legacy-redirect.js", "static/plotly.min.js"]:
        assert (out / rel).is_file(), rel
    assert (out / "static" / "plotly.min.js").stat().st_size > 1_000_000


def test_internal_links_are_relative_and_resolve(tmp_path):
    out = built(tmp_path)
    for page in out.rglob("*.html"):
        for link in LINK.findall(page.read_text()):
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            assert not link.startswith("/"), f"{page}: {link} breaks the /ipv6stats/ preview"
            target = (page.parent / link.split("#")[0]).resolve()
            if target.is_dir():
                target = target / "index.html"
            assert target.is_file(), f"{page}: broken link {link}"


def test_root_page_carries_legacy_redirect(tmp_path):
    out = built(tmp_path)
    root = (out / "index.html").read_text()
    assert 'id="legacy-pages"' in root
    assert '"Combined View": "overview/"' in root
    assert 'id="legacy-pages"' not in (out / "overview" / "index.html").read_text()


def test_footer_shows_build_time(tmp_path):
    html = (built(tmp_path) / "overview" / "index.html").read_text()
    assert "Data refreshed daily at 00:00 UTC · Last build: 2026-10-14 01:00 UTC" in html


def test_only_third_party_request_is_the_logo(tmp_path):
    html = (built(tmp_path) / "overview" / "index.html").read_text()
    srcs = re.findall(r'src="(https?://[^"]+)"', html)
    assert srcs == ["https://ipv6.army/images/v6.png"]


def test_reference_dates_warn_when_old(tmp_path):
    (tmp_path / "old.html").write_text('{% call reference(reviewed="2026-01-01") %}x{% endcall %}')
    (tmp_path / "new.html").write_text('{% call reference(reviewed="2026-09-01") %}x{% endcall %}')
    now = datetime(2026, 10, 14, tzinfo=timezone.utc)
    warnings = check_reference_dates(tmp_path, now)
    assert len(warnings) == 1 and "old.html" in warnings[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'web.build'`.

- [ ] **Step 3: Implement the Python modules** — `web/format.py`:

```python
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
```

`web/charts.py`:

```python
"""Plotly figures rendered as HTML fragments. plotly.min.js is loaded once by base.html."""
from __future__ import annotations

import plotly.graph_objects as go
from markupsafe import Markup

from web.data import Datum

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
        xaxis=dict(type="date", rangeselector=dict(buttons=RANGE_BUTTONS)),
    )
    return Markup(fig.to_html(full_html=False, include_plotlyjs=False,
                              config={"displaylogo": False, "responsive": True}))
```

`web/pages/__init__.py` (empty file). Minimal `web/pages/overview.py` (Task 10 replaces it):

```python
"""Overview page."""
from web import derive
from web.data import Data


def context(data: Data) -> dict:
    return {"consensus": derive.consensus(derive.consensus_components(data))}
```

`web/build.py`:

```python
"""Render the static site from data/*.json into dist/.

Usage: python -m web.build [--data-dir data] [--out dist]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from plotly.offline import get_plotlyjs

from web.data import Data
from web.format import date_only, format_value, provenance_text
from web.pages import overview

HERE = Path(__file__).parent
TEMPLATES = HERE / "templates"
STATIC = HERE / "static"
REFERENCE = re.compile(r'reference\(\s*reviewed\s*=\s*"(\d{4}-\d{2}-\d{2})"')


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    context: Callable[[Data], dict]


PAGES = (Page("overview", "Overview", overview.context),)

# Old Streamlit ?page= names -> new paths. Later plans add the remaining pages;
# names not listed here land on the Overview.
LEGACY_PAGES = {"Overview": "overview/", "Combined View": "overview/"}


def make_env() -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]),
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.filters["format_value"] = format_value
    env.filters["provenance_text"] = provenance_text
    env.filters["date_only"] = date_only
    return env


def check_reference_dates(templates_dir: Path, now: datetime, max_age_days: int = 180) -> list[str]:
    warnings = []
    for path in sorted(Path(templates_dir).rglob("*.html")):
        for match in REFERENCE.finditer(path.read_text()):
            reviewed = date.fromisoformat(match.group(1))
            age = (now.date() - reviewed).days
            if age > max_age_days:
                warnings.append(f"{path.name}: reference block last reviewed {reviewed} ({age} days ago)")
    return warnings


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(data_dir: Path, out_dir: Path, now: datetime) -> list[str]:
    data = Data(data_dir, now)
    env = make_env()
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(STATIC, out_dir / "static")
    (out_dir / "static" / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")

    common = {"pages": PAGES, "built_at": now.strftime("%Y-%m-%d %H:%M UTC"),
              "freshness": data.status_rows()}
    for page in PAGES:
        context = {**common, **page.context(data), "page_title": page.title, "current": page.slug}
        template = env.get_template(f"{page.slug}.html")
        _write(out_dir / page.slug / "index.html", template.render(context, base="../"))
        if page.slug == "overview":
            _write(out_dir / "index.html", template.render(context, base="", legacy_pages=LEGACY_PAGES))
    return check_reference_dates(TEMPLATES, now)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--out", default="dist")
    args = parser.parse_args(argv)
    for warning in build(Path(args.data_dir), Path(args.out), datetime.now(timezone.utc)):
        print(f"::warning::{warning}")
    print(f"Built site into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implement the templates** — `web/templates/base.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ page_title }} · IPv6 Global Statistics</title>
<link rel="stylesheet" href="{{ base }}static/site.css">
<script src="{{ base }}static/theme.js"></script>
<script src="{{ base }}static/plotly.min.js"></script>
{% if legacy_pages is defined %}
<script type="application/json" id="legacy-pages">{{ legacy_pages | tojson }}</script>
<script src="{{ base }}static/legacy-redirect.js"></script>
{% endif %}
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="{{ base or './' }}"><img src="https://ipv6.army/images/v6.png" alt="" width="32" height="32">IPv6 Global Statistics</a>
    <nav class="site-nav" aria-label="Pages">
      {% for p in pages %}
      <a href="{{ base }}{{ p.slug }}/"{% if p.slug == current %} aria-current="page"{% endif %}>{{ p.title }}</a>
      {% endfor %}
    </nav>
    <div class="header-tools">
      <a href="https://ipv6compatibility.com/">IPv6 Compatibility Database</a>
      <a href="https://tools.forwardingplane.net">IPv6 Tools</a>
      <a href="https://www.ipv6.army">IPv6 Tests</a>
      <button id="theme-toggle" type="button">Toggle theme</button>
    </div>
  </div>
</header>
<main>
{% block content %}{% endblock %}
</main>
<footer class="site-footer">
  Data refreshed daily at 00:00 UTC · Last build: {{ built_at }} · <a href="https://github.com/buraglio/ipv6stats">Source code</a>
</footer>
</body>
</html>
```

`web/templates/macros.html`:

```html
{% macro provenance(d) -%}
{% if d %}<div class="provenance">{{ d | provenance_text }}{% if d.stale %} · <span class="stale">⚠ stale since {{ d.fetched_at.date().isoformat() }}</span>{% endif %}</div>{% endif %}
{%- endmacro %}

{% macro unavailable() -%}
<p class="missing">— source unavailable</p>
{%- endmacro %}

{% macro metric(label, d, fmt, note=None) -%}
<div class="metric">
  <div class="metric-label">{{ label }}</div>
  {% if d is none %}
  <div class="metric-value missing">— source unavailable</div>
  {% else %}
  <div class="metric-value">{{ d.value | format_value(fmt) }}</div>
  {% if note %}<div class="metric-note">{{ note }}</div>{% endif %}
  {{ provenance(d) }}
  {% endif %}
</div>
{%- endmacro %}

{% macro reference(reviewed) -%}
<aside class="reference"><div class="provenance">Reference — last reviewed {{ reviewed }}</div>{{ caller() }}</aside>
{%- endmacro %}

{% macro freshness_table(rows) -%}
<div class="table-wrap">
<table>
  <thead><tr><th>Source</th><th>Status</th><th>Last success</th><th>Last attempt</th><th>Re-fetched every</th></tr></thead>
  <tbody>
  {% for r in rows %}
    <tr>
      <td><a href="{{ r.url }}">{{ r.title }}</a></td>
      <td class="status-{{ r.status | replace('_', '-') | replace(' ', '-') }}">{{ r.status | replace("_", " ") }}{% if r.stale %} <span class="stale">⚠ stale</span>{% endif %}{% if r.error %}<div class="provenance">{{ r.error }}</div>{% endif %}</td>
      <td>{{ r.last_success | date_only }}</td>
      <td>{{ r.last_attempt | date_only }}</td>
      <td>{{ r.ttl_days }} day{{ "s" if r.ttl_days != 1 else "" }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</div>
{%- endmacro %}
```

Minimal `web/templates/overview.html` (Task 10 replaces it):

```html
{% extends "base.html" %}
{% from "macros.html" import metric %}
{% block content %}
<h1>IPv6 Adoption Overview</h1>
<section class="metric-row">
  {{ metric("Global IPv6 adoption (consensus)", consensus, "pct") }}
</section>
{% endblock %}
```

- [ ] **Step 5: Implement the static assets** — `web/static/site.css`:

```css
:root {
  --bg: #f6f7f9; --surface: #ffffff; --text: #1d2330; --muted: #5b6475;
  --border: #d9dde5; --accent: #0b6bcb; --on-accent: #ffffff; --warn: #a15c00; --grid: #e3e6ec;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #11151c; --surface: #1a1f29; --text: #e6e9ef; --muted: #9aa3b2;
    --border: #2c3341; --accent: #5aa9ff; --on-accent: #0b1220; --warn: #f0b458; --grid: #2a303c;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #11151c; --surface: #1a1f29; --text: #e6e9ef; --muted: #9aa3b2;
  --border: #2c3341; --accent: #5aa9ff; --on-accent: #0b1220; --warn: #f0b458; --grid: #2a303c;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }
a { color: var(--accent); }
.site-header { background: var(--surface); border-bottom: 1px solid var(--border); }
.header-inner, main, .site-footer { max-width: 1200px; margin: 0 auto; padding-left: 16px; padding-right: 16px; }
.header-inner { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 24px; padding-top: 12px; padding-bottom: 12px; }
.brand { display: flex; align-items: center; gap: 10px; font-weight: 600; color: var(--text); text-decoration: none; }
.site-nav { display: flex; flex-wrap: wrap; gap: 4px 8px; }
.site-nav a { text-decoration: none; padding: 4px 10px; border-radius: 6px; color: var(--text); }
.site-nav a[aria-current="page"] { background: var(--accent); color: var(--on-accent); }
.header-tools { margin-left: auto; display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; font-size: 14px; }
#theme-toggle { font: inherit; padding: 4px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); cursor: pointer; }
main { padding-top: 24px; padding-bottom: 48px; }
h1 { font-size: 28px; margin: 0 0 16px; }
h2 { font-size: 21px; margin: 32px 0 12px; }
h3 { font-size: 17px; margin: 0 0 8px; }
.metric-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.metric, .card, details.source { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.metric-label { font-size: 14px; color: var(--muted); }
.metric-value { font-size: 28px; font-weight: 650; font-variant-numeric: tabular-nums; }
.metric-note { font-size: 14px; }
.provenance { font-size: 12.5px; color: var(--muted); margin-top: 6px; }
.stale { color: var(--warn); font-weight: 600; }
.missing { color: var(--muted); font-style: italic; }
.components { margin: 12px 0 0; padding-left: 20px; color: var(--muted); font-size: 14px; }
details.source { margin-bottom: 12px; }
details.source > summary { cursor: pointer; font-weight: 600; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
.status-error { color: var(--warn); }
.site-footer { padding-top: 16px; padding-bottom: 32px; color: var(--muted); font-size: 14px; border-top: 1px solid var(--border); }
```

`web/static/theme.js`:

```js
(function () {
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem("theme");
    if (saved) root.dataset.theme = saved;
  } catch (e) {}

  function current() {
    if (root.dataset.theme) return root.dataset.theme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function restyleCharts() {
    if (!window.Plotly) return;
    var css = getComputedStyle(root);
    var text = css.getPropertyValue("--text").trim();
    var grid = css.getPropertyValue("--grid").trim();
    document.querySelectorAll(".js-plotly-plot").forEach(function (el) {
      window.Plotly.relayout(el, { "font.color": text, "xaxis.gridcolor": grid, "yaxis.gridcolor": grid });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    restyleCharts();
    var button = document.getElementById("theme-toggle");
    if (!button) return;
    button.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) {}
      restyleCharts();
    });
  });
})();
```

`web/static/legacy-redirect.js`:

```js
(function () {
  var name = new URLSearchParams(window.location.search).get("page");
  if (!name) return;
  var map = JSON.parse(document.getElementById("legacy-pages").textContent);
  window.location.replace(map[name] || "overview/");
})();
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_build.py -v`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add web/ tests/test_build.py
git commit -m "Add static site build with templates, theme and legacy URL redirects"
```

---

### Task 10: Merged Overview page

**Files:**
- Modify: `web/pages/overview.py` (replace whole file), `web/templates/overview.html` (replace whole file)
- Create: `tests/test_overview.py`

**Interfaces:**
- Consumes: `Data.datum`, `Data.status_rows` (via `freshness` in the common context), all `derive.*`, `charts.line_chart`, macros `metric`, `provenance`, `unavailable`, `freshness_table` (Tasks 8–9).
- Produces: `web.pages.overview.context(data) -> dict` with keys `consensus, consensus_note, components, cf_ipv6, cf_ipv4, cf_chart, bgp_current, bgp_year, bgp_month, bgp_chart, sites, tranco, apnic_world, apnic_capable, above_threshold, above, considered, min_samples_label, top_economy, us, regions, lacnic, afrinic`; `ABOVE_THRESHOLD = 50`.

- [ ] **Step 1: Write the failing tests** — `tests/test_overview.py`:

```python
from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return (out / "overview" / "index.html").read_text()


def test_headline_numbers_come_from_data(tmp_path):
    html = render(tmp_path)
    assert '<div class="metric-value">47.7%</div>' in html      # consensus
    assert '<div class="metric-value">38.4%</div>' in html      # Cloudflare
    assert '<div class="metric-value">258,009</div>' in html    # BGP prefixes
    assert "+27,009 in the past year" in html
    assert '<div class="metric-value">61.2%</div>' in html      # Tranco sites
    assert "Economies ≥ 50% IPv6-capable" in html
    assert '<div class="metric-value">2</div>' in html
    assert "3 of 3 sources" in html


def test_removed_static_claims_are_gone(tmp_path):
    html = render(tmp_path)
    for text in ["228,789", "49%", "12%", "IPv6-only Support", "Facebook", "Mobile Leadership",
                 "US Milestone", "25+", "France (80%)", "13.2%"]:
        assert text not in html, text


def test_trends_use_ranked_economies_and_regions(tmp_path):
    html = render(tmp_path)
    assert "France" in html and "85.6%" in html
    assert "United States of America" in html and "61.9%" in html
    assert "Saint Barthelemy" not in html
    assert "Unclassified" not in html
    assert html.index("Americas") < html.index("Europe")


def test_updates_and_insights_are_generated(tmp_path):
    html = render(tmp_path)
    assert "+3,009" in html                      # BGP change in the last 30 days
    assert "31,250" in html and "2026-10-13" in html   # LACNIC total and file date
    assert "11,300" in html and "54 economies" in html  # AFRINIC
    assert "+17.6 points" in html                # Tranco 61.2 minus APNIC 43.6


def test_missing_source_shows_unavailable(tmp_path):
    html = render(tmp_path, omit=("cloudflare_ip_version",))
    assert "— source unavailable" in html
    assert '<div class="metric-value">52.4%</div>' in html
    assert "2 of 3 sources" in html


def test_empty_data_dir_still_builds(tmp_path):
    out = tmp_path / "dist"
    build(tmp_path / "no-data-yet", out, NOW)
    html = (out / "overview" / "index.html").read_text()
    assert html.count("— source unavailable") >= 5


def test_stale_source_is_marked(tmp_path):
    html = render(tmp_path, last_success={"bgp_v6_table": "2026-10-10T00:05:00+00:00"})
    assert "stale since 2026-10-10" in html


def test_freshness_table_lists_opt_in_source(tmp_path):
    html = render(tmp_path)
    assert "Internet Society Pulse API (opt-in)" in html
    assert "not configured" in html
    assert "ISOC_PULSE_API_KEY" in html


def test_charts_render(tmp_path):
    html = render(tmp_path)
    assert html.count("Plotly.newPlot") == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_overview.py -v`
Expected: FAIL (e.g. `test_headline_numbers_come_from_data` fails on the missing `38.4%`).

- [ ] **Step 3: Replace `web/pages/overview.py`**

```python
"""Overview page: the old Overview and Combined View merged, built only from collected data."""
from web import charts, derive
from web.data import Data

ABOVE_THRESHOLD = 50


def context(data: Data) -> dict:
    components = derive.consensus_components(data)
    present = sum(1 for _, d in components if d is not None)
    return {
        "consensus": derive.consensus(components),
        "consensus_note": f"{present} of {len(components)} sources",
        "components": components,
        "cf_ipv6": data.datum("cloudflare_ip_version", lambda p: p["latest_ipv6"]),
        "cf_ipv4": data.datum("cloudflare_ip_version", lambda p: p["latest_ipv4"]),
        "cf_chart": charts.line_chart(
            data.datum("cloudflare_ip_version", lambda p: p["series"]),
            x="t", y="ipv6", title="Cloudflare HTTP requests over IPv6", y_title="Percent"),
        "bgp_current": derive.bgp_current(data),
        "bgp_year": derive.bgp_change(data, 365),
        "bgp_month": derive.bgp_change(data, 30),
        "bgp_chart": charts.line_chart(
            data.datum("bgp_v6_table", lambda p: p["daily"]),
            x="date", y="prefixes", title="IPv6 BGP table size", y_title="Prefixes"),
        "sites": data.datum("tranco_aaaa", lambda p: p["percentage"]),
        "tranco": data.datum("tranco_aaaa", lambda p: p),
        "apnic_world": data.datum("apnic", lambda p: p["world"]),
        "apnic_capable": data.datum("apnic", lambda p: p["world"]["capable"]),
        "above_threshold": ABOVE_THRESHOLD,
        "above": derive.economies_above(data, ABOVE_THRESHOLD),
        "considered": derive.economies_considered(data),
        "min_samples_label": f"{derive.MIN_SAMPLES:,}",
        "top_economy": derive.top_economy(data),
        "us": derive.economy(data, "US"),
        "regions": derive.regions(data),
        "lacnic": data.datum("lacnic_delegations", lambda p: p),
        "afrinic": data.datum("afrinic_delegations", lambda p: p),
    }
```

- [ ] **Step 4: Replace `web/templates/overview.html`**

```html
{% extends "base.html" %}
{% from "macros.html" import metric, provenance, unavailable, freshness_table %}
{% block content %}
<h1>IPv6 Adoption Overview</h1>

<section class="metric-row" aria-label="Headline numbers">
  {{ metric("Global IPv6 adoption (consensus)", consensus, "pct", note=consensus_note) }}
  {{ metric("Cloudflare HTTP requests over IPv6", cf_ipv6, "pct") }}
  {{ metric("IPv6 BGP prefixes", bgp_current, "int",
            note=(bgp_year.value | format_value("signed_int")) ~ " in the past year" if bgp_year else None) }}
  {{ metric("Top 1000 sites with IPv6 (AAAA)", sites, "pct") }}
  {{ metric("Economies ≥ " ~ above_threshold ~ "% IPv6-capable", above, "int",
            note="of " ~ considered.value ~ " economies with at least " ~ min_samples_label ~ " APNIC samples" if considered else None) }}
</section>
<ul class="components">
  {% for label, d in components %}
  <li>{{ label }}: {% if d %}{{ d.value | format_value("pct") }}{% else %}<span class="missing">— source unavailable</span>{% endif %}</li>
  {% endfor %}
</ul>

<h2>Current trends</h2>
<div class="grid-2">
  <div class="card">
    <h3>IPv6 capability by region</h3>
    {% if regions %}
    <ol>
      {% for r in regions.value %}<li>{{ r.name }}: {{ r.capable | format_value("pct") }}</li>{% endfor %}
    </ol>
    {{ provenance(regions) }}
    {% else %}{{ unavailable() }}{% endif %}
  </div>
  <div class="card">
    <h3>Country leaders and registries</h3>
    {% if top_economy %}
    <p><strong>{{ top_economy.value.name }}</strong> has the highest share of IPv6-capable users: {{ top_economy.value.capable | format_value("pct") }}.</p>
    {% endif %}
    {% if us %}
    <p>{{ us.value.name }}: {{ us.value.capable | format_value("pct") }} of users IPv6-capable.</p>
    {% endif %}
    {% if top_economy or us %}{{ provenance(top_economy or us) }}{% else %}{{ unavailable() }}{% endif %}
    {% if lacnic %}
    <p>LACNIC region: {{ lacnic.value.total_blocks_32 | format_value("int") }} IPv6 /32 equivalents allocated across {{ lacnic.value.countries }} economies.</p>
    {{ provenance(lacnic) }}
    {% endif %}
  </div>
</div>

<h2>Detailed statistics by source</h2>
<details class="source" open>
  <summary>APNIC Labs: users able to use IPv6</summary>
  {% if apnic_world %}
  <p>{{ apnic_world.value.capable | format_value("pct") }} of users worldwide are IPv6-capable and {{ apnic_world.value.preferred | format_value("pct") }} prefer IPv6, from {{ apnic_world.value.samples | format_value("int") }} measurement samples.</p>
  {{ provenance(apnic_world) }}
  {% else %}{{ unavailable() }}{% endif %}
</details>
<details class="source" open>
  <summary>Top sites with IPv6 (Tranco list, AAAA lookups)</summary>
  {% if tranco %}
  <p>{{ tranco.value.with_aaaa | format_value("int") }} of the top {{ tranco.value.checked | format_value("int") }} sites ({{ tranco.value.percentage | format_value("pct") }}) publish an AAAA record on the bare domain or on <code>www</code>.</p>
  {{ provenance(tranco) }}
  {% else %}{{ unavailable() }}{% endif %}
</details>
<details class="source" open>
  <summary>IPv6 BGP routing table</summary>
  {% if bgp_current %}
  <p>{{ bgp_current.value | format_value("int") }} IPv6 prefixes in the routing table{% if bgp_year %}, {{ bgp_year.value | format_value("signed_int") }} over the past year{% endif %}{% if bgp_month %} and {{ bgp_month.value | format_value("signed_int") }} in the last 30 days{% endif %}.</p>
  {% if bgp_chart %}<div class="chart">{{ bgp_chart }}</div>{% endif %}
  {{ provenance(bgp_current) }}
  {% else %}{{ unavailable() }}{% endif %}
</details>
<details class="source" open>
  <summary>Cloudflare Radar: HTTP requests by IP version</summary>
  {% if cf_ipv6 %}
  <p>{{ cf_ipv6.value | format_value("pct") }} of HTTP requests to Cloudflare use IPv6{% if cf_ipv4 %} and {{ cf_ipv4.value | format_value("pct") }} use IPv4{% endif %}.</p>
  {% if cf_chart %}<div class="chart">{{ cf_chart }}</div>{% endif %}
  {{ provenance(cf_ipv6) }}
  {% else %}{{ unavailable() }}{% endif %}
</details>

<h2>Key combined insights</h2>
<ul>
  {% if consensus %}<li>Averaging {{ consensus_note }}, global IPv6 adoption is {{ consensus.value | format_value("pct") }}.</li>{% endif %}
  {% if apnic_capable and sites %}<li>{{ apnic_capable.value | format_value("pct") }} of users can use IPv6, while {{ sites.value | format_value("pct") }} of the top sites publish AAAA records: a difference of {{ (sites.value - apnic_capable.value) | format_value("pct_points") }}.</li>{% endif %}
  {% if bgp_year %}<li>The IPv6 routing table changed by {{ bgp_year.value | format_value("signed_int") }} prefixes over the past year.</li>{% endif %}
  {% if regions and regions.value %}<li>{{ regions.value[0].name }} leads all regions at {{ regions.value[0].capable | format_value("pct") }} IPv6-capable.</li>{% endif %}
  {% if not (consensus or bgp_year or regions) %}<li class="missing">— source unavailable</li>{% endif %}
</ul>

<h2>Recent updates</h2>
<ul>
  {% if bgp_month %}<li>IPv6 BGP table: {{ bgp_month.value | format_value("signed_int") }} prefixes in the last 30 days.</li>{% endif %}
  {% if lacnic %}<li>LACNIC: {{ lacnic.value.total_blocks_32 | format_value("int") }} IPv6 /32 equivalents allocated across {{ lacnic.value.countries }} economies (registry file of {{ lacnic.value.file_date }}).</li>{% endif %}
  {% if afrinic %}<li>AFRINIC: {{ afrinic.value.total_blocks_32 | format_value("int") }} IPv6 /32 equivalents allocated across {{ afrinic.value.countries }} economies (registry file of {{ afrinic.value.file_date }}).</li>{% endif %}
  {% if not (bgp_month or lacnic or afrinic) %}<li class="missing">— source unavailable</li>{% endif %}
</ul>

<h2>Data freshness</h2>
{{ freshness_table(freshness) }}
{% endblock %}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_overview.py tests/test_build.py -v`
Expected: all passed. If `test_charts_render` counts more than 2, check that `index.html` isn't being read instead of `overview/index.html`.

- [ ] **Step 6: Commit**

```bash
git add web/ tests/test_overview.py
git commit -m "Build merged Overview page from collected data only"
```

---

### Task 11: Guard against hard-coded statistics

**Files:**
- Create: `tests/test_no_static_stats.py`

**Interfaces:**
- Consumes: the files under `collect/`, `web/` (Python) and `web/templates/`.
- Produces: `find_statistics(text: str) -> list[str]` (test-local helper).

- [ ] **Step 1: Write the test** — `tests/test_no_static_stats.py`:

```python
"""Fail if a statistic is typed into code or templates instead of coming from data."""
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_DIRS = ("collect", "web")
TEMPLATES = ROOT / "web" / "templates"
STATISTIC = (
    re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s?%"),   # 49%, 12.5 %
    re.compile(r"\b\d{1,3}(?:,\d{3})+\b"),         # 228,789
)
REFERENCE_BLOCK = re.compile(r"{%-?\s*call\s+reference\(.*?{%-?\s*endcall\s*-?%}", re.S)
JINJA_COMMENT = re.compile(r"{#.*?#}", re.S)
STRING_TOKENS = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)}


def find_statistics(text: str) -> list[str]:
    return [m.group(0) for pattern in STATISTIC for m in pattern.finditer(text)]


def python_strings(path: Path):
    with path.open("rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type in STRING_TOKENS:
                yield tok.start[0], tok.string


def test_detector_catches_examples():
    assert find_statistics('"49%"') == ["49%"]
    assert find_statistics("BGP 228,789 prefixes") == ["228,789"]
    assert find_statistics("12.5 % of sites") == ["12.5 %"]
    assert find_statistics("{:.1f}% %Y-%m-%d rgba(0,0,0,0) /32 2001:db8::") == []


def test_python_has_no_hardcoded_statistics():
    offenders = []
    for directory in PY_DIRS:
        for path in sorted((ROOT / directory).rglob("*.py")):
            for line, text in python_strings(path):
                offenders += [f"{path.relative_to(ROOT)}:{line}: {hit!r}" for hit in find_statistics(text)]
    assert offenders == []


def test_templates_have_no_hardcoded_statistics():
    offenders = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = JINJA_COMMENT.sub("", REFERENCE_BLOCK.sub("", path.read_text()))
        offenders += [f"{path.relative_to(ROOT)}: {hit!r}" for hit in find_statistics(text)]
    assert offenders == []


def test_collectors_have_no_fallback_data():
    offenders = []
    for path in sorted((ROOT / "collect").rglob("*.py")):
        offenders += [f"{path.relative_to(ROOT)}:{line}" for line, text in python_strings(path)
                      if "fallback" in text.lower()]
    assert offenders == []
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/test_no_static_stats.py -v`
Expected: 4 passed. This test guards code that already exists, so it should pass straight away. To prove it bites, temporarily add `"49%"` to any string in `web/templates/overview.html`, run it, see `test_templates_have_no_hardcoded_statistics` FAIL naming the file, then revert.

- [ ] **Step 3: Run the whole suite**

Run: `uv run pytest -q`
Expected: all tests pass (about 70).

- [ ] **Step 4: Commit**

```bash
git add tests/test_no_static_stats.py
git commit -m "Add test that fails on hard-coded statistics or fallback data"
```

---

### Task 12: Workflow, docs and end-to-end check

**Files:**
- Create: `.github/workflows/publish.yml`
- Modify: `README.md` (add a section after "Quick Start")

**Interfaces:**
- Consumes: `python -m collect.run --data-dir data [--force]` (exit 1 when the threshold is exceeded); `python -m web.build --data-dir data --out dist`.
- Produces: the daily pipeline and the preview deployment.

- [ ] **Step 1: Run the real pipeline locally**

Make sure `.env` contains `CLOUDFLARE_API_KEY=...` (it is gitignored). Then run:

```bash
uv run python -m collect.run --data-dir data
uv run python -m web.build --data-dir data --out dist
```

Expected: the collect summary shows `failed=0`, `not_configured=1` (isoc_pulse); `data/` contains `apnic.json`, `bgp_v6_table.json`, `cloudflare_ip_version.json`, `tranco_aaaa.json`, `lacnic_delegations.json`, `afrinic_delegations.json`, `manifest.json`. The Tranco step takes a few minutes. If a source fails, read its `error` in `data/manifest.json` and fix the parser against the live response before continuing.

- [ ] **Step 2: Look at the page**

Run: `uv run python -m http.server 8000 --directory dist` and open `http://localhost:8000/` and `http://localhost:8000/?page=Combined%20View`.
Check: the headline numbers are plausible and match the sources (e.g. APNIC world capability on stats.labs.apnic.net); both charts draw; the theme toggle switches colors, including chart text; the `?page=` link lands on `/overview/`; the layout works at 375px wide (browser dev tools). Stop the server.

- [ ] **Step 3: Write `.github/workflows/publish.yml`**

```yaml
name: Collect data and publish site

on:
  schedule:
    - cron: "0 0 * * *"   # daily, 00:00 UTC (GitHub may start it a few minutes late)
  workflow_dispatch:
    inputs:
      force:
        description: "Re-fetch every source, ignoring re-fetch intervals"
        type: boolean
        default: false
  push:
    branches: [static-site]   # until merged to main, a push is the only way to run it (see Step 7)

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  publish:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v6
        with:
          python-version: "3.12"

      - name: Install
        run: uv sync --frozen

      - name: Test
        run: uv run pytest -q

      - name: Check out data branch into data/
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
          if git ls-remote --exit-code --heads origin data > /dev/null; then
            git fetch --depth=1 origin data
            git worktree add -B data data origin/data
          else
            git worktree add --orphan -b data data
          fi

      - name: Collect
        id: collect
        env:
          CLOUDFLARE_API_KEY: ${{ secrets.CLOUDFLARE_API_KEY }}
          ISOC_PULSE_API_KEY: ${{ secrets.ISOC_PULSE_API_KEY }}
        run: uv run python -m collect.run --data-dir data ${{ inputs.force && '--force' || '' }}

      - name: Save data (also after a failed collect, to keep the error record)
        if: ${{ !cancelled() && steps.collect.outcome != 'skipped' }}
        working-directory: data
        run: |
          git add -A
          if git diff --cached --quiet; then
            echo "No data changes"
          else
            git commit -m "data: $(date -u +%Y-%m-%dT%H:%MZ)"
            git push origin HEAD:data
          fi

      - name: Build site
        run: uv run python -m web.build --data-dir data --out dist

      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist

      - id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 4: Add the README section** — insert after the "Quick Start" section of `README.md`:

```markdown
## Static site (GitHub Pages)

The site is being moved from the Streamlit server to a static site on GitHub Pages
(design: `docs/superpowers/specs/2026-10-14-static-site-migration-design.md`).

- `collect/`: data sources. `uv run python -m collect.run --data-dir data` fetches the
  sources that are due and writes `data/<source>.json` plus `data/manifest.json`.
  `--force` re-fetches everything; `--only <source>` fetches one.
- `web/`: page generation. `uv run python -m web.build --data-dir data --out dist`
  renders the site from that JSON, with no network access.
- `.github/workflows/publish.yml` runs both daily at 00:00 UTC, saves the data on the
  `data` branch, and deploys to Pages. If more than a quarter of the sources that were
  due fail, nothing is published and GitHub emails the failure.
- Secrets: `CLOUDFLARE_API_KEY` (required for the Cloudflare source),
  `ISOC_PULSE_API_KEY` (optional; the ISOC Pulse source is off without it).
- Tests: `uv run pytest`.

Every number on the site must come from collected data; a test fails if a
statistic is typed into the code or templates.
```

- [ ] **Step 5: Commit and push the branch**

```bash
git add .github/workflows/publish.yml README.md
git commit -m "Add daily collect-and-publish workflow and static site docs"
git push -u origin static-site
```

- [ ] **Step 6: One-time GitHub settings (owner does these in the browser)**

1. **Settings → Pages → Build and deployment → Source:** "GitHub Actions".
2. **Settings → Environments → github-pages → Deployment branches and tags:** add `static-site` (only `main` is allowed by default).
3. **Settings → Secrets and variables → Actions:** add `CLOUDFLARE_API_KEY`.

- [ ] **Step 7: First real run**

GitHub only runs `schedule` and `workflow_dispatch` triggers from workflow files on the
default branch (`main`). Until the switch-over plan merges this branch, runs on
`static-site` are triggered by pushes; each push collects whatever sources are due.
To trigger a run without code changes: `git commit --allow-empty -m "Refresh data" && git push`.

Run: `gh run watch $(gh run list --workflow=publish.yml --branch static-site --limit 1 --json databaseId -q '.[0].databaseId')`
Expected: the run triggered by the Step 5 push succeeds (if it ran before the Step 6 settings were in place, push an empty commit as above); `gh api repos/buraglio/ipv6stats/branches/data` shows the new `data` branch; `https://buraglio.github.io/ipv6stats/` shows the Overview with numbers matching your local run; `https://buraglio.github.io/ipv6stats/?page=Combined%20View` redirects to `/ipv6stats/overview/`.
