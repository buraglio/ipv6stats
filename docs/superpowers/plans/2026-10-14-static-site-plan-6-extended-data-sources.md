# Static Site Plan 6: Extended Data Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An Extended Data Sources page with real, dated data on DNS/domains, routing security, measurement networks, interconnection, access networks, government websites and the five registries.

**Architecture:** Seven new monthly sources, two small reference files (carrier ASNs, government domains), one new page `/extended-data-sources/`.

**Spec:** `docs/superpowers/specs/2026-10-14-static-site-migration-design.md`, **Amendment 4 → Extended Data Sources**. ISOC Pulse `/ixp` is not used: its data isn't IPv6-specific (the list allowed it only "if usable").

## Global Constraints

- Work on `staging`; no Claude attribution; check that a PR from `staging` is open before pushing (open one if not).
- Collectors return parsed data or raise. All new sources `MONTH`. Sources that publish their own date reject data older than `MAX_AGE = 3 days` (Hurricane Electric root zone, Team Cymru bogons).
- Hurricane Electric's per-TLD zone files are of very different ages; the page shows each TLD's download date and flags any older than a year. The headline total is labelled as HE's total across those zones.
- Reference files (`reference/carriers.toml`, `reference/government_domains.toml`) hold lists only, never statistics; both have `last_reviewed` and feed the build's 180-day warning.
- Carrier figures come from APNIC's per-network tables already collected (`apnic_economy_detail`); a carrier absent from them shows "not among APNIC's largest networks for its economy".
- Page `/extended-data-sources/`, nav after Historical Trends; legacy `"Extended Data Sources": "extended-data-sources/"`.

## Review Focus

1. **HE's totals mix fresh and years-old zone data.** Per-TLD dates are shown and old zones flagged. Test: `test_old_zone_data_is_flagged`.
2. **A provider ships an HTML error page with HTTP 200** (Cymru bogons, IPv6 Matrix). Every prefix is validated and JSON must have the expected shape. Tests: `test_bogons_reject_non_prefix_lines`, `test_matrix_rejects_changed_format`.
3. **ISOC key absent.** The routing-security source is "not configured", and the page says so per section. Test: `test_routing_security_requires_key`.
4. **Government lookups mostly fail** (resolver trouble): the source fails instead of publishing "no IPv6". Test: `test_government_lookup_failures_fail_the_source`.

---

### Task 1: Hurricane Electric IPv6 progress report

**Files:** Create `collect/sources/he_report.py`, `tests/test_he_report.py`, `tests/fixtures/he/ipv6-progress-report.html`; Modify `collect/sources/__init__.py`

**Interfaces:** source `he_progress`; `parse(page, now=None, min_rows=MIN_ROWS) -> {"tlds", "tlds_ipv6_ns", "tlds_ipv6_glue", "root_zone_processed": "YYYY-MM-DD", "domains": {"domains","a","aaaa","a_glue","aaaa_glue"}, "top_tlds": [{"tld","domains","aaaa","downloaded": "YYYY-MM-DD"}] (20 largest), "url"}`.

- [ ] **Step 1: Record fixture** — `mkdir -p tests/fixtures/he && curl -s https://bgp.he.net/ipv6-progress-report.cgi -o tests/fixtures/he/ipv6-progress-report.html && grep -c "^ *total " tests/fixtures/he/ipv6-progress-report.html` → `1`.

- [ ] **Step 2: Failing tests** — `tests/test_he_report.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import he_report as he
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "he" / "ipv6-progress-report.html").read_text(encoding="utf-8", errors="ignore")
SAMPLE = """Root Zone Processed: Wed Oct 14 10:14:04 2026
<br>Top Level Domains (TLDs): 1437
<br>TLDs with IPv6 nameservers: 1421
<br>TLDs with nameservers with IPv6 glue in the root zone: 1419
<pre>
                     TLD   domains         A      AAAA    A-glue AAAA-glue                downloaded                   processed
                     com 167590972 147699636  30785986   1555630     32630  (Wed Oct 14 03:48:52 2026)  (Wed Oct 14 10:13:27 2026)
                      de  13155766   6375832   2330359    398186       114  (Wed Jan 20 01:22:39 2010)  (Wed Oct 14 10:13:40 2026)
                   total 180746738 154075468  33116345   1953816     32744
</pre>"""


def test_parse_sample():
    p = he.parse(SAMPLE, min_rows=1)
    assert (p["tlds"], p["tlds_ipv6_ns"], p["tlds_ipv6_glue"]) == (1437, 1421, 1419)
    assert p["root_zone_processed"] == "2026-10-14"
    assert p["domains"] == {"domains": 180746738, "a": 154075468, "aaaa": 33116345, "a_glue": 1953816, "aaaa_glue": 32744}
    assert p["top_tlds"][1] == {"tld": "de", "domains": 13155766, "aaaa": 2330359, "downloaded": "2010-01-20"}


def test_parse_recorded_page():
    p = he.parse(FIXTURE)
    assert p["domains"]["aaaa"] > 1_000_000 and len(p["top_tlds"]) == he.TOP


def test_rejects_stale_or_changed_report():
    with pytest.raises(ValueError, match="stopped updating"):
        he.parse(SAMPLE, now=datetime(2026, 10, 20, tzinfo=timezone.utc), min_rows=1)
    with pytest.raises(ValueError, match="HE report format changed"):
        he.parse("<html>maintenance</html>")


def test_fetch():
    assert SOURCES["he_progress"].fetch(make_ctx(routes={he.URL: FakeResponse(text=FIXTURE)}))["tlds"]
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_he_report.py -q` → FAIL (`ImportError`).

- [ ] **Step 4: Implement** — `collect/sources/he_report.py`:

