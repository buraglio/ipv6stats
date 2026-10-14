# Static Site Plan 4: BGP Statistics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A BGP Statistics page built from real routing data: Potaroo's IPv6 report (summary statistics, prefix-length distribution, AS-count history), the CIDR Report aggregation table, and RouteViews collectors.

**Architecture:** Four new daily sources in `collect/sources/`, one derive helper generalised, one new page `/bgp-statistics/`.

**Tech Stack:** As before.

**Spec:** `docs/superpowers/specs/2026-10-14-static-site-migration-design.md`, **Amendment 4 → BGP Statistics**.

## Global Constraints

- Work on `staging`; no Claude attribution in commits.
- Don't modify Streamlit files. Collectors return parsed data or raise; every displayed number goes through a `Datum`; the static-statistics guard stays green.
- New sources are `DAY` (routing data changes daily): `bgp_v6_ases`, `bgp_v6_summary`, `cidr_report_aggregation`, `routeviews_collectors`.
- The CIDR table is labelled "ASes that could shrink the table most by aggregating", never "top ASes by prefix count".
- AS names come from RIPEstat `as-overview`; a failed name lookup leaves the name empty (the AS number still shows) and is not a source failure.
- Page `/bgp-statistics/`, nav after Cloud Services; legacy `"BGP Statistics": "bgp-statistics/"`.

## Review Focus

1. **Potaroo renames a statistic** (data-file name changes). The parser must raise, not show a blank or zero. Test: `test_summary_rejects_missing_statistics`.
2. **The CIDR Report layout shifts.** Wrong numbers must not land in the wrong columns: the row pattern is anchored on all six cells, and fewer than 10 rows raises. Test: `test_cidr_rejects_changed_format`.
3. **RouteViews pagination.** A collector's latest snapshot may sit on the second-to-last page. Read the last two pages. Test: `test_routeviews_reads_last_two_pages`.
4. **RIPEstat down.** The aggregation table still publishes, without names. Test: `test_names_are_optional`.

---

### Task 1: AS-count history and a generic series change

**Files:** Modify `collect/sources/bgp.py`, `web/derive.py`; Test `tests/test_bgp.py`, `tests/test_derive.py` (append); `tests/sample_data.py` (add payload)

**Interfaces:** `bgp.parse(text, min_days=MIN_DAYS, now=None, field="prefixes")`; `bgp.AS_URL`; source `bgp_v6_ases` (payload `{"daily": [{"date", "ases"}], "current", "current_at", "url"}`); `derive.series_change(data, key, field, days) -> Datum | None`; `derive.bgp_change` unchanged in behaviour.

- [ ] **Step 1: Failing tests** — append to `tests/test_bgp.py`:

```python


def test_parse_named_field():
    parsed = bgp.parse(SAMPLE, min_days=1, field="ases")
    assert parsed["daily"][-1] == {"date": "2026-10-15", "ases": 258600}


def test_as_history_source():
    ctx = make_ctx(routes={bgp.AS_URL: FakeResponse(text=FIXTURE.read_text())})
    payload = SOURCES["bgp_v6_ases"].fetch(ctx)
    assert "ases" in payload["daily"][-1] and SOURCES["bgp_v6_ases"].ttl_seconds == DAY
```

Append to `tests/test_derive.py`:

```python


def test_series_change_on_ases(tmp_path):
    d = data(tmp_path)
    assert derive.series_change(d, "bgp_v6_ases", "ases", 365).value == 2751   # 37751 - 35000
    assert derive.series_change(d, "bgp_v6_ases", "ases", 4000) is None
```

Add to `PAYLOADS` in `tests/sample_data.py`:

```python
    "bgp_v6_ases": {
        "daily": [{"date": "2025-10-14", "ases": 35000}, {"date": "2026-10-14", "ases": 37751}],
        "current": 37751, "current_at": "2026-10-14T00:00:00+00:00",
        "url": "https://bgp.potaroo.net/v6/as2.0/index.html",
    },
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_bgp.py tests/test_derive.py -q` → FAIL (`unexpected keyword argument 'field'`).

