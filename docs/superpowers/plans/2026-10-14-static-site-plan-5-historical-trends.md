# Static Site Plan 5: Historical Trends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Historical Trends page made only of real time series: APNIC world and regional history, ISOC Pulse's global series, BGP table and AS growth, RIR allocation growth, Cloudflare's 52-week series, and this site's own daily snapshots.

**Architecture:** One new monthly source (`apnic_region_history`). A snapshot step at the end of each collection run appends today's headline values to `data/history.json`. One new page `/historical-trends/`.

**Spec:** `docs/superpowers/specs/2026-10-14-static-site-migration-design.md`, **Amendment 4 → Historical Trends**.

## Global Constraints

- Work on `staging`; no Claude attribution. Before pushing, check that a PR from `staging` is open; open a new one if not.
- No invented or extrapolated series. The milestones list is a dated reference block of historical events, not statistics.
- Snapshots record only sources whose latest JSON is current-format and successful. A value missing on a day is left out, never carried forward or interpolated.
- Page `/historical-trends/`, nav after BGP Statistics; legacy `"Historical Trends": "historical-trends/"`.

## Review Focus

1. **A region page fails.** The source fails as a whole (keeps last good data), because a partial regional chart would mislead. Test: `test_region_history_fails_if_any_region_fails`.
2. **Snapshots on a day when a source is stale, failed, or outdated-format** are skipped for that metric, not recorded from old JSON as if new. Test: `test_snapshot_skips_failed_and_outdated_sources`.
3. **Two runs on the same day** replace that day's snapshot, not duplicate it. Test: `test_snapshot_replaces_same_day`.
4. **Fewer than two snapshot days** (the first days after launch): the page explains that collection has started, rather than drawing a one-point chart. Test: `test_snapshots_note_until_two_days`.

---

### Task 1: APNIC regional history

**Files:** Create `collect/sources/apnic_regions.py`, `tests/test_apnic_regions.py`; Modify `collect/sources/__init__.py`

**Interfaces:** source `apnic_region_history` (MONTH); `REGIONS = {"XA": "World", "XB": "Africa", "XC": "Americas", "XD": "Asia", "XE": "Europe", "XF": "Oceania"}`; payload `{"regions": {code: {"name": str, "history": [{"date","capable","preferred"}]}}, "url"}` (weekly, from `apnic_detail.parse_economy`).

- [ ] **Step 1: Failing tests** — `tests/test_apnic_regions.py`:

```python
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import apnic, apnic_regions as ar
from tests.fakes import FakeResponse, make_ctx

PAGE = (Path(__file__).parent / "fixtures" / "apnic" / "economy-US.html").read_text(encoding="utf-8")


def routes(failing=None):
    table = {f"{apnic.URL}{code}": FakeResponse(text=PAGE) for code in ar.REGIONS}
    if failing:
        table[f"{apnic.URL}{failing}"] = FakeResponse(status_code=503)
    return table


def test_fetches_every_region():
    payload = SOURCES["apnic_region_history"].fetch(make_ctx(routes=routes()))
    assert set(payload["regions"]) == set(ar.REGIONS)
    assert payload["regions"]["XE"]["name"] == "Europe"
    assert len(payload["regions"]["XA"]["history"]) >= 52


def test_region_history_fails_if_any_region_fails():
    with pytest.raises(Exception, match="503"):
        SOURCES["apnic_region_history"].fetch(make_ctx(routes=routes(failing="XD")))
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_apnic_regions.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `collect/sources/apnic_regions.py`:

```python
"""APNIC Labs weekly IPv6 capability history for the world and its five regions."""
from collect.registry import MONTH, Context, source
from collect.sources import apnic
from collect.sources.apnic_detail import parse_economy

REGIONS = {"XA": "World", "XB": "Africa", "XC": "Americas", "XD": "Asia", "XE": "Europe", "XF": "Oceania"}