```python
"""Hurricane Electric's global IPv6 deployment progress report: TLD nameservers and AAAA domains."""
import re
from datetime import datetime, timedelta

from collect.registry import MONTH, Context, source

URL = "https://bgp.he.net/ipv6-progress-report.cgi"
DATE = r"(\w{3} \w{3} +\d{1,2} [\d:]+ \d{4})"
STATS = {
    "tlds": re.compile(r"Top Level Domains \(TLDs\): (\d+)"),
    "tlds_ipv6_ns": re.compile(r"TLDs with IPv6 nameservers: (\d+)"),
    "tlds_ipv6_glue": re.compile(r"TLDs with nameservers with IPv6 glue in the root zone: (\d+)"),
}
PROCESSED = re.compile(r"Root Zone Processed: " + DATE)
# <pre> table: TLD domains A AAAA A-glue AAAA-glue (downloaded) (processed)
ROW = re.compile(r"^\s*([a-z0-9-]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+\(" + DATE + r"\)", re.M)
TOTAL = re.compile(r"^\s*total\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.M)
MIN_ROWS = 100
TOP = 20
MAX_AGE = timedelta(days=3)


def _date(text: str) -> str:
    return datetime.strptime(" ".join(text.split()), "%a %b %d %H:%M:%S %Y").date().isoformat()


def parse(page: str, now: datetime | None = None, min_rows: int = MIN_ROWS) -> dict:
    stats = {k: int(m.group(1)) for k, rx in STATS.items() if (m := rx.search(page))}
    processed, total = PROCESSED.search(page), TOTAL.search(page)
    rows = [{"tld": t, "domains": int(d), "aaaa": int(aaaa), "downloaded": _date(dl)}
            for t, d, _a, aaaa, _ag, _aaaag, dl in ROW.findall(page)]
    if len(stats) < len(STATS) or not processed or not total or len(rows) < min_rows:
        raise ValueError(f"HE report format changed: stats={sorted(stats)}, rows={len(rows)}")
    processed_date = _date(processed.group(1))
    if now is not None and now.date() - datetime.fromisoformat(processed_date).date() > MAX_AGE:
        raise ValueError(f"HE report stopped updating: root zone processed {processed_date}")
    domains = dict(zip(("domains", "a", "aaaa", "a_glue", "aaaa_glue"), map(int, total.groups())))
    rows.sort(key=lambda r: r["domains"], reverse=True)
    return {**stats, "root_zone_processed": processed_date, "domains": domains, "top_tlds": rows[:TOP], "url": URL}


@source("he_progress", MONTH, title="Hurricane Electric IPv6 progress report", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text, now=ctx.now)
```

Register `he_report` in `collect/sources/__init__.py`.

- [ ] **Step 5: Verify** — `uv run pytest tests/test_he_report.py -q && uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add collect/sources/ tests/test_he_report.py tests/fixtures/he/ && git commit -m "Collect Hurricane Electric's IPv6 progress report"`

---

### Task 2: Team Cymru IPv6 bogons

**Files:** Create `collect/sources/cymru.py`, `tests/test_cymru.py`, `tests/fixtures/cymru/fullbogons-ipv6.txt`; Modify `collect/sources/__init__.py`

**Interfaces:** source `cymru_bogons`; `parse(text, now=None, min_prefixes=MIN_PREFIXES) -> {"prefixes": int, "updated": "YYYY-MM-DD", "url"}`.

- [ ] **Step 1: Record a trimmed fixture** — `mkdir -p tests/fixtures/cymru && curl -s https://team-cymru.org/Services/Bogons/fullbogons-ipv6.txt | head -n 1500 > tests/fixtures/cymru/fullbogons-ipv6.txt && head -1 tests/fixtures/cymru/fullbogons-ipv6.txt` → `# last updated …`.

- [ ] **Step 2: Failing tests** — `tests/test_cymru.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import cymru
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "cymru" / "fullbogons-ipv6.txt").read_text()
SAMPLE = "# last updated 1791996901 (Wed Oct 14 16:55:01 2026 GMT)\n# Know your network!\n::/10\n100::/8\n"


def test_parse_sample():
    assert cymru.parse(SAMPLE, min_prefixes=1) == {"prefixes": 2, "updated": "2026-10-14", "url": cymru.HOME}


def test_parse_recorded_file():
    assert cymru.parse(FIXTURE)["prefixes"] > 1000


def test_bogons_reject_non_prefix_lines():
    with pytest.raises(ValueError, match="not a prefix"):
        cymru.parse(SAMPLE + "<html>error</html>\n", min_prefixes=1)


def test_rejects_stale_list():
    with pytest.raises(ValueError, match="stopped updating"):
        cymru.parse(SAMPLE, now=datetime(2026, 10, 20, tzinfo=timezone.utc), min_prefixes=1)


def test_fetch():
    assert SOURCES["cymru_bogons"].fetch(make_ctx(routes={cymru.URL: FakeResponse(text=FIXTURE)}))["prefixes"]
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_cymru.py -q` → FAIL (`ImportError`).

- [ ] **Step 4: Implement** — `collect/sources/cymru.py`:

```python
"""Team Cymru's full IPv6 bogon list: address space that should not appear in the routing table."""
import ipaddress
import re
from datetime import datetime, timedelta, timezone

from collect.registry import MONTH, Context, source

URL = "https://team-cymru.org/Services/Bogons/fullbogons-ipv6.txt"
HOME = "https://www.team-cymru.com/bogon-reference"
UPDATED = re.compile(r"#\s*last updated (\d+)")
MIN_PREFIXES = 1000
MAX_AGE = timedelta(days=3)


def parse(text: str, now: datetime | None = None, min_prefixes: int = MIN_PREFIXES) -> dict:
    stamp = UPDATED.search(text)
    if not stamp:
        raise ValueError("Cymru bogon list format changed: no 'last updated' line")
    updated = datetime.fromtimestamp(int(stamp.group(1)), timezone.utc)
    if now is not None and now - updated > MAX_AGE:
        raise ValueError(f"Cymru bogon list stopped updating: last updated {updated.date()}")
    prefixes = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            ipaddress.IPv6Network(line, strict=False)
        except ValueError as exc:
            raise ValueError(f"Cymru bogon list format changed: not a prefix: {line[:60]!r}") from exc
        prefixes += 1
    if prefixes < min_prefixes:
        raise ValueError(f"Cymru bogon list format changed: only {prefixes} prefixes")
    return {"prefixes": prefixes, "updated": updated.date().isoformat(), "url": HOME}


@source("cymru_bogons", MONTH, title="Team Cymru IPv6 full bogons", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text, now=ctx.now)
```

Register `cymru` in `collect/sources/__init__.py`.