- [ ] **Step 3: Implement** — in `collect/sources/bgp.py`: change the signature to `def parse(text: str, min_days: int = MIN_DAYS, now: datetime | None = None, field: str = "prefixes") -> dict:` and the `daily = ...` line to `daily = [{"date": day, field: count} for day, (_, count) in sorted(latest_per_day.items())]`. Add `AS_URL = "https://bgp.potaroo.net/v6/as2.0/bgp-as-count.txt"  # "<unix time> <unique ASes>"` after `URL`, and at the end of the file:

```python


@source("bgp_v6_ases", DAY, title="Potaroo IPv6 AS count history", url=PAGE)
def fetch_ases(ctx: Context) -> dict:
    response = ctx.session.get(AS_URL, timeout=60)
    response.raise_for_status()
    return parse(response.text, now=ctx.now, field="ases")
```

In `web/derive.py`, replace `bgp_change` with:

```python
def series_change(data: Data, key: str, field: str, days: int) -> Datum | None:
    """Change in a daily series over `days`, or None when history doesn't reach back that far."""
    def pick(p):
        cutoff = date.fromisoformat(p["daily"][-1]["date"]) - timedelta(days=days)
        earlier = [d for d in p["daily"] if date.fromisoformat(d["date"]) <= cutoff]
        return p["current"] - earlier[-1][field] if earlier else None

    return data.datum(key, pick)


def bgp_change(data: Data, days: int) -> Datum | None:
    return series_change(data, "bgp_v6_table", "prefixes", days)
```

- [ ] **Step 4: Verify** — `uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/sources/bgp.py web/derive.py tests/ && git commit -m "Collect Potaroo IPv6 AS-count history"`

---

### Task 2: Potaroo summary statistics and prefix-length distribution

**Files:** Create `collect/sources/potaroo_summary.py`, `tests/test_potaroo_summary.py`, `tests/fixtures/bgp/v6-index.html`; Modify `collect/sources/__init__.py`

**Interfaces:** source `bgp_v6_summary`; `parse(page) -> {"stats": {name: number}, "prefix_lengths": [{"length": int, "prefixes": int, "share": float|None}], "url"}`; `WANTED` maps Potaroo data-file stems to stat names: `fib_entries`, `rib_entries`, `unique_ases`, `origin_only_ases`, `transit_only_ases`, `average_prefix_length`, `average_as_path_length`.

- [ ] **Step 1: Record fixture** — `curl -s https://bgp.potaroo.net/v6/as2.0/index.html -o tests/fixtures/bgp/v6-index.html && grep -c 'target="text"' tests/fixtures/bgp/v6-index.html` → about 1200.

- [ ] **Step 2: Failing tests** — `tests/test_potaroo_summary.py`:

```python
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import potaroo_summary as ps
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "bgp" / "v6-index.html").read_text(encoding="utf-8", errors="ignore")


def stat(stem, value, label="x"):
    return f'<a href="/cgi-bin/plota">{label}</a></td><td><b><a href="{stem}.txt" target="text">{value}</a></b></td>'


ALL = "".join(stat(stem, i + 1) for i, stem in enumerate(ps.WANTED)) + "".join(
    stat(f"bgp-prefix-{n}", n * 10) + stat(f"bgp-p-prefix-{n}", n / 10) for n in range(32, 49))


def test_parse_sample():
    parsed = ps.parse(ALL)
    assert parsed["stats"]["fib_entries"] == 1 and isinstance(parsed["stats"]["fib_entries"], int)
    assert parsed["prefix_lengths"][-1] == {"length": 48, "prefixes": 480, "share": 4.8}


def test_parse_recorded_page():
    parsed = ps.parse(FIXTURE)
    assert parsed["stats"]["unique_ases"] > 10_000
    assert 30 < parsed["stats"]["average_prefix_length"] < 64
    assert any(r["length"] == 48 and r["prefixes"] > 0 for r in parsed["prefix_lengths"])


def test_summary_rejects_missing_statistics():
    with pytest.raises(ValueError, match="Potaroo report format changed"):
        ps.parse(ALL.replace("bgp-as-count.txt", "bgp-ases.txt"))


def test_fetch():
    assert SOURCES["bgp_v6_summary"].fetch(make_ctx(routes={ps.URL: FakeResponse(text=FIXTURE)}))["stats"]
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_potaroo_summary.py -q` → FAIL (`ImportError`).