@source("apnic_region_history", MONTH, title="APNIC Labs regional IPv6 history", url=apnic.URL)
def fetch(ctx: Context) -> dict:
    regions = {}
    for code, name in REGIONS.items():  # all or nothing: a partial regional chart would mislead
        response = ctx.session.get(f"{apnic.URL}{code}", timeout=60)
        response.raise_for_status()
        regions[code] = {"name": name, "history": parse_economy(response.text)["history"]}
    return {"regions": regions, "url": apnic.URL}
```

Register `apnic_regions` in `collect/sources/__init__.py`.

- [ ] **Step 4: Verify** — `uv run pytest tests/test_apnic_regions.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/sources/ tests/test_apnic_regions.py && git commit -m "Collect APNIC regional IPv6 history"`

---

### Task 2: Daily snapshots of headline values

**Files:** Create `collect/history.py`, `tests/test_history.py`; Modify `collect/run.py` (call after saving the manifest), `web/data.py` (`Data.history()`)

**Interfaces:** `collect.history.TRACKED: dict[name, (source_key, path tuple)]`; `HISTORY = "history.json"`; `record(data_dir, manifest, sources, now) -> dict | None` (today's entry or None); `load(data_dir) -> list[{"date", "values"}]`; `Data.history() -> list`.

- [ ] **Step 1: Failing tests** — `tests/test_history.py`:

```python
import json
from datetime import datetime, timezone

from collect import history
from collect.manifest import load as load_manifest
from collect.registry import SOURCES
from tests.sample_data import write_sample_data

DAY1 = datetime(2026, 10, 14, 0, 30, tzinfo=timezone.utc)
DAY2 = datetime(2026, 10, 15, 0, 30, tzinfo=timezone.utc)


def test_snapshot_records_tracked_values(tmp_path):
    d = write_sample_data(tmp_path)
    entry = history.record(d, load_manifest(d), SOURCES, DAY1)
    assert entry == {"date": "2026-10-14", "values": {"apnic_world_capable": 43.6, "cloudflare_ipv6": 38.4,
                                                       "tranco_aaaa": 61.2, "isoc_top_sites": 51.7}}
    assert history.load(d) == [entry]


def test_snapshot_replaces_same_day(tmp_path):
    d = write_sample_data(tmp_path)
    history.record(d, load_manifest(d), SOURCES, DAY1)
    history.record(d, load_manifest(d), SOURCES, DAY1)
    history.record(d, load_manifest(d), SOURCES, DAY2)
    assert [h["date"] for h in history.load(d)] == ["2026-10-14", "2026-10-15"]


def test_snapshot_skips_failed_and_outdated_sources(tmp_path):
    d = write_sample_data(tmp_path, omit=("tranco_aaaa",))
    manifest = load_manifest(d)
    manifest["apnic"]["schema"] = 1  # written by an older parser
    values = history.record(d, manifest, SOURCES, DAY1)["values"]
    assert "tranco_aaaa" not in values and "apnic_world_capable" not in values
    assert values["cloudflare_ipv6"] == 38.4


def test_no_tracked_data_records_nothing(tmp_path):
    assert history.record(tmp_path, {}, SOURCES, DAY1) is None
    assert history.load(tmp_path) == []


def test_run_records_a_snapshot(tmp_path):
    from collect.registry import Source
    from collect.run import run
    from tests.fakes import make_ctx
    sources = {"tranco_aaaa": Source("tranco_aaaa", 1, lambda c: {"percentage": 50.0}, "T", "https://e.example/")}
    run(sources, tmp_path, make_ctx(now=DAY1))
    assert history.load(tmp_path)[0]["values"] == {"tranco_aaaa": 50.0}
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_history.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `collect/history.py`:

```python
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
```

In `collect/run.py`, add `from collect import history` with the other `collect` imports, and right after `manifest_file.save(data_dir, manifest)` in `run()` add:

```python
    history.record(data_dir, manifest, sources, ctx.now)
```