- [ ] **Step 5: Verify** — `uv run pytest tests/test_cymru.py -q && uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add collect/sources/ tests/test_cymru.py tests/fixtures/cymru/ && git commit -m "Collect Team Cymru's IPv6 bogon list"`

---

### Task 3: RIPE Atlas probes and PeeringDB networks

**Files:** Create `collect/sources/atlas.py`, `collect/sources/peeringdb.py`, `tests/test_atlas_peeringdb.py`; Modify `collect/sources/__init__.py`

**Interfaces:** source `ripe_atlas_probes` → `{"connected", "ipv6_works", "ipv4_works", "url"}`; source `peeringdb_networks` → `{"networks", "ipv6_networks", "url"}`.

- [ ] **Step 1: Failing tests** — `tests/test_atlas_peeringdb.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import atlas, peeringdb
from tests.fakes import FakeResponse, make_ctx


def atlas_routes(connected=15265, v6=7075, v4=14000):
    return {f"{atlas.API}&tags=system-ipv6-works": FakeResponse(json_data={"count": v6, "results": []}),
            f"{atlas.API}&tags=system-ipv4-works": FakeResponse(json_data={"count": v4, "results": []}),
            atlas.API: FakeResponse(json_data={"count": connected, "results": []})}


def test_atlas_counts():
    assert SOURCES["ripe_atlas_probes"].fetch(make_ctx(routes=atlas_routes())) == {
        "connected": 15265, "ipv6_works": 7075, "ipv4_works": 14000, "url": atlas.HOME}


def test_atlas_rejects_impossible_counts():
    with pytest.raises(ValueError, match="RIPE Atlas"):
        SOURCES["ripe_atlas_probes"].fetch(make_ctx(routes=atlas_routes(connected=10, v6=20)))


def test_peeringdb_counts(monkeypatch):
    monkeypatch.setattr(peeringdb, "MIN_NETWORKS", 1)
    body = {"data": [{"info_ipv6": True}, {"info_ipv6": False}, {"info_ipv6": True}]}
    payload = SOURCES["peeringdb_networks"].fetch(make_ctx(routes={peeringdb.API: FakeResponse(json_data=body)}))
    assert (payload["networks"], payload["ipv6_networks"]) == (3, 2)


def test_peeringdb_rejects_changed_format():
    with pytest.raises(ValueError, match="PeeringDB"):
        SOURCES["peeringdb_networks"].fetch(make_ctx(routes={peeringdb.API: FakeResponse(json_data={"data": []})}))
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_atlas_peeringdb.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `collect/sources/atlas.py`:

```python
"""RIPE Atlas: connected probes, and how many have working IPv6 and IPv4."""
from collect.registry import MONTH, Context, source

API = "https://atlas.ripe.net/api/v2/probes/?status=1&page_size=1"
HOME = "https://atlas.ripe.net/"


def _count(ctx: Context, url: str) -> int:
    response = ctx.session.get(url, timeout=60)
    response.raise_for_status()
    return int(response.json()["count"])


@source("ripe_atlas_probes", MONTH, title="RIPE Atlas probes (API)", url=HOME)
def fetch(ctx: Context) -> dict:
    connected = _count(ctx, API)
    v6 = _count(ctx, f"{API}&tags=system-ipv6-works")
    v4 = _count(ctx, f"{API}&tags=system-ipv4-works")
    if not connected or v6 > connected or v4 > connected:
        raise ValueError(f"RIPE Atlas API returned impossible counts: {connected}, {v6}, {v4}")
    return {"connected": connected, "ipv6_works": v6, "ipv4_works": v4, "url": HOME}
```

`collect/sources/peeringdb.py`:

```python
"""PeeringDB: networks that list IPv6 traffic (info_ipv6)."""
from collect.registry import MONTH, Context, source

API = "https://www.peeringdb.com/api/net?fields=info_ipv6&depth=0"
HOME = "https://www.peeringdb.com/"
MIN_NETWORKS = 10_000