- [ ] **Step 4: Implement** — `collect/sources/potaroo_summary.py`:

```python
"""Summary statistics and prefix-length distribution from Potaroo's IPv6 BGP report."""
import re

from collect.registry import DAY, Context, source

URL = "https://bgp.potaroo.net/v6/as2.0/index.html"
# Each statistic links to its own data file: ...>Label</a></td><td><b><a href="bgp-as-count.txt" target="text">37751</a>
STAT = re.compile(r'</a></td><td><b><a href="([a-z0-9.-]+)\.txt" target="text">([^<]+)</a>')
WANTED = {  # data-file stem -> name; the stems are stable, the labels are prose
    "bgp-active": "fib_entries",
    "bgp-all": "rib_entries",
    "bgp-as-count": "unique_ases",
    "bgp-as-term": "origin_only_ases",
    "bgp-transit": "transit_only_ases",
    "bgp-average-prefix": "average_prefix_length",
    "bgp-average-aspath-length": "average_as_path_length",
}
COUNT = re.compile(r"bgp-prefix-(\d+)$")
SHARE = re.compile(r"bgp-p-prefix-(\d+)$")
MIN_LENGTHS = 10


def _number(text: str):
    value = float(text)
    return int(value) if value.is_integer() and "." not in text else value


def parse(page: str) -> dict:
    stats, counts, shares = {}, {}, {}
    for stem, raw in STAT.findall(page):
        try:
            value = _number(raw.strip())
        except ValueError:  # "(data)" links to whole vectors
            continue
        if stem in WANTED:
            stats[WANTED[stem]] = value
        elif m := COUNT.match(stem):
            counts[int(m.group(1))] = int(value)
        elif m := SHARE.match(stem):
            shares[int(m.group(1))] = float(value)
    missing = sorted(set(WANTED.values()) - set(stats))
    if missing or len(counts) < MIN_LENGTHS:
        raise ValueError(f"Potaroo report format changed: missing {missing}, {len(counts)} prefix lengths")
    lengths = [{"length": n, "prefixes": counts[n], "share": shares.get(n)} for n in sorted(counts)]
    return {"stats": stats, "prefix_lengths": lengths, "url": URL}


@source("bgp_v6_summary", DAY, title="Potaroo IPv6 BGP report (summary)", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)
```

Register `potaroo_summary` in `collect/sources/__init__.py` (alphabetical).

- [ ] **Step 5: Verify** — `uv run pytest tests/test_potaroo_summary.py -q && uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add collect/sources/ tests/test_potaroo_summary.py tests/fixtures/bgp/v6-index.html && git commit -m "Collect Potaroo IPv6 summary statistics and prefix-length distribution"`

---

### Task 3: CIDR Report aggregation table with RIPEstat AS names

**Files:** Create `collect/sources/cidr_report.py`, `tests/test_cidr_report.py`, `tests/fixtures/bgp/cidr-aggregation.html`; Modify `collect/sources/__init__.py`

**Interfaces:** source `cidr_report_aggregation`; `parse(page, min_rows=MIN_ROWS) -> {"date": "YYYY-MM-DD", "table": {"now","aggregated","gain","gain_pct"}, "ases": [{"asn": int, "now","aggregated","gain","gain_pct","name": None}]}`; `NAMES_URL` (RIPEstat as-overview); `fetch` fills `name` (None on lookup failure).

- [ ] **Step 1: Record a trimmed fixture** (the aggregation table only):

```bash
curl -s https://www.cidr-report.org/v6/as2.0/ -o /tmp/cidr.html && python3 - <<'EOF'
t = open("/tmp/cidr.html", encoding="utf-8", errors="ignore").read()
start = t.index("<tr><th colspan=6 align=left>---")
end = t.index("</table>", start)
open("tests/fixtures/bgp/cidr-aggregation.html", "w").write("<table>" + t[start:end] + "</table>\n")
EOF
grep -c "as-report" tests/fixtures/bgp/cidr-aggregation.html
```
Expected: `30`.

- [ ] **Step 2: Failing tests** — `tests/test_cidr_report.py`:

```python
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import cidr_report as cr
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "bgp" / "cidr-aggregation.html").read_text()


def test_parse_recorded_table():
    parsed = cr.parse(FIXTURE)
    assert len(parsed["ases"]) == 30
    assert parsed["date"].count("-") == 2
    first = parsed["ases"][0]
    assert first["now"] - first["aggregated"] == first["gain"]
    assert parsed["table"]["now"] > first["now"]


def test_parse_date():
    assert cr.parse_date("14Oct26") == "2026-10-14"


def test_cidr_rejects_changed_format():
    with pytest.raises(ValueError, match="CIDR Report format changed"):
        cr.parse("<html>maintenance</html>")


def name_routes(asns, body):
    return {f"{cr.NAMES_URL}?resource=AS{a}": body for a in asns}


def test_fetch_adds_names():
    asns = [a["asn"] for a in cr.parse(FIXTURE)["ases"]]
    routes = {cr.URL: FakeResponse(text=FIXTURE)}
    routes.update(name_routes(asns, FakeResponse(json_data={"status": "ok", "data": {"holder": "EXAMPLE - Example Ltd"}})))
    payload = SOURCES["cidr_report_aggregation"].fetch(make_ctx(routes=routes))
    assert payload["ases"][0]["name"] == "EXAMPLE - Example Ltd"


def test_names_are_optional():
    routes = {cr.URL: FakeResponse(text=FIXTURE)}  # RIPEstat unreachable
    payload = SOURCES["cidr_report_aggregation"].fetch(make_ctx(routes=routes))
    assert all(a["name"] is None for a in payload["ases"])
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_cidr_report.py -q` → FAIL (`ImportError`).

- [ ] **Step 4: Implement** — `collect/sources/cidr_report.py`:

```python
"""CIDR Report (IPv6): ASes that could shrink the routing table most by aggregating."""
import logging
import re
from datetime import datetime

from collect.registry import DAY, Context, source

logger = logging.getLogger(__name__)

URL = "https://www.cidr-report.org/v6/as2.0/"
NAMES_URL = "https://stat.ripe.net/data/as-overview/data.json"
DATE = re.compile(r"<th colspan=6 align=left>--- (\d{2}[A-Za-z]{3}\d{2}) ---")
# ASnum | NetsNow | NetsAggr | NetGain | % Gain | Description (always "Gain")
ROW = re.compile(
    r'<tr><td align=left>(?:<a href="[^"]*">)?(AS\d+|Table)(?:</a>)?&nbsp;&nbsp;</td>'
    r"<td align=right><tt>(\d+)</tt></td><td align=right>&nbsp;&nbsp;<tt>(\d+)</tt></td>"
    r"<td align=right>&nbsp;&nbsp;<tt>(-?\d+)</tt></td><td align=right>&nbsp;&nbsp;<tt>([\d.]+)%</tt>&nbsp;&nbsp;</td>"
)
MIN_ROWS = 10


def parse_date(text: str) -> str:
    return datetime.strptime(text, "%d%b%y").date().isoformat()


def parse(page: str, min_rows: int = MIN_ROWS) -> dict:
    date = DATE.search(page)
    table, ases = None, []
    for name, now, aggregated, gain, pct in ROW.findall(page):
        row = {"now": int(now), "aggregated": int(aggregated), "gain": int(gain), "gain_pct": float(pct)}
        if name == "Table":
            table = row
        else:
            ases.append({"asn": int(name[2:]), **row, "name": None})
    if date is None or table is None or len(ases) < min_rows:
        raise ValueError(f"CIDR Report format changed: date={bool(date)}, table={bool(table)}, rows={len(ases)}")
    return {"date": parse_date(date.group(1)), "table": table, "ases": ases, "url": URL}


def _name(ctx: Context, asn: int) -> str | None:
    try:
        response = ctx.session.get(f"{NAMES_URL}?resource=AS{asn}", timeout=20)
        response.raise_for_status()
        return response.json()["data"].get("holder") or None
    except Exception as exc:  # a missing name is only a missing label
        logger.info("no RIPEstat name for AS%s: %s", asn, exc)
        return None


@source("cidr_report_aggregation", DAY, title="CIDR Report IPv6 aggregation summary", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    parsed = parse(response.text)
    for row in parsed["ases"]:
        row["name"] = _name(ctx, row["asn"])
    return parsed
```

Register `cidr_report` in `collect/sources/__init__.py`.