In `web/data.py`, add `from collect import history as history_file` after `from collect import manifest as manifest_file`, and add to `Data`:

```python
    def history(self) -> list[dict]:
        """This site's own daily snapshots (collect/history.py), oldest first."""
        return history_file.load(self.data_dir)
```

- [ ] **Step 4: Verify** — `uv run pytest tests/test_history.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/ web/data.py tests/test_history.py && git commit -m "Record daily snapshots of headline values in data/history.json"`

---

### Task 3: Historical Trends page

**Files:** Create `web/pages/historical_trends.py`, `web/templates/historical-trends.html`, `tests/test_historical_trends.py`; Modify `web/build.py`, `tests/sample_data.py`

**Interfaces:** `web.pages.historical_trends.context(data) -> dict`; `SNAPSHOT_LABELS`; `MIN_SNAPSHOT_DAYS = 2`.

- [ ] **Step 1: Sample data** — add to `PAYLOADS`:

```python
    "apnic_region_history": {
        "regions": {code: {"name": name, "history": [{"date": "2025-10-13", "capable": base, "preferred": base - 2},
                                                     {"date": "2026-10-12", "capable": base + 2, "preferred": base}]}
                    for code, name, base in (("XA", "World", 41.0), ("XB", "Africa", 5.0), ("XC", "Americas", 49.0),
                                             ("XD", "Asia", 48.0), ("XE", "Europe", 35.0), ("XF", "Oceania", 40.0))},
        "url": "https://stats.labs.apnic.net/ipv6/",
    },
```

- [ ] **Step 2: Failing tests** — `tests/test_historical_trends.py`:

```python
import json

from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, history=None, **kwargs):
    data = write_sample_data(tmp_path / "data", **kwargs)
    if history is not None:
        (data / "history.json").write_text(json.dumps(history))
    out = tmp_path / "dist"
    build(data, out, NOW)
    return out, (out / "historical-trends" / "index.html").read_text()


def test_real_series_charts(tmp_path):
    _, html = render(tmp_path)
    # world, regions, BGP table, ASes, RIR allocations, Cloudflare
    assert html.count("Plotly.newPlot") == 6
    assert "Africa" in html and "Oceania" in html


def test_snapshots_note_until_two_days(tmp_path):
    _, html = render(tmp_path, history=[{"date": "2026-10-14", "values": {"tranco_aaaa": 61.2}}])
    assert "This site started recording daily snapshots on 2026-10-14" in html
    assert html.count("Plotly.newPlot") == 6


def test_snapshot_chart_with_two_days(tmp_path):
    days = [{"date": "2026-10-14", "values": {"tranco_aaaa": 61.2, "apnic_world_capable": 43.6}},
            {"date": "2026-10-15", "values": {"tranco_aaaa": 61.3}}]
    _, html = render(tmp_path, history=days)
    assert html.count("Plotly.newPlot") == 7
    assert "Top 1000 sites with AAAA (Tranco)" in html


def test_milestones_are_dated_reference(tmp_path):
    _, html = render(tmp_path)
    assert "Reference — last reviewed 2026-10-14" in html
    assert "World IPv6 Launch" in html


def test_without_sources(tmp_path):
    _, html = render(tmp_path, omit=("apnic_region_history", "bgp_v6_table", "bgp_v6_ases", "cloudflare_ip_version"))
    assert html.count("— source unavailable") >= 4


def test_nav_and_legacy(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">Historical Trends' in html
    assert '"Historical Trends": "historical-trends/"' in (out / "index.html").read_text()
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_historical_trends.py -q` → FAIL.

- [ ] **Step 4: Implement** — `web/pages/historical_trends.py`:

```python
"""Historical Trends: real time series only, plus this site's own daily snapshots."""
from dataclasses import replace

from collect.sources.isoc import TOPSITES
from collect.sources.tranco import TOP_N
from web import charts, derive
from web.data import Data, Datum, combine
from web.pages.global_adoption import _rir_history

MIN_SNAPSHOT_DAYS = 2
SNAPSHOT_LABELS = {
    "apnic_world_capable": "Users able to use IPv6 (APNIC)",
    "cloudflare_ipv6": "HTTP requests over IPv6 (Cloudflare)",
    "tranco_aaaa": f"Top {TOP_N} sites with AAAA (Tranco)",
    "isoc_top_sites": f"Top {TOPSITES:,} sites with IPv6 (ISOC Pulse)",
}


def _series(name, points, x="date", y="capable"):
    return {"name": name, "points": [{"x": p[x], "y": p[y]} for p in points]}


def _world(data: Data):
    regions = data.datum("apnic_region_history", lambda p: p["regions"])
    isoc = data.datum("isoc_pulse", lambda p: p["users_ipv6"]["series"])
    parts = [d for d in (regions, isoc) if d is not None]
    if not parts:
        return None
    lines = []
    if regions:
        world = regions.value["XA"]["history"]
        lines += [_series("Able to use IPv6 (APNIC)", world), _series("Prefer IPv6 (APNIC)", world, y="preferred")]
    if isoc:
        lines.append(_series("Global IPv6 adoption (ISOC Pulse)", isoc.value, y="value"))
    return combine(lines, parts)


def _regions(data: Data):
    return data.datum("apnic_region_history", lambda p: [
        _series(r["name"], r["history"]) for code, r in sorted(p["regions"].items()) if code != "XA"])


def _snapshots(data: Data):
    days = data.history()
    if len(days) < MIN_SNAPSHOT_DAYS:
        return None, days
    lines = [{"name": label, "points": [{"x": d["date"], "y": d["values"][key]} for d in days if key in d["values"]]}
             for key, label in SNAPSHOT_LABELS.items()]
    lines = [line for line in lines if line["points"]]
    return Datum(lines, (), data.now, False), days


def context(data: Data) -> dict:
    snapshots, days = _snapshots(data)
    rirs = derive.rir_comparison(data)
    cf = data.datum("cloudflare_ip_version", lambda p: p["series"])
    world = _world(data)
    regions = _regions(data)
    return {
        "world": world,
        "world_chart": charts.multi_line_chart(world, title="IPv6 adoption worldwide", y_title="Percent"),
        "regions": regions,
        "regions_chart": charts.multi_line_chart(regions, title="Users able to use IPv6, by region", y_title="Percent"),
        "bgp": derive.bgp_current(data),
        "bgp_chart": charts.line_chart(data.datum("bgp_v6_table", lambda p: p["daily"]),
                                       x="date", y="prefixes", title="IPv6 BGP table size", y_title="Prefixes"),
        "ases": data.datum("bgp_v6_ases", lambda p: p["current"]),
        "ases_chart": charts.line_chart(data.datum("bgp_v6_ases", lambda p: p["daily"]),
                                        x="date", y="ases", title="ASes in the IPv6 routing table", y_title="ASes"),
        "rirs": rirs,
        "rir_chart": charts.multi_line_chart(_rir_history(rirs), title="IPv6 allocated over time (/32 equivalents)",
                                             y_title="/32 equivalents", x_type="linear"),
        "cloudflare": cf,
        "cloudflare_chart": charts.line_chart(cf, x="t", y="ipv6", title="HTTP requests over IPv6 (Cloudflare)",
                                              y_title="Percent"),
        "snapshots_chart": charts.multi_line_chart(snapshots, title="Recorded daily by this site", y_title="Percent"),
        "snapshot_days": len(days),
        "snapshot_start": days[0]["date"] if days else None,
    }
```

`web/templates/historical-trends.html`:

```html
{% extends "base.html" %}
{% from "macros.html" import provenance, unavailable, reference, freshness_table %}
{% block content %}
<h1>Historical IPv6 Trends</h1>
<p>Every chart is a measured time series from its source. Nothing is projected or interpolated.</p>

<h2>Worldwide</h2>
{% if world_chart %}<div class="chart">{{ world_chart }}</div>{{ provenance(world) }}{% else %}{{ unavailable() }}{% endif %}

<h2>By region</h2>
{% if regions_chart %}<div class="chart">{{ regions_chart }}</div>{{ provenance(regions) }}{% else %}{{ unavailable() }}{% endif %}

<h2>Routing table</h2>
<div class="grid-2">
  <div class="card">{% if bgp_chart %}<div class="chart">{{ bgp_chart }}</div>{{ provenance(bgp) }}{% else %}{{ unavailable() }}{% endif %}</div>
  <div class="card">{% if ases_chart %}<div class="chart">{{ ases_chart }}</div>{{ provenance(ases) }}{% else %}{{ unavailable() }}{% endif %}</div>
</div>

<h2>Address allocations</h2>
{% if rir_chart %}<div class="chart">{{ rir_chart }}</div>{{ provenance(rirs) }}{% else %}{{ unavailable() }}{% endif %}

<h2>Traffic</h2>
{% if cloudflare_chart %}<div class="chart">{{ cloudflare_chart }}</div>{{ provenance(cloudflare) }}{% else %}{{ unavailable() }}{% endif %}

<h2>Recorded by this site</h2>
{% if snapshots_chart %}
<div class="chart">{{ snapshots_chart }}</div>
<p class="provenance">Daily snapshots from this site's own collection since {{ snapshot_start }}. A source that failed or was outdated on a day is left out for that day.</p>
{% elif snapshot_start %}
<p class="missing">This site started recording daily snapshots on {{ snapshot_start }}; a chart appears once there are two days of data.</p>
{% else %}{{ unavailable() }}{% endif %}

<h2>Milestones</h2>
{% call reference(reviewed="2026-10-14") %}
<ul>
  <li>December 1998: RFC 2460 specifies IPv6.</li>
  <li>3 February 2011: IANA allocates its last IPv4 /8 blocks to the regional registries.</li>
  <li>15 April 2011: APNIC reaches its final IPv4 /8.</li>
  <li>8 June 2011: World IPv6 Day.</li>
  <li>6 June 2012: World IPv6 Launch.</li>
  <li>14 September 2012: RIPE NCC begins allocating from its last IPv4 /8.</li>
  <li>24 September 2015: ARIN's free IPv4 pool is exhausted.</li>
  <li>July 2017: RFC 8200 replaces RFC 2460 as the IPv6 standard.</li>
  <li>25 November 2019: RIPE NCC runs out of IPv4 addresses.</li>
  <li>19 November 2020: OMB memorandum M-21-07 sets US federal IPv6-only targets.</li>
</ul>
{% endcall %}

<h2>Data freshness</h2>
{{ freshness_table(freshness) }}
{% endblock %}
```

In `web/build.py`: add `historical_trends` to the `from web.pages import ...` line; append `Page("historical-trends", "Historical Trends", historical_trends.context),` to `PAGES` and `"Historical Trends": "historical-trends/",` to `LEGACY_PAGES`.

- [ ] **Step 5: Verify** — `uv run pytest tests/test_historical_trends.py -q && uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add web/ tests/ && git commit -m "Add Historical Trends page from real time series and the site's own snapshots"`

---

### Task 4: Live run and visual check

- [ ] **Step 1:** `uv run python -m collect.run --data-dir data --force --only apnic_region_history` → `failed=0`; `data/history.json` exists with today's entry.
- [ ] **Step 2:** build, serve, look at `/historical-trends/` at desktop and 375px.
- [ ] **Step 3:** README "Pages so far" adds Historical Trends, and a bullet: `- data/history.json (on the data branch) holds this site's own daily snapshots of headline values.` `uv run pytest -q`; commit `"Document the Historical Trends page"`.