@source("peeringdb_networks", MONTH, title="PeeringDB networks (API)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(API, timeout=120)
    response.raise_for_status()
    networks = response.json().get("data", [])
    if len(networks) < MIN_NETWORKS:
        raise ValueError(f"PeeringDB API format changed: {len(networks)} networks")
    return {"networks": len(networks), "ipv6_networks": sum(1 for n in networks if n.get("info_ipv6")), "url": HOME}
```

Register `atlas` and `peeringdb` in `collect/sources/__init__.py`.

- [ ] **Step 4: Verify** — `uv run pytest tests/test_atlas_peeringdb.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/sources/ tests/test_atlas_peeringdb.py && git commit -m "Collect RIPE Atlas probe and PeeringDB network IPv6 counts"`

---

### Task 4: ISOC Pulse routing security (ROA coverage, ROV)

**Files:** Create `collect/sources/isoc_routing.py`, `tests/test_isoc_routing.py`; Modify `collect/sources/__init__.py`

**Interfaces:** source `isoc_routing` (`requires_env=("ISOC_PULSE_API_KEY",)`); payload `{"roa_ipv6": parse_series, "roa_ipv4": parse_series, "rov": {"latest": {"date","partial","full"}, "series": [...]}, "url"}` (percent values).

- [ ] **Step 1: Failing tests** — `tests/test_isoc_routing.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import isoc, isoc_routing as ir
from tests.fakes import FakeResponse, make_ctx

KEY = {"ISOC_PULSE_API_KEY": "k"}
ROA6 = {"data": [{"date": "2026-10-12", "value": 0.7324}, {"date": "2026-10-11", "value": 0.73}]}
ROA4 = {"data": [{"date": "2026-10-12", "value": 0.648}]}
ROV = {"data": [{"date": "2026-10-10", "partial": 0.9424, "full": 0.3487}, {"date": "2021-12-24", "partial": 0.3006, "full": 0.0625}]}


def routes(rov=ROV):
    return {f"{isoc.API}/roa?ip_version=6": FakeResponse(json_data=ROA6),
            f"{isoc.API}/roa?ip_version=4": FakeResponse(json_data=ROA4),
            f"{isoc.API}/rov": FakeResponse(json_data=rov)}


def test_fetch_routing_security():
    p = SOURCES["isoc_routing"].fetch(make_ctx(routes=routes(), env=KEY))
    assert p["roa_ipv6"]["latest"] == {"date": "2026-10-12", "value": 73.24}
    assert p["roa_ipv4"]["latest"]["value"] == 64.8
    assert p["rov"]["latest"] == {"date": "2026-10-10", "partial": 94.24, "full": 34.87}
    assert p["rov"]["series"][0]["date"] == "2021-12-24"


def test_routing_security_requires_key():
    assert SOURCES["isoc_routing"].requires_env == ("ISOC_PULSE_API_KEY",)


def test_rov_rejects_changed_format():
    with pytest.raises(ValueError, match="ISOC Pulse response format changed"):
        SOURCES["isoc_routing"].fetch(make_ctx(routes=routes(rov={"data": [{"date": "2026-10-10", "value": 0.5}]}), env=KEY))
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_isoc_routing.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `collect/sources/isoc_routing.py`:

```python
"""Internet Society Pulse routing security: ROA coverage by IP version, and ROV adoption."""
from collect.registry import MONTH, Context, source
from collect.sources.isoc import API, HOME, parse_series


def _get(ctx: Context, path: str) -> dict:
    headers = {"Authorization": f"Bearer {ctx.env['ISOC_PULSE_API_KEY'].strip()}"}
    response = ctx.session.get(f"{API}{path}", headers=headers, timeout=60)
    if not response.ok:
        raise ValueError(f"ISOC Pulse API HTTP {response.status_code} for {path}: {response.text[:200]}")
    return response.json()


def parse_rov(body: dict) -> dict:
    rows = body.get("data") if isinstance(body, dict) else None
    if not rows or not all({"date", "partial", "full"} <= set(r) for r in rows):
        raise ValueError("ISOC Pulse response format changed: ROV rows need date, partial and full")
    series = sorted(({"date": r["date"], "partial": round(100 * float(r["partial"]), 2),
                      "full": round(100 * float(r["full"]), 2)} for r in rows), key=lambda r: r["date"])
    return {"latest": series[-1], "series": series}


@source("isoc_routing", MONTH, title="Internet Society Pulse routing security (API)", url=HOME,
        requires_env=("ISOC_PULSE_API_KEY",))
def fetch(ctx: Context) -> dict:
    return {"roa_ipv6": parse_series(_get(ctx, "/roa?ip_version=6")),
            "roa_ipv4": parse_series(_get(ctx, "/roa?ip_version=4")),
            "rov": parse_rov(_get(ctx, "/rov")), "url": HOME}
```

Register `isoc_routing` in `collect/sources/__init__.py`.

- [ ] **Step 4: Verify** — `uv run pytest tests/test_isoc_routing.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/sources/ tests/test_isoc_routing.py && git commit -m "Collect ISOC Pulse ROA coverage and ROV adoption"`

---

### Task 5: IPv6 Matrix host crawl

**Files:** Create `collect/sources/ipv6matrix.py`, `tests/test_ipv6matrix.py`; Modify `collect/sources/__init__.py`

**Interfaces:** source `ipv6matrix_hosts`; `parse(body) -> {"latest": {"date","hosts","hosts_ipv6","share"}, "series": [{"date","share"}], "countries": [{"code","hosts","hosts_ipv6","share"}] (20 with most hosts, ISO-like codes only), "url"}`.

- [ ] **Step 1: Failing tests** — `tests/test_ipv6matrix.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import ipv6matrix as m
from tests.fakes import FakeResponse, make_ctx

BODY = {
    "Sat Aug 21 2010 00:00:00 GMT+0000 (Coordinated Universal Time)": {"US": {"hosts": 100, "hosts6": 1}},
    "Sun Oct 04 2026 00:00:00 GMT+0000 (Coordinated Universal Time)": {
        "US": {"hosts": 1000, "hosts6": 600}, "DE": {"hosts": 500, "hosts6": 200}, "A1": {"hosts": 50, "hosts6": 0}},
}


def test_parse_latest_crawl_and_series():
    p = m.parse(BODY)
    assert p["latest"] == {"date": "2026-10-04", "hosts": 1550, "hosts_ipv6": 800, "share": 51.6}
    assert [s["date"] for s in p["series"]] == ["2010-08-21", "2026-10-04"]
    assert [c["code"] for c in p["countries"]] == ["US", "DE"]          # A1 (anonymous proxy) left out
    assert p["countries"][0]["share"] == 60.0


def test_matrix_rejects_changed_format():
    with pytest.raises(ValueError, match="IPv6 Matrix format changed"):
        m.parse({"results": []})


def test_fetch():
    assert SOURCES["ipv6matrix_hosts"].fetch(make_ctx(routes={m.URL: FakeResponse(json_data=BODY)}))["latest"]
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_ipv6matrix.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `collect/sources/ipv6matrix.py`:

```python
"""IPv6 Matrix: share of crawled hosts reachable over IPv6, globally and by country."""
import re
from datetime import datetime

from collect.registry import MONTH, Context, source

URL = "https://ipv6matrix.com/json/hosts/group-country"
HOME = "https://ipv6matrix.com/"
COUNTRY = re.compile(r"^[A-Z]{2}$")
NOT_COUNTRIES = {"A1", "A2", "AP", "EU"}  # GeoIP pseudo-codes
TOP = 20


def _share(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def parse(body: dict) -> dict:
    if not isinstance(body, dict) or not body:
        raise ValueError("IPv6 Matrix format changed: expected crawls keyed by date")
    crawls = []
    for key, countries in body.items():
        try:
            day = datetime.strptime(key[:15], "%a %b %d %Y").date().isoformat()
            hosts = sum(int(c["hosts"]) for c in countries.values())
            hosts6 = sum(int(c["hosts6"]) for c in countries.values())
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"IPv6 Matrix format changed: {exc}") from exc
        crawls.append((day, hosts, hosts6, countries))
    crawls.sort()
    day, hosts, hosts6, countries = crawls[-1]
    table = sorted(({"code": code, "hosts": int(c["hosts"]), "hosts_ipv6": int(c["hosts6"]),
                     "share": _share(int(c["hosts6"]), int(c["hosts"]))}
                    for code, c in countries.items() if COUNTRY.match(code) and code not in NOT_COUNTRIES),
                   key=lambda c: c["hosts"], reverse=True)[:TOP]
    return {"latest": {"date": day, "hosts": hosts, "hosts_ipv6": hosts6, "share": _share(hosts6, hosts)},
            "series": [{"date": d, "share": _share(h6, h)} for d, h, h6, _ in crawls],
            "countries": table, "url": HOME}


@source("ipv6matrix_hosts", MONTH, title="IPv6 Matrix host crawl (API)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=120)
    response.raise_for_status()
    return parse(response.json())
```

Register `ipv6matrix` in `collect/sources/__init__.py`.

- [ ] **Step 4: Verify** — `uv run pytest tests/test_ipv6matrix.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add collect/sources/ tests/test_ipv6matrix.py && git commit -m "Collect IPv6 Matrix host crawl results"`

---

### Task 6: Reference lists and the government website check

**Files:** Create `reference/carriers.toml`, `reference/government_domains.toml`, `collect/sources/government.py`, `tests/test_government.py`; Modify `web/reference.py` (loaders + warnings), `web/build.py` (warnings), `collect/sources/__init__.py`; Test `tests/test_cloud_reference.py` (append)

**Interfaces:** `web.reference.load_carriers() -> {"last_reviewed", "carrier": [{"name","asn","country"}]}`; `load_government() -> {"last_reviewed", "group": [{"name","domains"}]}`; `list_reviews(now) -> list[str]` (180-day warnings for both); source `government_domains` → `{"groups": [{"name","domains": [{"domain","status"}],"with_ipv6","checked"}], "unknown", "total", "url"}`; `MAX_UNKNOWN = 0.1`.

- [ ] **Step 1: Create the reference files** — `reference/carriers.toml`:

```toml
# Access networks shown on the Extended Data Sources page. Lists only: their IPv6 figures
# come from APNIC's per-network measurements. Update last_reviewed when you check the list.
last_reviewed = "2026-10-14"

[[carrier]]
name = "T-Mobile USA"
asn = 21928
country = "US"

[[carrier]]
name = "Verizon Wireless"
asn = 22394
country = "US"

[[carrier]]
name = "AT&T Mobility"
asn = 20057
country = "US"

[[carrier]]
name = "Comcast"
asn = 7922
country = "US"

[[carrier]]
name = "Reliance Jio"
asn = 55836
country = "IN"

[[carrier]]
name = "Bharti Airtel"
asn = 9498
country = "IN"

[[carrier]]
name = "Deutsche Telekom"
asn = 3320
country = "DE"

[[carrier]]
name = "Vodafone Germany"
asn = 3209
country = "DE"

[[carrier]]
name = "Orange France"
asn = 3215
country = "FR"

[[carrier]]
name = "BT / EE"
asn = 2856
country = "GB"

[[carrier]]
name = "NTT Docomo"
asn = 9605
country = "JP"

[[carrier]]
name = "SoftBank"
asn = 17676
country = "JP"

[[carrier]]
name = "Telstra"
asn = 1221
country = "AU"

[[carrier]]
name = "SK Telecom"
asn = 9644
country = "KR"

[[carrier]]
name = "KT"
asn = 4766
country = "KR"
```

`reference/government_domains.toml`:

```toml
# Government websites checked for IPv6 (AAAA on the domain or www.) by
# collect/sources/government.py. Lists only. Update last_reviewed when you check the list.
last_reviewed = "2026-10-14"

[[group]]
name = "US Federal"
domains = ["whitehouse.gov", "nasa.gov", "cdc.gov", "irs.gov", "census.gov", "defense.gov", "state.gov",
           "treasury.gov", "dhs.gov", "fbi.gov", "nih.gov", "noaa.gov"]

[[group]]
name = "European Union"
domains = ["europa.eu", "ec.europa.eu", "europarl.europa.eu", "consilium.europa.eu", "curia.europa.eu", "eeas.europa.eu"]

[[group]]
name = "United Kingdom"
domains = ["gov.uk", "nhs.uk", "hmrc.gov.uk", "police.uk", "parliament.uk", "judiciary.gov.uk"]

[[group]]
name = "Australia"
domains = ["australia.gov.au", "ato.gov.au", "aph.gov.au", "abs.gov.au", "austrade.gov.au", "defence.gov.au"]
```

- [ ] **Step 2: Failing tests** — `tests/test_government.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import government as gov
from tests.fakes import make_ctx

LIST = {"group": [{"name": "Test", "domains": ["a.example", "b.example", "c.example"]}]}


def test_measure_apex_or_www():
    result = gov.measure(LIST, {"a.example", "www.b.example"}.__contains__,
                         {"a.example", "b.example", "c.example", "www.b.example"}.__contains__)
    g = result["groups"][0]
    assert [d["status"] for d in g["domains"]] == ["ipv6", "ipv6", "ipv4_only"]
    assert (g["with_ipv6"], g["checked"]) == (2, 3)


def test_government_lookup_failures_fail_the_source():
    with pytest.raises(ValueError, match="lookups failed"):
        gov.measure(LIST, lambda n: None, lambda n: None)


def test_fetch_reads_reference_list():
    hosts = {d for g in gov.load_list()["group"] for d in g["domains"]}
    result = SOURCES["government_domains"].fetch(make_ctx(aaaa=hosts))
    assert result["total"] == len(hosts) and result["unknown"] == 0
```

Append to `tests/test_cloud_reference.py`:

```python


def test_list_reference_files_load_and_have_no_statistics():
    carriers, gov = reference.load_carriers(), reference.load_government()
    assert carriers["carrier"][0]["asn"] == 21928 and gov["group"][0]["domains"]
    for path in (reference.CARRIERS_FILE, reference.GOVERNMENT_FILE):
        assert "%" not in path.read_text()


def test_list_reviews_warn_when_old():
    old = datetime(2027, 6, 1, tzinfo=timezone.utc)
    assert len(reference.list_reviews(old)) == 2
    assert reference.list_reviews(datetime(2026, 10, 15, tzinfo=timezone.utc)) == []
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_government.py tests/test_cloud_reference.py -q` → FAIL.

- [ ] **Step 4: Implement** — `collect/sources/government.py`:

```python
"""Whether government websites publish IPv6 (AAAA on the domain or its www. name).

The list lives in reference/government_domains.toml. Measured from GitHub's runners (no IPv6),
so this shows published IPv6, not end-to-end reachability.
"""
import tomllib
from pathlib import Path

from collect.registry import MONTH, Context, source
from collect.sources.cloud_endpoints import check

LIST_FILE = Path(__file__).resolve().parents[2] / "reference" / "government_domains.toml"
METHOD = "https://github.com/buraglio/ipv6stats/blob/main/collect/sources/government.py"
MAX_UNKNOWN = 0.1


def load_list(path: Path = LIST_FILE) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _status(domain: str, has_aaaa, has_a) -> str:
    apex = check(domain, has_aaaa, has_a)
    if apex == "ipv6":
        return apex
    www = check(f"www.{domain}", has_aaaa, has_a)
    if www == "ipv6":
        return www
    return "ipv4_only" if "ipv4_only" in (apex, www) else "unknown"


def measure(listing: dict, has_aaaa, has_a) -> dict:
    groups, unknown, total = [], 0, 0
    for group in listing["group"]:
        domains = [{"domain": d, "status": _status(d, has_aaaa, has_a)} for d in group["domains"]]
        unknown += sum(d["status"] == "unknown" for d in domains)
        total += len(domains)
        groups.append({"name": group["name"], "domains": domains,
                       "with_ipv6": sum(d["status"] == "ipv6" for d in domains),
                       "checked": sum(d["status"] != "unknown" for d in domains)})
    if unknown > MAX_UNKNOWN * total:
        raise ValueError(f"{unknown} of {total} government domain lookups failed; not trusting the result")
    return {"groups": groups, "unknown": unknown, "total": total, "url": METHOD}


@source("government_domains", MONTH, title="Government websites with IPv6 (AAAA lookups, measured)", url=METHOD)
def fetch(ctx: Context) -> dict:
    return measure(load_list(), ctx.has_aaaa, ctx.has_a)
```

In `web/reference.py`, add after `CLOUD_FILE`:

```python
CARRIERS_FILE = CLOUD_FILE.parent / "carriers.toml"
GOVERNMENT_FILE = CLOUD_FILE.parent / "government_domains.toml"
```

and at the end of the file:

```python


def _load_list(path: Path, items: str) -> dict:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    try:
        date.fromisoformat(data["last_reviewed"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{Path(path).name}: missing or invalid last_reviewed") from exc
    if not data.get(items):
        raise ValueError(f"{Path(path).name}: no [[{items}]] entries")
    return data


def load_carriers(path: Path = CARRIERS_FILE) -> dict:
    return _load_list(path, "carrier")


def load_government(path: Path = GOVERNMENT_FILE) -> dict:
    return _load_list(path, "group")


def list_reviews(now: datetime, max_age_days: int = MAX_AGE_DAYS) -> list[str]:
    warnings = []
    for path, loader in ((CARRIERS_FILE, load_carriers), (GOVERNMENT_FILE, load_government)):
        reviewed = date.fromisoformat(loader()["last_reviewed"])
        if (age := (now.date() - reviewed).days) > max_age_days:
            warnings.append(f"{path.name}: last reviewed {reviewed} ({age} days ago)")
    return warnings
```

In `web/build.py`, change the final return to `return (check_reference_dates(TEMPLATES, now) + reference.stale_reviews(reference.load_cloud_providers(), now) + reference.list_reviews(now))`. Register `government` in `collect/sources/__init__.py`.

- [ ] **Step 5: Verify** — `uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add reference/ collect/sources/ web/ tests/ && git commit -m "Add carrier and government reference lists and the government website IPv6 check"`

---

### Task 7: Extended Data Sources page

**Files:** Create `web/pages/extended_data_sources.py`, `web/templates/extended-data-sources.html`, `tests/test_extended_data_sources.py`; Modify `web/build.py`, `tests/sample_data.py`

**Interfaces:** `context(data) -> dict`; `OLD_ZONE_DAYS = 365`; `RIR_TOP = 10`.

- [ ] **Step 1: Sample data** — add to `PAYLOADS`:

```python
    "he_progress": {
        "tlds": 1437, "tlds_ipv6_ns": 1421, "tlds_ipv6_glue": 1419, "root_zone_processed": "2026-10-14",
        "domains": {"domains": 315029019, "a": 241264321, "aaaa": 51978468, "a_glue": 3954051, "aaaa_glue": 278080},
        "top_tlds": [{"tld": "com", "domains": 167590972, "aaaa": 30785986, "downloaded": "2026-10-14"},
                     {"tld": "de", "domains": 13155766, "aaaa": 2330359, "downloaded": "2010-01-20"}],
        "url": "https://bgp.he.net/ipv6-progress-report.cgi",
    },
    "cymru_bogons": {"prefixes": 157946, "updated": "2026-10-14", "url": "https://www.team-cymru.com/bogon-reference"},
    "ripe_atlas_probes": {"connected": 15265, "ipv6_works": 7075, "ipv4_works": 14000, "url": "https://atlas.ripe.net/"},
    "peeringdb_networks": {"networks": 35630, "ipv6_networks": 21723, "url": "https://www.peeringdb.com/"},
    "isoc_routing": {
        "roa_ipv6": {"latest": {"date": "2026-10-12", "value": 73.24}, "series": [{"date": "2026-10-12", "value": 73.24}]},
        "roa_ipv4": {"latest": {"date": "2026-10-12", "value": 64.8}, "series": [{"date": "2026-10-12", "value": 64.8}]},
        "rov": {"latest": {"date": "2026-10-10", "partial": 94.24, "full": 34.87},
                "series": [{"date": "2026-10-10", "partial": 94.24, "full": 34.87}]},
        "url": "https://pulse.internetsociety.org/",
    },
    "ipv6matrix_hosts": {
        "latest": {"date": "2026-10-04", "hosts": 5281926, "hosts_ipv6": 2890607, "share": 54.7},
        "series": [{"date": "2010-08-21", "share": 1.0}, {"date": "2026-10-04", "share": 54.7}],
        "countries": [{"code": "US", "hosts": 1000000, "hosts_ipv6": 600000, "share": 60.0}],
        "url": "https://ipv6matrix.com/",
    },
    "government_domains": {
        "groups": [{"name": "US Federal", "with_ipv6": 1, "checked": 2,
                    "domains": [{"domain": "nasa.gov", "status": "ipv6"}, {"domain": "irs.gov", "status": "ipv4_only"}]}],
        "unknown": 0, "total": 2, "url": "https://github.com/buraglio/ipv6stats",
    },
```

- [ ] **Step 2: Failing tests** — `tests/test_extended_data_sources.py`:

```python
from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "extended-data-sources" / "index.html").read_text()


def test_domains_and_dns(tmp_path):
    _, html = render(tmp_path)
    assert "1,421 of 1,437" in html and "51,978,468" in html and "315,029,019" in html


def test_old_zone_data_is_flagged(tmp_path):
    _, html = render(tmp_path)
    row = html[html.index("<td>de</td>"):html.index("</tr>", html.index("<td>de</td>"))]
    assert "zone data from 2010-01-20" in row


def test_routing_security_and_measurement(tmp_path):
    _, html = render(tmp_path)
    for text in ("73.2%", "64.8%", "94.2%", "34.9%", "157,946", "7,075 of 15,265", "21,723 of 35,630", "54.7%"):
        assert text in html, text


def test_access_networks_join_apnic(tmp_path):
    _, html = render(tmp_path)
    nets = html[html.index("Access networks"):]
    assert "Comcast" in nets and "85.3%" in nets                   # AS7922 is in the US network table
    assert "not among APNIC" in nets                               # e.g. T-Mobile isn't in the sample


def test_government_and_registries(tmp_path):
    _, html = render(tmp_path)
    assert "1 of 2" in html and "nasa.gov" in html
    assert "RIPE NCC" in html and "DE" in html


def test_routing_security_unavailable_without_key(tmp_path):
    _, html = render(tmp_path, not_configured=("isoc_routing",))
    sec = html[html.index("Routing security"):html.index("Measurement networks")]
    assert "— source unavailable" in sec


def test_nav_and_legacy(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">Extended Data Sources' in html
    assert '"Extended Data Sources": "extended-data-sources/"' in (out / "index.html").read_text()
```

- [ ] **Step 3: Run to verify failure** — `uv run pytest tests/test_extended_data_sources.py -q` → FAIL.

- [ ] **Step 4: Implement** — `web/pages/extended_data_sources.py`:

```python
"""Extended Data Sources: DNS, routing security, measurement networks, interconnection,
access networks, government websites and the five registries."""
from dataclasses import replace
from datetime import date

from web import charts, derive, reference
from web.data import Data

OLD_ZONE_DAYS = 365
RIR_TOP = 10


def _carriers(data: Data):
    listing = reference.load_carriers()
    detail = data.datum("apnic_economy_detail", lambda p: {
        n["asn"]: n for e in p["economies"].values() for n in e["networks"]})
    rows = [{**c, "apnic": detail.value.get(c["asn"]) if detail else None} for c in listing["carrier"]]
    return rows, detail, listing["last_reviewed"]


def context(data: Data) -> dict:
    he = data.datum("he_progress", lambda p: p)
    today = data.now.date()
    tlds = None if he is None else [
        {**t, "old": (today - date.fromisoformat(t["downloaded"])).days > OLD_ZONE_DAYS} for t in he.value["top_tlds"]]
    routing = data.datum("isoc_routing", lambda p: p)
    matrix = data.datum("ipv6matrix_hosts", lambda p: p)
    carriers, carrier_detail, carriers_reviewed = _carriers(data)
    return {
        "he": he, "tlds": tlds,
        "routing": routing,
        "roa_chart": charts.multi_line_chart(
            None if routing is None else replace(routing, value=[
                {"name": "IPv6 address space covered by ROAs", "points": [{"x": p["date"], "y": p["value"]} for p in routing.value["roa_ipv6"]["series"]]},
                {"name": "IPv4 address space covered by ROAs", "points": [{"x": p["date"], "y": p["value"]} for p in routing.value["roa_ipv4"]["series"]]}]),
            title="RPKI ROA coverage", y_title="Percent"),
        "bogons": data.datum("cymru_bogons", lambda p: p),
        "atlas": data.datum("ripe_atlas_probes", lambda p: p),
        "matrix": matrix,
        "matrix_chart": charts.line_chart(None if matrix is None else replace(matrix, value=matrix.value["series"]),
                                          x="date", y="share", title="Crawled hosts reachable over IPv6 (IPv6 Matrix)",
                                          y_title="Percent"),
        "peeringdb": data.datum("peeringdb_networks", lambda p: p),
        "carriers": carriers, "carrier_detail": carrier_detail, "carriers_reviewed": carriers_reviewed,
        "government": data.datum("government_domains", lambda p: p),
        "government_reviewed": reference.load_government()["last_reviewed"],
        "rirs": derive.rir_comparison(data),
        "rir_details": [(name, data.datum(key, lambda p: p)) for key, name in derive.RIR_SOURCES],
        "rir_top": RIR_TOP,
    }
```

`web/templates/extended-data-sources.html`:

```html
{% extends "base.html" %}
{% from "macros.html" import provenance, unavailable, freshness_table %}
{% block content %}
<h1>Extended IPv6 Data Sources</h1>

<h2>Domains and DNS</h2>
{% if he %}
<p>{{ he.value.tlds_ipv6_ns | format_value("int") }} of {{ he.value.tlds | format_value("int") }} top-level domains have IPv6 nameservers, and {{ he.value.tlds_ipv6_glue | format_value("int") }} have IPv6 glue in the root zone (root zone processed {{ he.value.root_zone_processed }}).</p>
<p>Across the zone files Hurricane Electric can download, {{ he.value.domains.aaaa | format_value("int") }} of {{ he.value.domains.domains | format_value("int") }} registered domains have an AAAA record. Some zone files are years old; each TLD's download date is shown below.</p>
<div class="table-wrap"><table>
  <thead><tr><th>TLD</th><th>Domains</th><th>With AAAA</th><th>Zone downloaded</th></tr></thead>
  <tbody>{% for t in tlds %}<tr><td>{{ t.tld }}</td><td>{{ t.domains | format_value("int") }}</td><td>{{ t.aaaa | format_value("int") }}</td><td>{% if t.old %}<span class="stale">zone data from {{ t.downloaded }}</span>{% else %}{{ t.downloaded }}{% endif %}</td></tr>{% endfor %}</tbody>
</table></div>
{{ provenance(he) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Routing security</h2>
{% if routing %}
<p>ROAs cover {{ routing.value.roa_ipv6.latest.value | format_value("pct") }} of advertised IPv6 address space and {{ routing.value.roa_ipv4.latest.value | format_value("pct") }} of IPv4 ({{ routing.value.roa_ipv6.latest.date }}). Route origin validation: {{ routing.value.rov.latest.partial | format_value("pct") }} partial and {{ routing.value.rov.latest.full | format_value("pct") }} full ({{ routing.value.rov.latest.date }}).</p>
<div class="chart">{{ roa_chart }}</div>
{{ provenance(routing) }}
{% else %}{{ unavailable() }}{% endif %}
{% if bogons %}<p>Team Cymru lists {{ bogons.value.prefixes | format_value("int") }} IPv6 bogon prefixes (updated {{ bogons.value.updated }}).</p>{{ provenance(bogons) }}{% else %}{{ unavailable() }}{% endif %}

<h2>Measurement networks</h2>
{% if atlas %}<p>RIPE Atlas: {{ atlas.value.ipv6_works | format_value("int") }} of {{ atlas.value.connected | format_value("int") }} connected probes have working IPv6 ({{ atlas.value.ipv4_works | format_value("int") }} have working IPv4).</p>{{ provenance(atlas) }}{% else %}{{ unavailable() }}{% endif %}
{% if matrix %}
<p>IPv6 Matrix: {{ matrix.value.latest.share | format_value("pct") }} of {{ matrix.value.latest.hosts | format_value("int") }} crawled hosts reachable over IPv6 (crawl of {{ matrix.value.latest.date }}).</p>
<div class="chart">{{ matrix_chart }}</div>
<details class="source"><summary>By country (largest crawls)</summary>
<div class="table-wrap"><table><thead><tr><th>Country</th><th>Hosts</th><th>With IPv6</th></tr></thead>
<tbody>{% for c in matrix.value.countries %}<tr><td>{{ c.code }}</td><td>{{ c.hosts | format_value("int") }}</td><td>{{ c.share | format_value("pct") }}</td></tr>{% endfor %}</tbody></table></div>
</details>
{{ provenance(matrix) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Interconnection</h2>
{% if peeringdb %}<p>{{ peeringdb.value.ipv6_networks | format_value("int") }} of {{ peeringdb.value.networks | format_value("int") }} networks in PeeringDB list IPv6 traffic.</p>{{ provenance(peeringdb) }}{% else %}{{ unavailable() }}{% endif %}

<h2>Access networks</h2>
<p class="provenance">Network list maintained by this site, last reviewed {{ carriers_reviewed }}; figures from APNIC's per-network measurements.</p>
{% if carrier_detail %}
<div class="table-wrap"><table>
  <thead><tr><th>Network</th><th>AS</th><th>Country</th><th>IPv6-capable</th><th>Prefers IPv6</th></tr></thead>
  <tbody>{% for c in carriers %}<tr><td>{{ c.name }}</td><td>AS{{ c.asn }}</td><td>{{ c.country }}</td>
  {% if c.apnic %}<td>{{ c.apnic.capable | format_value("pct") }}</td><td>{{ c.apnic.preferred | format_value("pct") }}</td>
  {% else %}<td colspan="2" class="missing">not among APNIC's largest networks for its economy</td>{% endif %}</tr>{% endfor %}</tbody>
</table></div>
{{ provenance(carrier_detail) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Government websites</h2>
<p class="provenance">Domain list maintained by this site, last reviewed {{ government_reviewed }}. A site counts when its domain or www. name publishes an IPv6 address.</p>
{% if government %}
{% for g in government.value.groups %}
<details class="source"><summary>{{ g.name }}: {{ g.with_ipv6 }} of {{ g.checked }} with IPv6</summary>
<ul>{% for d in g.domains %}<li><code>{{ d.domain }}</code>: {{ {"ipv6": "IPv6", "ipv4_only": "IPv4 only", "unknown": "unknown"}[d.status] }}</li>{% endfor %}</ul>
</details>
{% endfor %}
{{ provenance(government) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Regional registries</h2>
{% for name, d in rir_details %}
<details class="source"><summary>{{ name }}</summary>
{% if d %}
<p>{{ d.value.total_blocks_32 | format_value("int") }} IPv6 /32 equivalents across {{ d.value.countries }} economies (registry file of {{ d.value.file_date }}).</p>
<div class="table-wrap"><table><thead><tr><th>Economy</th><th>/32 equivalents</th><th>Share</th></tr></thead>
<tbody>{% for c in d.value.top_countries[:rir_top] %}<tr><td>{{ c.code }}</td><td>{{ c.blocks_32 | format_value("int") }}</td><td>{{ c.share | format_value("pct") }}</td></tr>{% endfor %}</tbody></table></div>
{{ provenance(d) }}
{% else %}{{ unavailable() }}{% endif %}
</details>
{% endfor %}

<h2>Data freshness</h2>
{{ freshness_table(freshness) }}
{% endblock %}
```

In `web/build.py`: add `extended_data_sources` to the `from web.pages import ...` line; append `Page("extended-data-sources", "Extended Data Sources", extended_data_sources.context),` to `PAGES` and `"Extended Data Sources": "extended-data-sources/",` to `LEGACY_PAGES`.

- [ ] **Step 5: Verify** — `uv run pytest tests/test_extended_data_sources.py -q && uv run pytest -q` → all pass.
- [ ] **Step 6: Commit** — `git add web/ tests/ && git commit -m "Add Extended Data Sources page"`

---

### Task 8: Live run and visual check

- [ ] **Step 1:** `uv run python -m collect.run --data-dir data --force --only he_progress --only cymru_bogons --only ripe_atlas_probes --only peeringdb_networks --only isoc_routing --only ipv6matrix_hosts --only government_domains` → `failed=0`.
- [ ] **Step 2:** build, serve, check `/extended-data-sources/` at desktop and 375px; check that carriers resolve against APNIC's tables (most should show values).
- [ ] **Step 3:** README "Pages so far" adds Extended Data Sources, and the reference-file bullet mentions `carriers.toml` and `government_domains.toml`. `uv run pytest -q`; commit `"Document the Extended Data Sources page"`.