- [ ] **Step 5: Verify** — `uv run pytest tests/test_cidr_report.py -q && uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add collect/sources/ tests/test_cidr_report.py tests/fixtures/bgp/cidr-aggregation.html && git commit -m "Collect the CIDR Report IPv6 aggregation table with AS names"`

---

### Task 4: RouteViews collectors

**Files:** Create `collect/sources/routeviews.py`, `tests/test_routeviews.py`; Modify `collect/sources/__init__.py`

**Interfaces:** source `routeviews_collectors`; payload `{"collectors": [{"name","country","rir_region","date","ipv6_prefixes","ipv6_peers","ipv4_prefixes"}] (active collectors with a snapshot, by ipv6_prefixes desc), "active": int, "snapshot_date": str, "url"}`.

- [ ] **Step 1: Failing tests** — `tests/test_routeviews.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import routeviews as rv
from tests.fakes import FakeResponse, make_ctx

COLLECTORS = {"count": 3, "results": [
    {"name": "route-views2", "country": "US", "rir_region": "ARIN", "removed": False},
    {"name": "route-views.wide", "country": "JP", "rir_region": "APNIC", "removed": False},
    {"name": "route-views.old", "country": "US", "rir_region": "ARIN", "removed": True}]}


def snap(name, date, v6):
    return {"collector": name, "date": f"{date}T00:00:00Z", "ipv6_prefix_count": v6, "ipv6_peer_count": 5,
            "ipv4_prefix_count": 1000000}


FIRST = {"count": 150, "results": [snap("route-views2", "2001-10-27", 0)] * 100}
PAGE1 = {"results": [snap("route-views2", "2026-10-13", 250000)] * 50}       # second-to-last page
PAGE2 = {"results": [snap("route-views.wide", "2026-10-14", 255106)]}        # last page


def routes():
    return {f"{rv.BASE}/collector/": FakeResponse(json_data=COLLECTORS),
            f"{rv.BASE}/timeseries/?page=2": FakeResponse(json_data=PAGE2),
            f"{rv.BASE}/timeseries/?page=1": FakeResponse(json_data=PAGE1),
            f"{rv.BASE}/timeseries/": FakeResponse(json_data=FIRST)}


def test_routeviews_reads_last_two_pages():
    payload = rv.collect(make_ctx(routes=routes()), min_collectors=1)
    names = [c["name"] for c in payload["collectors"]]
    assert names == ["route-views.wide", "route-views2"]     # by IPv6 prefixes, removed collector skipped
    assert payload["collectors"][1]["date"] == "2026-10-13"
    assert payload["active"] == 2 and payload["snapshot_date"] == "2026-10-14"


def test_rejects_changed_format():
    bad = routes(); bad[f"{rv.BASE}/collector/"] = FakeResponse(json_data={"detail": "Not found"})
    with pytest.raises(ValueError, match="RouteViews API format changed"):
        rv.collect(make_ctx(routes=bad), min_collectors=1)


def test_registered_daily():
    assert SOURCES["routeviews_collectors"].ttl_seconds == 86_400
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_routeviews.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `collect/sources/routeviews.py`:

```python
"""RouteViews: active collectors and each one's latest IPv6 table size and peer count."""
from collect.registry import DAY, Context, source

BASE = "https://api.routeviews.org"
HOME = "https://www.routeviews.org/"
MIN_COLLECTORS = 10


def _get(ctx: Context, path: str) -> dict:
    response = ctx.session.get(f"{BASE}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def collect(ctx: Context, min_collectors: int = MIN_COLLECTORS) -> dict:
    listing = _get(ctx, "/collector/")
    if "results" not in listing:
        raise ValueError(f"RouteViews API format changed: collector keys {sorted(listing)}")
    active = {c["name"]: c for c in listing["results"] if not c.get("removed")}
    first = _get(ctx, "/timeseries/")
    size = len(first.get("results", []))
    if not size or "count" not in first:
        raise ValueError("RouteViews API format changed: empty timeseries")
    last_page = (first["count"] + size - 1) // size
    entries = []
    for page in range(max(1, last_page - 1), last_page + 1):  # a collector's latest may be one page back
        entries += _get(ctx, f"/timeseries/?page={page}")["results"]
    latest: dict[str, dict] = {}
    for e in entries:
        name = e["collector"]
        if name in active and (name not in latest or e["date"] > latest[name]["date"]):
            latest[name] = e
    collectors = sorted(({"name": n, "country": active[n].get("country"), "rir_region": active[n].get("rir_region"),
                          "date": e["date"][:10], "ipv6_prefixes": e["ipv6_prefix_count"],
                          "ipv6_peers": e["ipv6_peer_count"], "ipv4_prefixes": e["ipv4_prefix_count"]}
                         for n, e in latest.items()), key=lambda c: c["ipv6_prefixes"], reverse=True)
    if len(collectors) < min_collectors:
        raise ValueError(f"RouteViews API format changed: only {len(collectors)} collectors with snapshots")
    return {"collectors": collectors, "active": len(active),
            "snapshot_date": max(c["date"] for c in collectors), "url": HOME}


@source("routeviews_collectors", DAY, title="RouteViews collectors (API)", url=HOME)
def fetch(ctx: Context) -> dict:
    return collect(ctx)
```

Register `routeviews` in `collect/sources/__init__.py`.

- [ ] **Step 4: Verify** — `uv run pytest tests/test_routeviews.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/sources/ tests/test_routeviews.py && git commit -m "Collect RouteViews collectors' latest IPv6 table sizes"`

---

### Task 5: BGP Statistics page

**Files:** Create `web/pages/bgp_statistics.py`, `web/templates/bgp-statistics.html`, `tests/test_bgp_statistics.py`; Modify `web/format.py` (`"decimal"` format), `web/build.py`, `tests/sample_data.py`

**Interfaces:** `format_value(v, "decimal") -> f"{v:,.2f}"`; `web.pages.bgp_statistics.context(data) -> dict`; `SIXLAB_TOP = 10`.

- [ ] **Step 1: Sample data** — add to `PAYLOADS`:

```python
    "bgp_v6_summary": {
        "stats": {"fib_entries": 258530, "rib_entries": 1002824, "unique_ases": 37751, "origin_only_ases": 31235,
                  "transit_only_ases": 379, "average_prefix_length": 42.9949, "average_as_path_length": 4.9156},
        "prefix_lengths": [{"length": 32, "prefixes": 30000, "share": 11.6}, {"length": 44, "prefixes": 25091, "share": 9.71},
                           {"length": 48, "prefixes": 121568, "share": 47.02}],
        "url": "https://bgp.potaroo.net/v6/as2.0/index.html",
    },
    "cidr_report_aggregation": {
        "date": "2026-10-14",
        "table": {"now": 258420, "aggregated": 127591, "gain": 130829, "gain_pct": 50.6},
        "ases": [{"asn": 9808, "now": 7194, "aggregated": 1160, "gain": 6034, "gain_pct": 83.9,
                  "name": "CHINAMOBILE-CN - China Mobile Communications Group Co., Ltd."},
                 {"asn": 7552, "now": 4044, "aggregated": 27, "gain": 4017, "gain_pct": 99.3, "name": None}],
        "url": "https://www.cidr-report.org/v6/as2.0/",
    },
    "routeviews_collectors": {
        "collectors": [{"name": "route-views.wide", "country": "JP", "rir_region": "APNIC", "date": "2026-10-14",
                        "ipv6_prefixes": 255106, "ipv6_peers": 5, "ipv4_prefixes": 1087315}],
        "active": 57, "snapshot_date": "2026-10-14", "url": "https://www.routeviews.org/",
    },
```

- [ ] **Step 2: Failing tests** — `tests/test_bgp_statistics.py`:

```python
from tests.sample_data import NOW, write_sample_data
from web.build import build
from web.format import format_value


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "bgp-statistics" / "index.html").read_text()


def test_decimal_format():
    assert format_value(4.9156, "decimal") == "4.92"


def test_headline_numbers(tmp_path):
    _, html = render(tmp_path)
    for text in ("258,009", "+27,009 in the past year", "37,751", "+2,751 in the past year", "42.99", "4.92"):
        assert text in html, text


def test_prefix_lengths_and_aggregation(tmp_path):
    _, html = render(tmp_path)
    assert "/48" in html and "121,568" in html and "47.0%" in html
    agg = html[html.index("could shrink the table most"):]
    assert "AS9808" in agg and "CHINAMOBILE-CN" in agg and "AS7552" in agg and "2026-10-14" in agg


def test_routeviews_and_charts(tmp_path):
    _, html = render(tmp_path)
    assert "route-views.wide" in html and "255,106" in html
    assert html.count("Plotly.newPlot") == 3   # table size, AS count, prefix lengths


def test_without_new_sources(tmp_path):
    _, html = render(tmp_path, omit=("bgp_v6_summary", "cidr_report_aggregation", "routeviews_collectors", "bgp_v6_ases"))
    assert html.count("— source unavailable") >= 4


def test_nav_and_legacy(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">BGP Statistics' in html
    assert '"BGP Statistics": "bgp-statistics/"' in (out / "index.html").read_text()
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_bgp_statistics.py -q` → FAIL.

- [ ] **Step 4: Implement** — in `web/format.py`, add before `if fmt == "text":`:

```python
    if fmt == "decimal":
        return f"{value:,.2f}"
```

`web/pages/bgp_statistics.py`:

```python
"""BGP Statistics: routing table size and growth, ASes, prefix lengths, aggregation, collectors."""
from dataclasses import replace

from web import charts, derive
from web.data import Data, field

SIXLAB_TOP = 10


def context(data: Data) -> dict:
    summary = data.datum("bgp_v6_summary", lambda p: p["stats"])
    lengths = data.datum("bgp_v6_summary", lambda p: [r for r in p["prefix_lengths"] if r["prefixes"]])
    ases = data.datum("bgp_v6_ases", lambda p: p["current"])
    return {
        "fib": derive.bgp_current(data),
        "fib_year": derive.bgp_change(data, 365),
        "ases": ases,
        "ases_year": derive.series_change(data, "bgp_v6_ases", "ases", 365),
        "origin_only": field(summary, "origin_only_ases"),
        "transit_only": field(summary, "transit_only_ases"),
        "avg_prefix": field(summary, "average_prefix_length"),
        "avg_path": field(summary, "average_as_path_length"),
        "rib": field(summary, "rib_entries"),
        "table_chart": charts.line_chart(data.datum("bgp_v6_table", lambda p: p["daily"]),
                                         x="date", y="prefixes", title="IPv6 BGP table size", y_title="Prefixes"),
        "ases_chart": charts.line_chart(data.datum("bgp_v6_ases", lambda p: p["daily"]),
                                        x="date", y="ases", title="ASes in the IPv6 routing table", y_title="ASes"),
        "lengths": lengths,
        "lengths_chart": charts.bar_chart(
            None if lengths is None else replace(lengths, value=[{"length": f"/{r['length']}", "prefixes": r["prefixes"]}
                                                                for r in lengths.value]),
            x="length", y="prefixes", title="IPv6 prefixes by prefix length", y_title="Prefixes"),
        "aggregation": data.datum("cidr_report_aggregation", lambda p: p),
        "routeviews": data.datum("routeviews_collectors", lambda p: p),
        "sixlab_top": SIXLAB_TOP,
        "sixlab": data.datum("cisco_6lab", lambda p: sorted(p["countries"], key=lambda c: c["ipv6_users_pct"],
                                                              reverse=True)[:SIXLAB_TOP]),
    }
```

`web/templates/bgp-statistics.html`:

```html
{% extends "base.html" %}
{% from "macros.html" import metric, provenance, unavailable, freshness_table %}
{% block content %}
<h1>IPv6 BGP Routing Statistics</h1>

<section class="metric-row" aria-label="Headline numbers">
  {{ metric("IPv6 prefixes in the routing table", fib, "int",
            note=(fib_year.value | format_value("signed_int")) ~ " in the past year" if fib_year else None) }}
  {{ metric("ASes in the IPv6 routing table", ases, "int",
            note=(ases_year.value | format_value("signed_int")) ~ " in the past year" if ases_year else None) }}
  {{ metric("Origin-only ASes", origin_only, "int") }}
  {{ metric("Transit-only ASes", transit_only, "int") }}
  {{ metric("Average prefix length", avg_prefix, "decimal") }}
  {{ metric("Average AS path length", avg_path, "decimal") }}
</section>

<h2>Growth</h2>
<div class="grid-2">
  <div class="card">{% if table_chart %}<div class="chart">{{ table_chart }}</div>{{ provenance(fib) }}{% else %}{{ unavailable() }}{% endif %}</div>
  <div class="card">{% if ases_chart %}<div class="chart">{{ ases_chart }}</div>{{ provenance(ases) }}{% else %}{{ unavailable() }}{% endif %}</div>
</div>

<h2>Prefix lengths</h2>
{% if lengths %}
<div class="chart">{{ lengths_chart }}</div>
<details class="source"><summary>All prefix lengths</summary>
<div class="table-wrap"><table>
  <thead><tr><th>Length</th><th>Prefixes</th><th>Share of table</th></tr></thead>
  <tbody>{% for r in lengths.value %}<tr><td>/{{ r.length }}</td><td>{{ r.prefixes | format_value("int") }}</td><td>{{ r.share | format_value("pct") if r.share is not none else "—" }}</td></tr>{% endfor %}</tbody>
</table></div>
</details>
{{ provenance(lengths) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>ASes that could shrink the table most by aggregating</h2>
{% if aggregation %}
<p>As of {{ aggregation.value.date }}, the table could shrink from {{ aggregation.value.table.now | format_value("int") }} to {{ aggregation.value.table.aggregated | format_value("int") }} entries if every AS aggregated its announcements. These ASes would contribute most:</p>
<div class="table-wrap"><table>
  <thead><tr><th>AS</th><th>Name</th><th>Prefixes now</th><th>After aggregation</th><th>Reduction</th></tr></thead>
  <tbody>{% for a in aggregation.value.ases %}<tr><td>AS{{ a.asn }}</td><td>{{ a.name or "—" }}</td><td>{{ a.now | format_value("int") }}</td><td>{{ a.aggregated | format_value("int") }}</td><td>{{ a.gain_pct | format_value("pct") }}</td></tr>{% endfor %}</tbody>
</table></div>
{{ provenance(aggregation) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>RouteViews collectors</h2>
{% if routeviews %}
<p>{{ routeviews.value.active }} active RouteViews collectors; latest snapshot {{ routeviews.value.snapshot_date }}.</p>
<div class="table-wrap"><table>
  <thead><tr><th>Collector</th><th>Region</th><th>IPv6 prefixes</th><th>IPv6 peers</th><th>Snapshot</th></tr></thead>
  <tbody>{% for c in routeviews.value.collectors %}<tr><td>{{ c.name }}</td><td>{{ c.rir_region or "—" }}</td><td>{{ c.ipv6_prefixes | format_value("int") }}</td><td>{{ c.ipv6_peers }}</td><td>{{ c.date }}</td></tr>{% endfor %}</tbody>
</table></div>
{{ provenance(routeviews) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>IPv6 users (Cisco 6lab)</h2>
{% if sixlab %}
<ol>{% for c in sixlab.value %}<li>{{ c.name }}: {{ c.ipv6_users_pct | format_value("pct") }}</li>{% endfor %}</ol>
{{ provenance(sixlab) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Data freshness</h2>
{{ freshness_table(freshness) }}
{% endblock %}
```

In `web/build.py`: add `bgp_statistics` to the `from web.pages import ...` line; append `Page("bgp-statistics", "BGP Statistics", bgp_statistics.context),` to `PAGES` and `"BGP Statistics": "bgp-statistics/",` to `LEGACY_PAGES`.

- [ ] **Step 5: Verify** — `uv run pytest tests/test_bgp_statistics.py -q && uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add web/ tests/ && git commit -m "Add BGP Statistics page built from Potaroo, CIDR Report and RouteViews"`

---

### Task 6: Live run and visual check

- [ ] **Step 1:** `uv run python -m collect.run --data-dir data --force --only bgp_v6_ases --only bgp_v6_summary --only cidr_report_aggregation --only routeviews_collectors` → `failed=0`; check `data/cidr_report_aggregation.json` has 30 ASes with names and `data/routeviews_collectors.json` lists dozens of collectors.
- [ ] **Step 2:** build, serve and look at `/bgp-statistics/` at desktop and 375px.
- [ ] **Step 3:** README "Pages so far" adds BGP Statistics. `uv run pytest -q`; commit `"Document the BGP Statistics page"`.
