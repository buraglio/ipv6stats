# Static Site Plan 2: Global Adoption + Country Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Global Adoption page, the Country Analysis page with a world map, and one static page per economy, all built only from live, collected data.

**Architecture:** Five new collectors (`collect/sources/`) write JSON like the Plan 1 sources. `web/derive.py` gains joins across sources (APNIC + 6lab + Vyncke + RIR files). `web/build.py` gains two nav pages and a generator for `/country/<cc>/` pages. The world map is a Plotly choropleth whose geography file is served from `static/topojson/`.

**Tech Stack:** As Plan 1, plus `pycountry` (ISO 3166 alpha-2 → alpha-3 for the map).

**Spec:** `docs/superpowers/specs/2026-10-14-static-site-migration-design.md`. **Amendment 2** (end of file) is the approved scope for this plan; Amendment 1 and the Plan 1 rules still apply.

## Global Constraints

- Work on `staging`. Do not modify the Streamlit files (`app.py`, `data_sources.py`, `visualization.py`, `components.py`, `utils.py`, `data_manager.py`, `page_modules/`, `cloud_data.py`, `requirements.txt`).
- A collector returns parsed data or raises; never fallback values. Every displayed number goes through a `Datum`. `tests/test_no_static_stats.py` must stay green: no `%`/thousands-separated literals or bare numbers ≥1000 (or floats other than 0.0/1.0) outside `UPPER_CASE = ...` constant lines in `collect/` and `web/`; no 4+ digit numbers or `%` statistics in templates outside `{% call reference(...) %}` blocks.
- Re-fetch intervals: all new sources `MONTH`.
- APNIC rankings use economies with ≥ `MIN_SAMPLES` (100,000) samples; the map and country index use every economy.
- Per-economy detail: `TOP_ECONOMIES = 50` by samples; `TOP_NETWORKS = 20`; `MAX_MISSING = 5` failed pages tolerated.
- Vyncke: map ccTLD `uk` → `GB`; drop `eu` rows.
- NIST cell colors: `00A000` operational, `FFFF00` in progress, `D00000` none, `999999` not applicable; any other color raises.
- RIR file date comes from the header's **end date** (field 6, YYYYMMDD), never the serial.
- Map geography: `web/static/topojson/world_110m.json` from plotly.js **3.1.0**; chart config `topojsonURL` is relative (`../static/topojson/`).
- Legacy redirects add `"Global Adoption": "global-adoption/"` and `"Country Analysis": "country-analysis/"`.
- Country pages live at `/country/<lowercase iso2>/`, rendered with `base="../../"`, nav highlights Country Analysis.
- OMB M-21-07 targets appear only inside a `reference(reviewed="2026-10-14")` block.

## Review Focus

1. **One APNIC economy page fails or changes format.** The other pages still publish; the code is listed in `missing`; that country page says history is unavailable. Tests: `test_fetch_tolerates_a_few_failed_pages`, `test_country_in_missing_list_says_unavailable`.
2. **An economy exists in APNIC but not in 6lab, Vyncke or any RIR file.** It must show "—", not crash or borrow another country's value. Tests: `test_economy_table_joins_by_code`, `test_country_without_other_sources_renders`.
3. **ccTLD vs ISO codes** (`uk`/`GB`, `eu`). No wrong-country joins. Test: `test_uk_maps_to_gb_and_eu_is_dropped`.
4. **The map must not make third-party requests.** Its geography file is served from our site. Test: `test_map_uses_self_hosted_topojson`.
5. **Run time and size.** ARIN's file is 12 MB and 50 APNIC pages are about 2 MB each; the job has a 30-minute limit. Task 11 measures a real run.

---

## File Structure

```
collect/sources/rir.py              # all five RIRs; by_country + history; end-date fix (modify)
collect/sources/apnic_detail.py     # key "apnic_economy_detail" (new)
collect/sources/sixlab.py           # key "cisco_6lab" (new)
collect/sources/vyncke.py           # key "vyncke" (new)
collect/sources/nist.py             # key "nist_usgv6" (new)
collect/sources/__init__.py         # register new modules (modify)
web/data.py                         # + field() (modify)
web/derive.py                       # + joins (modify)
web/charts.py                       # + bar_chart, multi_line_chart, choropleth (modify)
web/build.py                        # + pages, country generator, legacy names (modify)
web/pages/global_adoption.py        # (new)
web/pages/country_analysis.py       # (new)
web/pages/country.py                # pages(data), context(data, code) (new)
web/templates/global-adoption.html  country-analysis.html  country.html   (new)
web/static/site.css                 # + map / index styles (modify)
web/static/topojson/world_110m.json # vendored (new)
pyproject.toml, uv.lock             # + pycountry
tests/fixtures/apnic/economy-US.html  tests/fixtures/sixlab/users.js  tests/fixtures/vyncke/ipv6status.html
tests/test_rir.py (extend)  test_apnic_detail.py  test_sixlab.py  test_vyncke.py  test_nist.py
tests/sample_data.py (extend)  test_derive.py (extend)  test_charts.py (extend)
tests/test_global_adoption.py  test_country_analysis.py  test_country_pages.py
```

---

### Task 1: All five RIR delegation files, per-country totals and history

**Files:**
- Modify: `collect/sources/rir.py` (replace whole file)
- Test: `tests/test_rir.py` (append)

**Interfaces:**
- Produces: source keys `afrinic_delegations`, `apnic_delegations`, `arin_delegations`, `lacnic_delegations`, `ripe_delegations`; `rir.URLS: dict[str, str]` keyed by registry name in the file (`afrinic`, `apnic`, `arin`, `lacnic`, `ripencc`); `rir.LACNIC_URL`, `rir.AFRINIC_URL` kept. Payload adds `"by_country": {cc: blocks_32}` and `"history": [{"year": int, "blocks_32": cumulative float}]`; existing fields unchanged.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_rir.py`:

```python


RIPE_SAMPLE = """2|ripencc|1791928799|167536|19700101|20261013|+0200
ripencc|*|ipv6|*|26850|summary
ripencc|NL|ipv6|2001:600::|29|19990826|allocated
ripencc|DE|ipv6|2001:608::|32|20030812|allocated
ripencc|DE|ipv6|2001:609::|48||assigned
"""


def test_file_date_comes_from_end_date_not_serial():
    # RIPE's serial is a Unix timestamp; reading it as YYYYMMDD gave "1791-92-87".
    assert rir.parse_delegations(RIPE_SAMPLE, "ripencc", rir.URLS["ripencc"])["file_date"] == "2026-10-13"


def test_by_country_and_history():
    parsed = rir.parse_delegations(RIPE_SAMPLE, "ripencc", rir.URLS["ripencc"])
    assert parsed["by_country"] == {"DE": 1.0, "NL": 8.0}  # DE: /32 + /48 rounds to 1.0
    # The undated /48 counts in the totals but not in the dated history.
    assert parsed["history"] == [{"year": 1999, "blocks_32": 8.0}, {"year": 2003, "blocks_32": 9.0}]


def test_arin_extended_format():
    text = ("2.3|arin|1791982821510|204020|19700101|20261014|-0400\n"
            "arin|US|ipv6|2001:400::|32|19990803|allocated|04f048163e37eef48d891498545eefc0\n"
            "arin||ipv6|2001:4:113::|48||available|\n")
    parsed = rir.parse_delegations(text, "arin", rir.URLS["arin"])
    assert parsed["file_date"] == "2026-10-14"
    assert parsed["by_country"] == {"US": 1.0}


def test_rejects_bad_end_date():
    text = "2|ripencc|1|1|19700101|garbage|+0200\nripencc|DE|ipv6|2001:608::|32|20030812|allocated\n"
    with pytest.raises(ValueError, match="format changed"):
        rir.parse_delegations(text, "ripencc", rir.URLS["ripencc"])


def test_all_five_registered():
    for key in ("afrinic_delegations", "apnic_delegations", "arin_delegations",
                "lacnic_delegations", "ripe_delegations"):
        assert key in SOURCES
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_rir.py -q`
Expected: FAIL (`AttributeError: module 'collect.sources.rir' has no attribute 'URLS'`).

- [ ] **Step 3: Replace `collect/sources/rir.py`**

```python
"""IPv6 allocations from the five RIR delegation files, in /32 equivalents."""
from collect.registry import MONTH, Context, source

URLS = {
    "afrinic": "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest",
    "apnic": "https://ftp.apnic.net/stats/apnic/delegated-apnic-latest",
    "arin": "https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest",
    "lacnic": "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
    "ripencc": "https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest",
}
LACNIC_URL = URLS["lacnic"]
AFRINIC_URL = URLS["afrinic"]
REGISTRIES = (  # (source key, registry name used inside the file, title)
    ("afrinic_delegations", "afrinic", "AFRINIC delegation file"),
    ("apnic_delegations", "apnic", "APNIC delegation file"),
    ("arin_delegations", "arin", "ARIN delegation file (extended)"),
    ("lacnic_delegations", "lacnic", "LACNIC delegation file"),
    ("ripe_delegations", "ripencc", "RIPE NCC delegation file"),
)
UNIT = 32
COUNTED = {"allocated", "assigned"}
TOP_N = 10
NO_DATE = "00000000"


def _is_yyyymmdd(text: str) -> bool:
    return len(text) == len("YYYYMMDD") and text.isdigit()


def parse_delegations(text: str, registry: str, url: str) -> dict:
    # Header: version|registry|serial|records|startdate|enddate|UTCoffset. The serial is
    # YYYYMMDD at some RIRs and a Unix timestamp at others; enddate is YYYYMMDD everywhere.
    # Records: registry|cc|type|start|value|date|status[|opaque-id]
    file_date, per_country, per_year, total = None, {}, {}, 0.0
    for line in text.splitlines():
        parts = line.strip().split("|")
        if file_date is None and len(parts) >= 6 and parts[1] == registry and parts[0][:1].isdigit():
            end = parts[5]
            if not _is_yyyymmdd(end):
                raise ValueError(f"{registry} delegation file format changed: header end date {end!r}")
            file_date = f"{end[:4]}-{end[4:6]}-{end[6:]}"
            continue
        if (len(parts) < 7 or parts[0] != registry or parts[2] != "ipv6"
                or parts[1] in ("*", "") or parts[6] not in COUNTED):
            continue
        blocks = 2 ** (UNIT - int(parts[4]))  # int base; a negative power gives a float
        per_country[parts[1]] = per_country.get(parts[1], 0) + blocks
        total += blocks
        if _is_yyyymmdd(parts[5]) and parts[5] != NO_DATE:
            year = int(parts[5][:4])
            per_year[year] = per_year.get(year, 0) + blocks
    if file_date is None or not per_country:
        raise ValueError(f"{registry} delegation file format changed")
    top = sorted(per_country.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    history, running = [], 0.0
    for year in sorted(per_year):
        running += per_year[year]
        history.append({"year": year, "blocks_32": round(running, 2)})
    return {
        "file_date": file_date,
        "total_blocks_32": round(total, 2),
        "countries": len(per_country),
        "top_countries": [{"code": cc, "blocks_32": round(b, 2), "share": round(100 * b / total, 2)}
                          for cc, b in top],
        "by_country": {cc: round(b, 2) for cc, b in sorted(per_country.items())},
        "history": history,
        "url": url,
    }


def _fetch(ctx: Context, registry: str, url: str) -> dict:
    response = ctx.session.get(url, timeout=120)
    response.raise_for_status()
    return parse_delegations(response.text, registry, url)


def _register(key: str, registry: str, title: str) -> None:
    url = URLS[registry]

    def fetch(ctx: Context) -> dict:
        return _fetch(ctx, registry, url)

    source(key, MONTH, title=title, url=url)(fetch)


for _key, _registry, _title in REGISTRIES:
    _register(_key, _registry, _title)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_rir.py -q && uv run pytest -q`
Expected: all pass (the existing LACNIC/AFRINIC tests still pass).

- [ ] **Step 5: Commit**

```bash
git add collect/sources/rir.py tests/test_rir.py
git commit -m "Collect all five RIR delegation files with per-country totals and history

Also read the file date from the header's end date: RIPE and ARIN put a
timestamp in the serial field."
```

---

### Task 2: APNIC per-economy history and networks

**Files:**
- Create: `collect/sources/apnic_detail.py`, `tests/test_apnic_detail.py`, `tests/fixtures/apnic/economy-US.html`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Consumes: `apnic.URL`, `apnic.parse` (Plan 1).
- Produces: source key `apnic_economy_detail`; `parse_economy(page) -> {"history": [{"date","capable","preferred"}] (weekly), "networks": [{"asn": int, "name", "capable", "preferred", "samples"}] (≤ TOP_NETWORKS, by samples)}`; payload `{"economies": {CC: parse_economy(...)}, "missing": [CC]}`; constants `TOP_ECONOMIES`, `TOP_NETWORKS`, `MAX_MISSING`.

- [ ] **Step 1: Record a trimmed real page**

```bash
curl -s https://stats.labs.apnic.net/ipv6/US -o /tmp/apnic-us.html && python3 - <<'EOF'
import re
lines = open("/tmp/apnic-us.html", encoding="utf-8").read().splitlines()
series = [l for l in lines if re.search(r"\[new Date\('\d{4}-\d{2}-\d{2}'\),[\d.]+,[\d.]+\]", l)][:400]
networks = [l for l in lines if "stats.labs.apnic.net/ipv6/AS" in l][:40]
open("tests/fixtures/apnic/economy-US.html", "w", encoding="utf-8").write("\n".join(series + networks) + "\n")
print(len(series), len(networks))
EOF
```
Expected: `400 40`.

- [ ] **Step 2: Write the failing tests** — `tests/test_apnic_detail.py`:

```python
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import apnic, apnic_detail
from tests.fakes import FakeResponse, make_ctx

FIXTURES = Path(__file__).parent / "fixtures" / "apnic"
MAIN = (FIXTURES / "ipv6.html").read_text(encoding="utf-8")
US = (FIXTURES / "economy-US.html").read_text(encoding="utf-8")

SAMPLE = r"""
      [new Date('2026-10-05'),60.1,58.0],
      [new Date('2026-10-06'),60.2,58.1],
      [new Date('2026-10-12'),61.0,59.0],
      [new Date('2026-10-03'),3498874],
["<a href=\"//stats.labs.apnic.net/ipv6/AS7922?c=US&p=1&v=1&w=30&x=1\">AS7922</a>","COMCAST-7922 - Comcast Cable Communications, LLC",{v: 85.28, f:'x'},{v: 83.59, f: 'x'},16629912],
["<a href=\"//stats.labs.apnic.net/ipv6/AS7018?c=US&p=1&v=1&w=30&x=1\">AS7018</a>","ATT-INTERNET4 - AT&amp;T \"Enterprises\", LLC",{v: 85.95, f:'x'},{v: 84.0, f: 'x'},20000000],
["<a href=\"//stats.labs.apnic.net/ipv6/AS7922?c=US&p=1&v=1&w=30&x=1\">AS7922</a>","dup",{v: 1.0, f:'x'},{v: 1.0, f: 'x'},1],
"""


def test_parse_economy_sample():
    parsed = apnic_detail.parse_economy(SAMPLE)
    # 2026-10-05 and -06 are the same ISO week (keep the later); -12 is the next week
    assert parsed["history"] == [{"date": "2026-10-06", "capable": 60.2, "preferred": 58.1},
                                 {"date": "2026-10-12", "capable": 61.0, "preferred": 59.0}]
    assert [n["asn"] for n in parsed["networks"]] == [7018, 7922]  # by samples, first copy kept
    assert parsed["networks"][0]["name"] == 'ATT-INTERNET4 - AT&T "Enterprises", LLC'


def test_parse_recorded_page():
    parsed = apnic_detail.parse_economy(US)
    assert len(parsed["history"]) >= 52
    assert parsed["networks"] and isinstance(parsed["networks"][0]["asn"], int)
    assert len(parsed["networks"]) <= apnic_detail.TOP_NETWORKS


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="APNIC economy page format changed"):
        apnic_detail.parse_economy("<html>redesigned</html>")


def top_codes(n):
    ranked = sorted(apnic.parse(MAIN)["economies"], key=lambda e: e["samples"], reverse=True)
    return [e["code"] for e in ranked[:n]]


def test_fetch_top_economies(monkeypatch):
    monkeypatch.setattr(apnic_detail, "TOP_ECONOMIES", 2)
    codes = top_codes(2)
    routes = {f"{apnic.URL}{c}": FakeResponse(text=US) for c in codes}
    routes[apnic.URL] = FakeResponse(text=MAIN)  # last: it is a prefix of every economy URL
    result = SOURCES["apnic_economy_detail"].fetch(make_ctx(routes=routes))
    assert sorted(result["economies"]) == sorted(codes)
    assert result["missing"] == []


def test_fetch_tolerates_a_few_failed_pages(monkeypatch):
    monkeypatch.setattr(apnic_detail, "TOP_ECONOMIES", 2)
    first, second = top_codes(2)
    routes = {f"{apnic.URL}{first}": FakeResponse(text=US), f"{apnic.URL}{second}": FakeResponse(status_code=503),
              apnic.URL: FakeResponse(text=MAIN)}
    monkeypatch.setattr(apnic_detail, "MAX_MISSING", 1)
    assert SOURCES["apnic_economy_detail"].fetch(make_ctx(routes=routes))["missing"] == [second]
    monkeypatch.setattr(apnic_detail, "MAX_MISSING", 0)
    with pytest.raises(ValueError, match="economy pages failed"):
        SOURCES["apnic_economy_detail"].fetch(make_ctx(routes=routes))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_apnic_detail.py -q`
Expected: FAIL (`ImportError: cannot import name 'apnic_detail'`).

- [ ] **Step 4: Implement** — `collect/sources/apnic_detail.py`:

```python
"""APNIC per-economy pages: weekly IPv6 capability history and the per-network (AS) table."""
import html
import logging
import re
from datetime import date

from collect.registry import MONTH, Context, source
from collect.sources import apnic

logger = logging.getLogger(__name__)

TOP_ECONOMIES = 50
TOP_NETWORKS = 20
MAX_MISSING = 5
# History rows: [new Date('2011-10-20'),0.19,0.22]  -> date, IPv6-capable, IPv6-preferred
# (sample-count rows have only two values and are not matched)
SERIES = re.compile(r"\[new Date\('(\d{4}-\d{2}-\d{2})'\),([\d.]+),([\d.]+)\]")
# Network rows: ["<a href=\"//stats.labs.apnic.net/ipv6/AS7922?c=US...\">AS7922</a>","NAME",
#                {v: 85.28, ...},{v: 83.59, ...},16629912]
NETWORK = re.compile(
    r'\["<a href=\\"//stats\.labs\.apnic\.net/ipv6/AS(\d+)\?[^"]*\\">AS\d+</a>",'
    r'"((?:[^"\\]|\\.)*)",\{v:\s*([\d.]+)[^}]*\},\s*\{v:\s*([\d.]+)[^}]*\},(\d+)\]'
)


def weekly(points: list[dict]) -> list[dict]:
    """Keep the last point of each ISO week."""
    by_week = {}
    for point in sorted(points, key=lambda p: p["date"]):
        year, week, _ = date.fromisoformat(point["date"]).isocalendar()
        by_week[(year, week)] = point
    return [by_week[key] for key in sorted(by_week)]


def parse_economy(page: str) -> dict:
    points = [{"date": d, "capable": float(c), "preferred": float(p)} for d, c, p in SERIES.findall(page)]
    if not points:
        raise ValueError("APNIC economy page format changed: no history rows")
    networks, seen = [], set()
    for asn, name, capable, preferred, samples in NETWORK.findall(page):
        if asn in seen:  # the page repeats the table in several layouts; keep the first
            continue
        seen.add(asn)
        networks.append({"asn": int(asn), "name": html.unescape(name.replace('\\"', '"')),
                         "capable": float(capable), "preferred": float(preferred), "samples": int(samples)})
    networks.sort(key=lambda n: n["samples"], reverse=True)
    return {"history": weekly(points), "networks": networks[:TOP_NETWORKS]}


@source("apnic_economy_detail", MONTH, title="APNIC Labs per-economy history and networks", url=apnic.URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(apnic.URL, timeout=30)
    response.raise_for_status()
    ranked = sorted(apnic.parse(response.text)["economies"], key=lambda e: e["samples"], reverse=True)
    economies, missing = {}, []
    for economy in ranked[:TOP_ECONOMIES]:
        code = economy["code"]
        try:
            page = ctx.session.get(f"{apnic.URL}{code}", timeout=60)
            page.raise_for_status()
            economies[code] = parse_economy(page.text)
        except Exception as exc:  # one bad page must not discard the others
            logger.warning("APNIC page for %s failed: %s", code, exc)
            missing.append(code)
    if len(missing) > MAX_MISSING:
        raise ValueError(f"{len(missing)} APNIC economy pages failed: {', '.join(missing)}")
    return {"economies": economies, "missing": missing}
```

Replace the import line in `collect/sources/__init__.py` with:

```python
from collect.sources import apnic, apnic_detail, bgp, cloudflare, isoc, rir, tranco  # noqa: F401
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_apnic_detail.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add collect/sources/ tests/test_apnic_detail.py tests/fixtures/apnic/economy-US.html
git commit -m "Add APNIC per-economy history and network tables for the top 50 economies"
```

---

### Task 3: Cisco 6lab mirror (IPv6 users per country)

**Files:**
- Create: `collect/sources/sixlab.py`, `tests/test_sixlab.py`, `tests/fixtures/sixlab/users.js`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Produces: source key `cisco_6lab`; `sixlab.parse(text, min_countries=MIN_COUNTRIES) -> {"countries": [{"code", "name", "ipv6_users_pct"}], "url"}`; `sixlab.URL`.

- [ ] **Step 1: Record the fixture**

Run: `mkdir -p tests/fixtures/sixlab && curl -s https://6lab-stats.com/6lab-stats/curr/users.js -o tests/fixtures/sixlab/users.js && grep -c '^\["' tests/fixtures/sixlab/users.js`
Expected: about 240.

- [ ] **Step 2: Write the failing tests** — `tests/test_sixlab.py`:

```python
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import sixlab
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "sixlab" / "users.js").read_text(encoding="utf-8")

SAMPLE = """var UsersData = {
  data: [
["US", "United States of America",0.546,1.36532176E8,57.2],
["AE", "United Arab Emirates",0.41799998,4121796.5,30.7],
["AI", "Anguilla",0.0,0.0,0.0],
"""


def test_parse_sample_uses_last_column():
    parsed = sixlab.parse(SAMPLE, min_countries=1)
    assert parsed["countries"][0] == {"code": "US", "name": "United States of America", "ipv6_users_pct": 57.2}
    assert len(parsed["countries"]) == 3


def test_parse_recorded_file():
    codes = {c["code"] for c in sixlab.parse(FIXTURE)["countries"]}
    assert {"US", "FR", "IN"} <= codes


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="6lab users.js format changed"):
        sixlab.parse("<html>404</html>")


def test_fetch():
    ctx = make_ctx(routes={sixlab.URL: FakeResponse(text=FIXTURE)})
    assert SOURCES["cisco_6lab"].fetch(ctx)["countries"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_sixlab.py -q`
Expected: FAIL (`ImportError: cannot import name 'sixlab'`).

- [ ] **Step 4: Implement** — `collect/sources/sixlab.py`:

```python
"""IPv6 users per country from the Cisco 6lab statistics mirror (6lab-stats.com)."""
import re

from collect.registry import MONTH, Context, source

URL = "https://6lab-stats.com/6lab-stats/curr/users.js"
HOME = "https://6lab-stats.com/"
# Rows: ["US", "United States of America",0.546,1.36532176E8,57.2],
# Only the last column (IPv6 users %) is used; the meaning of the middle two is not documented.
ROW = re.compile(r'^\["([A-Z]{2})",\s*"([^"]*)",\s*[-\d.Ee+]+,\s*[-\d.Ee+]+,\s*([\d.]+)\]', re.M)
MIN_COUNTRIES = 150


def parse(text: str, min_countries: int = MIN_COUNTRIES) -> dict:
    countries = [{"code": code, "name": name, "ipv6_users_pct": float(pct)}
                 for code, name, pct in ROW.findall(text)]
    if len(countries) < min_countries:
        raise ValueError(f"6lab users.js format changed: {len(countries)} countries")
    return {"countries": countries, "url": HOME}


@source("cisco_6lab", MONTH, title="Cisco 6lab statistics (community mirror)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=30)
    response.raise_for_status()
    return parse(response.text)
```

Replace the import line in `collect/sources/__init__.py` with:

```python
from collect.sources import apnic, apnic_detail, bgp, cloudflare, isoc, rir, sixlab, tranco  # noqa: F401
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_sixlab.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add collect/sources/ tests/test_sixlab.py tests/fixtures/sixlab/
git commit -m "Add Cisco 6lab mirror source for IPv6 users per country"
```

---

### Task 4: Vyncke website IPv6 status per country

**Files:**
- Create: `collect/sources/vyncke.py`, `tests/test_vyncke.py`, `tests/fixtures/vyncke/ipv6status.html`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Produces: source key `vyncke`; `vyncke.parse(page, min_rows=MIN_ROWS) -> {"web": [Row], "email": [Row], "dns": [Row], "url"}`, `Row = {"code": ISO2, "name", "sites": int, "weighted_pct": float, "green_pct": float}`; `vyncke.URL`, `SERVICES = ("web", "email", "dns")`.

- [ ] **Step 1: Record the fixture**

Run: `mkdir -p tests/fixtures/vyncke && curl -s https://www.vyncke.org/ipv6status/ -o tests/fixtures/vyncke/ipv6status.html && grep -c 'detailed.php?country=' tests/fixtures/vyncke/ipv6status.html`
Expected: several hundred.

- [ ] **Step 2: Write the failing tests** — `tests/test_vyncke.py`:

```python
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import vyncke
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "vyncke" / "ipv6status.html").read_text(encoding="utf-8")


def table(title, rows):
    body = "".join(
        f'<tr><td>{i}<td><a href=detailed.php?country={cc}><img class="flag-{cc}" src="/flags/flags-sprite.png" border=0> {name}</a>\n'
        f"\t<td align=right>50\n\t<td align=right>{weighted}%\n\t<td align=right>{green}% (17)\n\t<td align=right>0.0% (0)\n"
        for i, (cc, name, weighted, green) in enumerate(rows, 1))
    return f'<h3>{title} (Umbrella)</h3>\n<table class="table"><tbody>\n{body}</tbody>\n  </table>'


SAMPLE = (table("Web", [("no", "Norway", "55.54", "68.0"), ("uk", "United-Kingdom", "66.14", "34.0"),
                        ("eu", "European Union", "42.24", "40.0")])
          + table("Email", [("no", "Norway", "56.72", "70.0")])
          + table("DNS", [("de", "Germany", "91.75", "98.0")]))


def test_parse_sample():
    parsed = vyncke.parse(SAMPLE, min_rows=1)
    assert parsed["web"][0] == {"code": "NO", "name": "Norway", "sites": 50, "weighted_pct": 55.54, "green_pct": 68.0}
    assert parsed["dns"][0]["code"] == "DE"


def test_uk_maps_to_gb_and_eu_is_dropped():
    codes = [r["code"] for r in vyncke.parse(SAMPLE, min_rows=1)["web"]]
    assert codes == ["NO", "GB"]


def test_parse_recorded_page():
    parsed = vyncke.parse(FIXTURE)
    for service in vyncke.SERVICES:
        assert len(parsed[service]) >= vyncke.MIN_ROWS
    assert "US" in {r["code"] for r in parsed["web"]}


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="Vyncke page format changed"):
        vyncke.parse("<html>redesigned</html>")


def test_fetch():
    ctx = make_ctx(routes={vyncke.URL: FakeResponse(text=FIXTURE)})
    assert SOURCES["vyncke"].fetch(ctx)["web"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_vyncke.py -q`
Expected: FAIL (`ImportError: cannot import name 'vyncke'`).

- [ ] **Step 4: Implement** — `collect/sources/vyncke.py`:

```python
"""Per-country IPv6 support among top websites, from Eric Vyncke's IPv6 deployment status."""
import html
import re

from collect.registry import MONTH, Context, source

URL = "https://www.vyncke.org/ipv6status/"
SERVICES = ("web", "email", "dns")
TITLES = {"web": "Web", "email": "Email", "dns": "DNS"}
# Rows (HTML rows are not closed):
# <tr><td>1<td><a href=detailed.php?country=no><img ...> Norway</a>
#     <td align=right>50 <td align=right>55.54% <td align=right>68.0% (34) <td align=right>0.0% (0)
ROW = re.compile(
    r"<tr><td>\d+<td><a href=detailed\.php\?country=([a-z]{2})>.*?>\s*([^<]+?)</a>\s*"
    r"<td align=right>(\d+)\s*<td align=right>([\d.]+)%\s*<td align=right>([\d.]+)% \(\d+\)",
    re.S,
)
CCTLD_TO_ISO = {"uk": "GB"}
NOT_A_COUNTRY = {"eu"}
MIN_ROWS = 50


def _section(page: str, title: str) -> str:
    match = re.search(rf"<h3>{title} \(Umbrella\)</h3>(.*?)</table>", page, re.S)
    return match.group(1) if match else ""


def parse(page: str, min_rows: int = MIN_ROWS) -> dict:
    result = {"url": URL}
    for service in SERVICES:
        rows = []
        for cc, name, sites, weighted, green in ROW.findall(_section(page, TITLES[service])):
            if cc in NOT_A_COUNTRY:
                continue
            rows.append({"code": CCTLD_TO_ISO.get(cc, cc.upper()), "name": html.unescape(name.strip()),
                         "sites": int(sites), "weighted_pct": float(weighted), "green_pct": float(green)})
        if len(rows) < min_rows:
            raise ValueError(f"Vyncke page format changed: {len(rows)} rows in the {service} table")
        result[service] = rows
    return result


@source("vyncke", MONTH, title="Vyncke IPv6 deployment status (top websites per country)", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)
```

Replace the import line in `collect/sources/__init__.py` with:

```python
from collect.sources import apnic, apnic_detail, bgp, cloudflare, isoc, rir, sixlab, tranco, vyncke  # noqa: F401
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_vyncke.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add collect/sources/ tests/test_vyncke.py tests/fixtures/vyncke/
git commit -m "Add Vyncke source for website, email and DNS IPv6 support per country"
```

---

### Task 5: NIST USGv6 federal deployment

**Files:**
- Create: `collect/sources/nist.py`, `tests/test_nist.py`
- Modify: `collect/sources/__init__.py`

**Interfaces:**
- Produces: source key `nist_usgv6`; `nist.parse(page, min_domains=MIN_DOMAINS) -> {"domains": int, "totals": {svc: {status: n}}, "agencies": [{"name", "domains", "dns": {status: n}, "mail": {...}, "web": {...}}] (by domains desc, then name), "url"}`; statuses `operational`, `in_progress`, `none`, `not_applicable`; `nist.URL`, `nist.HOME`, `SERVICES = ("dns", "mail", "web")`.

- [ ] **Step 1: Write the failing tests** — `tests/test_nist.py`:

```python
import pytest

from collect.registry import SOURCES
from collect.sources import nist
from tests.fakes import FakeResponse, make_ctx

# Three rows copied from the live page's markup: a normal row, a row whose agency is a
# link with ANTD-7 grey cells, and an italic (greyed-out) domain.
ROWS = (
    '<TR align=center><TD align=left><ANTD-0><a href="https://www.abmc.gov">gov.abmc.</a></TD>'
    '<TD><ANTD-9>American Battle Monuments Commission</TD>'
    '<TD BGCOLOR=#00A000><ANTD-8>[3] 9/9/8 [O]</TD><TD BGCOLOR=#00A000><ANTD-8>[1] 4/4/4 [O]</TD>'
    '<TD BGCOLOR=#00A000><ANTD-8>[1] 1/1/1 [O]</TD><TD BGCOLOR=#DDDDDD></TD>'
    '<TR align=center><TD align=left><ANTD-0><a href="https://www.18f.gov">gov.18f.</a></TD>'
    '<TD><ANTD-9><a href=../cgi-bin/cfo?gsa>General Services Administration</a></TD>'
    '<TD BGCOLOR=#00A000><ANTD-8>[4] 4/0/4 [O]</TD><TD BGCOLOR=#999999><ANTD-7>[0] 0/0/0 [-]</TD>'
    '<TD BGCOLOR=#999999><ANTD-7>[0] 0/0/0 [-]</TD><TD BGCOLOR=#DDDDDD></TD>'
    '<TR align=center><TD BGCOLOR=#DDDDDD align=left><ANTD-0><i>gov.budgetlob.</i></TD>'
    '<TD><ANTD-9><a href=../cgi-bin/cfo?education>Department of Education</a></TD>'
    '<TD BGCOLOR=#D00000><ANTD-8>[S] 0/0/0 [L]</TD><TD BGCOLOR=#999999><ANTD-7>[0] 0/0/0 [-]</TD>'
    '<TD BGCOLOR=#FFFF00><ANTD-8>[1] 1/0/0 [P]</TD><TD BGCOLOR=#DDDDDD></TD>'
)


def test_parse_counts_by_service_and_agency():
    parsed = nist.parse(ROWS, min_domains=1)
    assert parsed["domains"] == 3
    assert parsed["totals"]["web"] == {"operational": 1, "not_applicable": 1, "in_progress": 1}
    assert parsed["totals"]["dns"] == {"operational": 2, "none": 1}
    assert [a["name"] for a in parsed["agencies"]] == [
        "American Battle Monuments Commission", "Department of Education", "General Services Administration"]
    assert parsed["agencies"][0]["web"] == {"operational": 1}


def test_rejects_unknown_color():
    with pytest.raises(ValueError, match="NIST page format changed"):
        nist.parse(ROWS.replace("#FFFF00", "#123456"), min_domains=1)


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="NIST page format changed"):
        nist.parse("<html>maintenance</html>")


def test_fetch():
    ctx = make_ctx(routes={nist.URL: FakeResponse(text=ROWS)})
    with pytest.raises(ValueError):  # three rows are below MIN_DOMAINS
        SOURCES["nist_usgv6"].fetch(ctx)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_nist.py -q`
Expected: FAIL (`ImportError: cannot import name 'nist'`).

- [ ] **Step 3: Implement** — `collect/sources/nist.py`:

```python
"""NIST USGv6 deployment monitor: IPv6 status of federal .gov domains' DNS, mail and web."""
import html
import re

from collect.registry import MONTH, Context, source

URL = "https://usgv6-deploymon.nist.gov/cgi-bin/generate-gov"
HOME = "https://usgv6-deploymon.nist.gov/"
SERVICES = ("dns", "mail", "web")
# NIST colors each service cell: green operational, yellow in progress, red none, grey n/a.
STATUS = {"00A000": "operational", "FFFF00": "in_progress", "D00000": "none", "999999": "not_applicable"}
CELL = r"<TD BGCOLOR=#([0-9A-Fa-f]{6})>(?:<ANTD-\d+>)?[^<]*</TD>"
ROW = re.compile(
    r"<TD(?: BGCOLOR=#[0-9A-Fa-f]{6})? align=left><ANTD-\d+>(?:<a [^>]*>|<i>)?(gov\.[^<]*?)(?:</a>|</i>)?</TD>"
    r"<TD><ANTD-\d+>(?:<a [^>]*>)?([^<]*?)(?:</a>)?</TD>" + CELL + CELL + CELL
)
MIN_DOMAINS = 500


def _count(counter: dict, status: str) -> None:
    counter[status] = counter.get(status, 0) + 1


def parse(page: str, min_domains: int = MIN_DOMAINS) -> dict:
    totals = {service: {} for service in SERVICES}
    agencies: dict[str, dict] = {}
    rows = ROW.findall(page)
    for _domain, agency, *colors in rows:
        name = html.unescape(agency.strip())
        entry = agencies.setdefault(name, {"name": name, "domains": 0, **{s: {} for s in SERVICES}})
        entry["domains"] += 1
        for service, color in zip(SERVICES, colors):
            status = STATUS.get(color.upper())
            if status is None:
                raise ValueError(f"NIST page format changed: unknown cell color #{color}")
            _count(totals[service], status)
            _count(entry[service], status)
    if len(rows) < min_domains:
        raise ValueError(f"NIST page format changed: only {len(rows)} domains parsed")
    ordered = sorted(agencies.values(), key=lambda a: (-a["domains"], a["name"]))
    return {"domains": len(rows), "totals": totals, "agencies": ordered, "url": HOME}


@source("nist_usgv6", MONTH, title="NIST USGv6 deployment monitor (.gov domains)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=120)
    response.raise_for_status()
    return parse(response.text)
```

Replace the import line in `collect/sources/__init__.py` with:

```python
from collect.sources import (  # noqa: F401
    apnic, apnic_detail, bgp, cloudflare, isoc, nist, rir, sixlab, tranco, vyncke,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_nist.py -q && uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add collect/sources/ tests/test_nist.py
git commit -m "Add NIST USGv6 source for federal DNS, mail and web IPv6 status"
```

---

### Task 6: Sample data and cross-source joins

**Files:**
- Modify: `tests/sample_data.py` (extend `PAYLOADS`), `web/data.py` (+ `field`), `web/derive.py` (append), `pyproject.toml`, `uv.lock`
- Test: `tests/test_derive.py` (append)

**Interfaces:**
- Consumes: payload shapes from Tasks 1–5.
- Produces: `web.data.field(d, key) -> Datum | None`; in `web.derive`: `RIR_SOURCES`, `iso3(code) -> str | None`, `economy_table(data, limit=None)`, `economy_index(data)`, `map_points(data)`, `rir_comparison(data)`, `rir_total(data)`, `country_allocation(data, code)`, `sixlab_for(data, code)`, `vyncke_for(data, code)`, `website_table(data, limit)`, `nist(data)`, all `-> Datum | None`. Row shapes:
  - `economy_table`: `{code, name, capable, preferred, samples, slug, sixlab: float|None, web: float|None}`
  - `economy_index`: `{code, name, slug}` sorted by name
  - `map_points`: `{iso3, code, name, capable}`
  - `rir_comparison`: `{name, total, countries, file_date, history}`
  - `country_allocation`: `{blocks_32, registries: [name]}`
  - `vyncke_for`: `{web, email, dns}` (green %, each float|None)
  - `website_table`: `{code, name, web, email, dns}` sorted by web desc

- [ ] **Step 1: Add pycountry**

Run: add `"pycountry>=24.6.1",` to `dependencies` in `pyproject.toml` (after `"dnspython>=2.6.1",`), then `uv lock && uv sync`.
Expected: `pycountry` installed.

- [ ] **Step 2: Extend the sample data** — in `tests/sample_data.py`, replace the `"lacnic_delegations"` and `"afrinic_delegations"` entries and add the new sources (keep every other entry as it is):

```python
    "lacnic_delegations": {
        "file_date": "2026-10-13", "total_blocks_32": 31250.0, "countries": 33,
        "top_countries": [{"code": "BR", "blocks_32": 20000.0, "share": 64.0}],
        "by_country": {"BR": 20000.0, "MX": 4000.0},
        "history": [{"year": 2003, "blocks_32": 100.0}, {"year": 2026, "blocks_32": 31250.0}],
        "url": "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
    },
    "afrinic_delegations": {
        "file_date": "2026-10-14", "total_blocks_32": 11300.0, "countries": 54,
        "top_countries": [{"code": "ZA", "blocks_32": 2500.0, "share": 22.1}],
        "by_country": {"ZA": 2500.0},
        "history": [{"year": 2005, "blocks_32": 10.0}, {"year": 2026, "blocks_32": 11300.0}],
        "url": "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest",
    },
    "apnic_delegations": {
        "file_date": "2026-10-14", "total_blocks_32": 14000.0, "countries": 50,
        "top_countries": [{"code": "JP", "blocks_32": 8000.0, "share": 57.1}],
        "by_country": {"JP": 8000.0, "IN": 6000.0},
        "history": [{"year": 1999, "blocks_32": 50.0}, {"year": 2026, "blocks_32": 14000.0}],
        "url": "https://ftp.apnic.net/stats/apnic/delegated-apnic-latest",
    },
    "arin_delegations": {
        "file_date": "2026-10-14", "total_blocks_32": 63000.0, "countries": 25,
        "top_countries": [{"code": "US", "blocks_32": 60000.0, "share": 95.2}],
        "by_country": {"US": 60000.0, "CA": 3000.0},
        "history": [{"year": 1999, "blocks_32": 40.0}, {"year": 2026, "blocks_32": 63000.0}],
        "url": "https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest",
    },
    "ripe_delegations": {
        "file_date": "2026-10-13", "total_blocks_32": 52000.0, "countries": 70,
        "top_countries": [{"code": "DE", "blocks_32": 9000.0, "share": 17.3}],
        "by_country": {"DE": 9000.0, "FR": 7000.0},
        "history": [{"year": 1999, "blocks_32": 60.0}, {"year": 2026, "blocks_32": 52000.0}],
        "url": "https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest",
    },
    "apnic_economy_detail": {
        "economies": {
            "US": {"history": [{"date": "2025-10-13", "capable": 58.0, "preferred": 56.0},
                               {"date": "2026-10-12", "capable": 61.9, "preferred": 59.9}],
                   "networks": [{"asn": 7922, "name": "COMCAST-7922 - Comcast Cable Communications, LLC",
                                 "capable": 85.28, "preferred": 83.59, "samples": 16629912}]},
            "FR": {"history": [{"date": "2026-10-12", "capable": 85.6, "preferred": 80.0}],
                   "networks": [{"asn": 3215, "name": "FRANCE-TELECOM - Orange", "capable": 90.1,
                                 "preferred": 88.0, "samples": 5000000}]},
        },
        "missing": ["DE"],
    },
    "cisco_6lab": {
        "countries": [{"code": "US", "name": "United States of America", "ipv6_users_pct": 57.2},
                      {"code": "FR", "name": "France", "ipv6_users_pct": 39.0}],
        "url": "https://6lab-stats.com/",
    },
    "vyncke": {
        "web": [{"code": "FR", "name": "France", "sites": 50, "weighted_pct": 57.62, "green_pct": 44.0},
                {"code": "US", "name": "United States of America", "sites": 50, "weighted_pct": 70.51,
                 "green_pct": 50.0}],
        "email": [{"code": "US", "name": "United States of America", "sites": 50, "weighted_pct": 69.89,
                   "green_pct": 52.0}],
        "dns": [{"code": "US", "name": "United States of America", "sites": 50, "weighted_pct": 84.85,
                 "green_pct": 92.0}],
        "url": "https://www.vyncke.org/ipv6status/",
    },
    "nist_usgv6": {
        "domains": 4,
        "totals": {"web": {"operational": 2, "none": 1, "not_applicable": 1},
                   "mail": {"operational": 1, "not_applicable": 3},
                   "dns": {"operational": 4}},
        "agencies": [{"name": "Department of Justice", "domains": 3,
                      "web": {"operational": 2, "none": 1}, "mail": {"operational": 1, "not_applicable": 2},
                      "dns": {"operational": 3}},
                     {"name": "Access Board", "domains": 1, "web": {"not_applicable": 1},
                      "mail": {"not_applicable": 1}, "dns": {"operational": 1}}],
        "url": "https://usgv6-deploymon.nist.gov/",
    },
```

- [ ] **Step 3: Write the failing tests** — append to `tests/test_derive.py`:

```python


def test_economy_table_joins_by_code(tmp_path):
    rows = derive.economy_table(data(tmp_path)).value
    assert [r["code"] for r in rows] == ["FR", "US", "DE"]  # BL has too few samples
    fr, us, de = rows
    assert (fr["sixlab"], fr["web"], fr["slug"]) == (39.0, 44.0, "fr")
    assert (us["sixlab"], us["web"]) == (57.2, 50.0)
    assert (de["sixlab"], de["web"]) == (None, None)


def test_economy_table_without_optional_sources(tmp_path):
    d = derive.economy_table(data(tmp_path, omit=("cisco_6lab", "vyncke")))
    assert d.sources == ("apnic",)
    assert d.value[0]["sixlab"] is None


def test_index_and_map_cover_every_economy(tmp_path):
    d = data(tmp_path)
    assert [e["code"] for e in derive.economy_index(d).value] == ["FR", "DE", "BL", "US"]  # by name
    points = {p["code"]: p for p in derive.map_points(d).value}
    assert points["US"]["iso3"] == "USA" and points["BL"]["iso3"] == "BLM"
    assert derive.iso3("ZZ") is None


def test_rir_comparison_and_total(tmp_path):
    d = data(tmp_path)
    assert [r["name"] for r in derive.rir_comparison(d).value] == ["AFRINIC", "APNIC", "ARIN", "LACNIC", "RIPE NCC"]
    assert derive.rir_total(d).value == 171550.0
    assert derive.rir_total(data(tmp_path / "x", omit=("arin_delegations",))).value == 108550.0


def test_country_lookups(tmp_path):
    d = data(tmp_path)
    assert derive.country_allocation(d, "US").value == {"blocks_32": 60000.0, "registries": ["ARIN"]}
    assert derive.country_allocation(d, "BL") is None
    assert derive.sixlab_for(d, "US").value == 57.2
    assert derive.sixlab_for(d, "DE") is None
    assert derive.vyncke_for(d, "US").value == {"web": 50.0, "email": 52.0, "dns": 92.0}
    assert derive.vyncke_for(d, "FR").value == {"web": 44.0, "email": None, "dns": None}
    assert derive.vyncke_for(d, "DE") is None


def test_website_table_sorted_by_web(tmp_path):
    rows = derive.website_table(data(tmp_path), 10).value
    assert [r["code"] for r in rows] == ["US", "FR"]
    assert rows[1] == {"code": "FR", "name": "France", "web": 44.0, "email": None, "dns": None}


def test_field_extracts_from_a_dict_datum(tmp_path):
    from web.data import field
    row = derive.economy(data(tmp_path), "US")
    assert field(row, "capable").value == 61.9
    assert field(row, "missing_key") is None
    assert field(None, "capable") is None
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_derive.py -q`
Expected: FAIL (`AttributeError: module 'web.derive' has no attribute 'economy_table'`).

- [ ] **Step 5: Implement** — in `web/data.py`, change `from dataclasses import dataclass` to `from dataclasses import dataclass, replace` and add after `combine()`:

```python


def field(d: Datum | None, key: str) -> Datum | None:
    """A Datum for one key of a dict-valued Datum, keeping its provenance."""
    if d is None or not isinstance(d.value, dict) or d.value.get(key) is None:
        return None
    return replace(d, value=d.value[key])
```

In `web/derive.py`, add `import pycountry` after `from datetime import date, timedelta`, then append:

```python


RIR_SOURCES = (
    ("afrinic_delegations", "AFRINIC"),
    ("apnic_delegations", "APNIC"),
    ("arin_delegations", "ARIN"),
    ("lacnic_delegations", "LACNIC"),
    ("ripe_delegations", "RIPE NCC"),
)
VYNCKE_SERVICES = ("web", "email", "dns")


def iso3(code: str) -> str | None:
    country = pycountry.countries.get(alpha_2=code)
    return country.alpha_3 if country else None


def _present(*datums):
    return [d for d in datums if d is not None]


def economy_table(data: Data, limit: int | None = None) -> Datum | None:
    apnic = data.datum("apnic", _ranked)
    if apnic is None:
        return None
    sixlab = data.datum("cisco_6lab", lambda p: {c["code"]: c["ipv6_users_pct"] for c in p["countries"]})
    web = data.datum("vyncke", lambda p: {r["code"]: r["green_pct"] for r in p["web"]})
    rows = [{**e, "slug": e["code"].lower(),
             "sixlab": sixlab.value.get(e["code"]) if sixlab else None,
             "web": web.value.get(e["code"]) if web else None}
            for e in sorted(apnic.value, key=lambda e: e["capable"], reverse=True)[:limit]]
    return combine(rows, _present(apnic, sixlab, web))


def economy_index(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: sorted(
        ({"code": e["code"], "name": e["name"], "slug": e["code"].lower()} for e in p["economies"]),
        key=lambda e: e["name"]))


def map_points(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: [
        {"iso3": iso3(e["code"]), "code": e["code"], "name": e["name"], "capable": e["capable"]}
        for e in p["economies"] if iso3(e["code"])])


def rir_comparison(data: Data) -> Datum | None:
    rows, inputs = [], []
    for key, name in RIR_SOURCES:
        d = data.datum(key, lambda p: p)
        if d is None:
            continue
        inputs.append(d)
        rows.append({"name": name, "total": d.value["total_blocks_32"], "countries": d.value["countries"],
                     "file_date": d.value["file_date"], "history": d.value["history"]})
    return combine(rows, inputs) if inputs else None


def rir_total(data: Data) -> Datum | None:
    rirs = rir_comparison(data)
    return None if rirs is None else combine(sum(r["total"] for r in rirs.value), [rirs])


def country_allocation(data: Data, code: str) -> Datum | None:
    hits = [(name, d) for key, name in RIR_SOURCES
            if (d := data.datum(key, lambda p: p["by_country"].get(code))) is not None]
    if not hits:
        return None
    return combine({"blocks_32": sum(d.value for _, d in hits), "registries": [name for name, _ in hits]},
                   [d for _, d in hits])


def sixlab_for(data: Data, code: str) -> Datum | None:
    return data.datum("cisco_6lab", lambda p: next(
        (c["ipv6_users_pct"] for c in p["countries"] if c["code"] == code), None))


def _vyncke_row(p: dict, code: str) -> dict | None:
    values = {s: next((r["green_pct"] for r in p[s] if r["code"] == code), None) for s in VYNCKE_SERVICES}
    return values if any(v is not None for v in values.values()) else None


def vyncke_for(data: Data, code: str) -> Datum | None:
    return data.datum("vyncke", lambda p: _vyncke_row(p, code))


def website_table(data: Data, limit: int) -> Datum | None:
    def pick(p):
        names = {r["code"]: r["name"] for s in VYNCKE_SERVICES for r in p[s]}
        rows = [{"code": code, "name": names[code], **_vyncke_row(p, code)} for code in names]
        return sorted(rows, key=lambda r: (r["web"] is None, -(r["web"] or 0)))[:limit]

    return data.datum("vyncke", pick)


def nist(data: Data) -> Datum | None:
    return data.datum("nist_usgv6", lambda p: p)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_derive.py -q && uv run pytest -q`
Expected: all pass (existing Overview tests still pass with the extended sample data).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock tests/sample_data.py tests/test_derive.py web/data.py web/derive.py
git commit -m "Join APNIC, 6lab, Vyncke, RIR and NIST data for country and adoption pages"
```

---

### Task 7: Bar, multi-line and map charts with self-hosted geography

**Files:**
- Modify: `web/charts.py` (append), `web/static/site.css` (append)
- Create: `web/static/topojson/world_110m.json`
- Test: `tests/test_charts.py` (append)

**Interfaces:**
- Consumes: `Datum`.
- Produces: `bar_chart(d, *, x, y, title, y_title) -> Markup | None`; `multi_line_chart(d, *, title, y_title, x_type="date") -> Markup | None` where `d.value = [{"name", "points": [{"x", "y"}]}]`; `choropleth(d, *, title, topojson_url) -> Markup | None` where `d.value = [{"iso3", "name", "capable"}]`; `TOPOJSON_DIR = "static/topojson/"`.

- [ ] **Step 1: Vendor the map geography (must match plotly.js 3.1.0)**

Run: `mkdir -p web/static/topojson && curl -sL https://cdn.jsdelivr.net/npm/plotly.js@3.1.0/dist/topojson/world_110m.json -o web/static/topojson/world_110m.json && python3 -c "import json;print(json.load(open('web/static/topojson/world_110m.json'))['type'])"`
Expected: `Topology`.

- [ ] **Step 2: Write the failing tests** — append to `tests/test_charts.py`:

```python


from web.charts import bar_chart, choropleth, multi_line_chart

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)


def figure_of(html):
    decoder = json.JSONDecoder()
    start = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*', html).end()
    data, i = decoder.raw_decode(html, start)
    layout, i = decoder.raw_decode(html, html.index("{", i))
    config, _ = decoder.raw_decode(html, html.index("{", i))
    return data, layout, config


def test_bar_chart():
    d = Datum([{"name": "Americas", "capable": 51.0}], ("apnic",), NOW, False)
    data, _, _ = figure_of(bar_chart(d, x="name", y="capable", title="T", y_title="Y"))
    assert data[0]["type"] == "bar" and data[0]["x"] == ["Americas"]


def test_multi_line_chart_one_trace_per_series():
    d = Datum([{"name": "A", "points": [{"x": 2000, "y": 1}]}, {"name": "B", "points": [{"x": 2000, "y": 2}]}],
              ("x",), NOW, False)
    data, layout, _ = figure_of(multi_line_chart(d, title="T", y_title="Y", x_type="linear"))
    assert [t["name"] for t in data] == ["A", "B"]
    assert layout["xaxis"]["type"] == "linear"


def test_map_uses_self_hosted_topojson():
    d = Datum([{"iso3": "USA", "name": "United States", "capable": 61.9}], ("apnic",), NOW, False)
    data, _, config = figure_of(choropleth(d, title="T", topojson_url="../static/topojson/"))
    assert data[0]["type"] == "choropleth" and data[0]["locationmode"] == "ISO-3"
    assert config["topojsonURL"] == "../static/topojson/"


def test_new_charts_return_none_without_data():
    assert bar_chart(None, x="a", y="b", title="T", y_title="Y") is None
    assert multi_line_chart(None, title="T", y_title="Y") is None
    assert choropleth(None, title="T", topojson_url="x/") is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_charts.py -q`
Expected: FAIL (`ImportError: cannot import name 'bar_chart'`).

- [ ] **Step 4: Implement** — append to `web/charts.py`:

```python


TOPOJSON_DIR = "static/topojson/"
CONFIG = {"displaylogo": False, "responsive": True}
PERCENT_RANGE = [0, 100]


def _html(fig: go.Figure, **extra_config) -> Markup:
    return Markup(fig.to_html(full_html=False, include_plotlyjs=False, config={**CONFIG, **extra_config}))


def _layout(fig: go.Figure, title: str, y_title: str) -> None:
    fig.update_layout(title=title, height=340, yaxis_title=y_title, margin=dict(l=56, r=16, t=48, b=40),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")


def bar_chart(d: Datum | None, *, x: str, y: str, title: str, y_title: str) -> Markup | None:
    if d is None:
        return None
    fig = go.Figure(go.Bar(x=[p[x] for p in d.value], y=[p[y] for p in d.value]))
    _layout(fig, title, y_title)
    fig.update_layout(showlegend=False)
    return _html(fig)


def multi_line_chart(d: Datum | None, *, title: str, y_title: str, x_type: str = "date") -> Markup | None:
    if d is None:
        return None
    fig = go.Figure([go.Scatter(x=[p["x"] for p in s["points"]], y=[p["y"] for p in s["points"]],
                                mode="lines", name=s["name"]) for s in d.value])
    _layout(fig, title, y_title)
    xaxis = dict(type=x_type)
    if x_type == "date":
        xaxis["rangeselector"] = dict(buttons=RANGE_BUTTONS, x=1, xanchor="right", y=BUTTONS_Y)
    fig.update_layout(xaxis=xaxis, legend=dict(orientation="h"))
    return _html(fig)


def choropleth(d: Datum | None, *, title: str, topojson_url: str) -> Markup | None:
    if d is None:
        return None
    fig = go.Figure(go.Choropleth(
        locations=[p["iso3"] for p in d.value], z=[p["capable"] for p in d.value],
        text=[p["name"] for p in d.value], locationmode="ISO-3", colorscale="Blues",
        zmin=PERCENT_RANGE[0], zmax=PERCENT_RANGE[1], colorbar=dict(title="%"),
        hovertemplate="%{text}: %{z:.1f}%<extra></extra>"))
    fig.update_layout(title=title, height=460, margin=dict(l=0, r=0, t=48, b=0),
                      paper_bgcolor="rgba(0,0,0,0)",
                      geo=dict(showframe=False, projection_type="natural earth", bgcolor="rgba(0,0,0,0)"))
    return _html(fig, topojsonURL=topojson_url)
```

Append to `web/static/site.css`:

```css
.chart-map { min-height: 460px; }
.country-index { columns: 3 200px; padding-left: 20px; margin: 0; }
.country-index li { break-inside: avoid; }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_charts.py -q && uv run pytest -q`
Expected: all pass. (`hovertemplate` contains `%{z:.1f}%` — the statistics guard ignores it because no digits precede a `%`.)

- [ ] **Step 6: Commit**

```bash
git add web/charts.py web/static/site.css web/static/topojson/ tests/test_charts.py
git commit -m "Add bar, multi-line and world map charts; serve map geography from the site"
```

---

### Task 8: Country Analysis page, world map and one page per economy

**Files:**
- Create: `web/pages/country_analysis.py`, `web/templates/country-analysis.html`, `tests/test_country_analysis.py`, `web/pages/country.py`, `web/templates/country.html`, `tests/test_country_pages.py`
- Modify: `web/build.py` (imports, `PAGES`, `LEGACY_PAGES`, country page loop in `build()`)

The two pages link to each other, so they land together (the Plan 1 link-check test would fail if either came alone).

**Interfaces:**
- Consumes: `derive.map_points`, `economy_table`, `economy_index`, `regions`, `nist`; `charts.choropleth`.
- Consumes (country pages): `web.data.field`, `charts.multi_line_chart`, `collect.sources.apnic_detail.TOP_ECONOMIES`.
- Produces: `web.pages.country_analysis.context(data) -> dict`; `TOPOJSON_URL = "../" + charts.TOPOJSON_DIR`; page at `/country-analysis/`. `web.pages.country.pages(data) -> list[tuple[str, dict]]` (slug, context); `context(data, code) -> dict`; pages at `/country/<slug>/` rendered with `base="../../"` and `current="country-analysis"`; `NIST_AGENCIES = 25`.

- [ ] **Step 1: Write the failing tests** — `tests/test_country_analysis.py`:

```python
from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "country-analysis" / "index.html").read_text()


def test_map_and_geography_file(tmp_path):
    out, html = render(tmp_path)
    assert "ISO-3" in html
    assert "../static/topojson/" in html
    assert (out / "static" / "topojson" / "world_110m.json").is_file()


def test_index_links_every_economy(tmp_path):
    _, html = render(tmp_path)
    index = html[html.index("All economies"):]
    for slug in ("bl", "de", "fr", "us"):
        assert f'href="../country/{slug}/"' in index


def test_leaders_regions_and_nist(tmp_path):
    _, html = render(tmp_path)
    leaders = html[html.index("<h3>Leaders</h3>"):html.index("<h3>By region</h3>")]
    assert leaders.index("France") < leaders.index("Germany")   # the map's data lists codes in another order
    assert "Americas" in html
    assert "2 of 4" in html                      # NIST web-operational domains
    assert 'href="../country/us/"' in html


def test_without_apnic(tmp_path):
    _, html = render(tmp_path, omit=("apnic",))
    assert "— source unavailable" in html
    assert "Plotly.newPlot" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_country_analysis.py -q`
Expected: FAIL (`FileNotFoundError` for `country-analysis/index.html`).

- [ ] **Step 3: Implement** — `web/pages/country_analysis.py`:

```python
"""Country Analysis: world map, leaders, regions and an index of every economy."""
from dataclasses import replace

from web import charts, derive
from web.data import Data

TOPOJSON_URL = "../" + charts.TOPOJSON_DIR  # the page lives one directory below the site root
LEADERS = 20


def context(data: Data) -> dict:
    points = derive.map_points(data)
    nist = derive.nist(data)
    return {
        "map_points": points,
        "map_chart": charts.choropleth(points, title="Users able to use IPv6 (APNIC)", topojson_url=TOPOJSON_URL),
        "leaders_size": LEADERS,
        "leaders": derive.economy_table(data, LEADERS),
        "regions": derive.regions(data),
        "index": derive.economy_index(data),
        "nist": nist,
        "nist_web": None if nist is None else replace(nist, value=nist.value["totals"]["web"].get("operational", 0)),
    }
```

`web/templates/country-analysis.html`:

```html
{% extends "base.html" %}
{% from "macros.html" import provenance, unavailable, freshness_table %}
{% block content %}
<h1>Country Analysis</h1>

{% if map_chart %}<div class="chart chart-map">{{ map_chart }}</div>{{ provenance(map_points) }}{% else %}{{ unavailable() }}{% endif %}

<div class="grid-2">
  <div class="card">
    <h3>Leaders</h3>
    {% if leaders %}
    <ol>
      {% for r in leaders.value %}<li><a href="{{ base }}country/{{ r.slug }}/">{{ r.name }}</a>: {{ r.capable | format_value("pct") }}</li>{% endfor %}
    </ol>
    {{ provenance(leaders) }}
    {% else %}{{ unavailable() }}{% endif %}
  </div>
  <div class="card">
    <h3>By region</h3>
    {% if regions %}
    <ol>
      {% for r in regions.value %}<li>{{ r.name }}: {{ r.capable | format_value("pct") }}</li>{% endfor %}
    </ol>
    {{ provenance(regions) }}
    {% else %}{{ unavailable() }}{% endif %}
  </div>
</div>

<h2>US federal government</h2>
{% if nist %}
<p>{{ nist_web.value | format_value("int") }} of {{ nist.value.domains | format_value("int") }} federal .gov domains tested by NIST serve their website over IPv6. <a href="{{ base }}country/us/">Agency details on the United States page</a>.</p>
{{ provenance(nist) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>All economies</h2>
{% if index %}
<ul class="country-index">
  {% for e in index.value %}<li><a href="{{ base }}country/{{ e.slug }}/">{{ e.name }}</a></li>{% endfor %}
</ul>
{% else %}{{ unavailable() }}{% endif %}

<h2>Data freshness</h2>
{{ freshness_table(freshness) }}
{% endblock %}
```

- [ ] **Step 4: Write the failing country page tests** — `tests/test_country_pages.py`:

```python
from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out


def page(out, slug):
    return (out / "country" / slug / "index.html").read_text()


def test_a_page_per_economy(tmp_path):
    out = render(tmp_path)
    assert sorted(p.name for p in (out / "country").iterdir()) == ["bl", "de", "fr", "us"]


def test_us_page(tmp_path):
    html = page(render(tmp_path), "us")
    assert "<title>United States of America · IPv6 Global Statistics</title>" in html
    for text in ("61.9%", "59.9%", "57.2%", "50.0%", "52.0%", "92.0%", "60,000", "ARIN", "COMCAST-7922"):
        assert text in html, text
    assert html.count("Plotly.newPlot") == 1                  # history chart
    assert 'aria-current="page">Country Analysis' in html
    assert 'href="../../static/site.css"' in html


def test_us_page_has_nist_and_dated_reference(tmp_path):
    html = page(render(tmp_path), "us")
    assert "Department of Justice" in html
    assert "OMB memorandum M-21-07" in html
    assert "Reference — last reviewed 2026-10-14" in html
    assert "Department of Justice" not in page(render(tmp_path / "b"), "fr")


def test_country_in_missing_list_says_unavailable(tmp_path):
    html = page(render(tmp_path), "de")
    assert "History for this economy could not be fetched" in html
    assert "Plotly.newPlot" not in html


def test_country_without_other_sources_renders(tmp_path):
    html = page(render(tmp_path), "bl")
    assert "97.1%" in html
    assert "collected for the 50 economies with the most APNIC samples" in html
    assert html.count("—") >= 1

```

- [ ] **Step 5: Run tests to verify they fail**

Run: `uv run pytest tests/test_country_pages.py -q`
Expected: FAIL (`FileNotFoundError` on `country/`).

- [ ] **Step 6: Implement** — `web/pages/country.py`:

```python
"""One page per economy: APNIC, 6lab, Vyncke and RIR numbers, history, networks; NIST for the US."""
from dataclasses import replace

from collect.sources.apnic_detail import TOP_ECONOMIES
from web import charts, derive
from web.data import Data, field

NIST_AGENCIES = 25
US = "US"


def _history(detail):
    if detail is None:
        return None
    points = detail.value["history"]
    return replace(detail, value=[
        {"name": "IPv6-capable", "points": [{"x": p["date"], "y": p["capable"]} for p in points]},
        {"name": "Prefers IPv6", "points": [{"x": p["date"], "y": p["preferred"]} for p in points]},
    ])


def context(data: Data, code: str) -> dict:
    row = derive.economy(data, code)
    detail = data.datum("apnic_economy_detail", lambda p: p["economies"].get(code))
    missing = data.datum("apnic_economy_detail", lambda p: code in p["missing"] or None)
    nist = derive.nist(data) if code == US else None
    nist_count = (lambda svc: None if nist is None
                  else replace(nist, value=nist.value["totals"][svc].get("operational", 0)))
    return {
        "page_title": row.value["name"] if row else code,
        "code": code,
        "economy": row,
        "capable": field(row, "capable"),
        "preferred": field(row, "preferred"),
        "samples": field(row, "samples"),
        "sixlab": derive.sixlab_for(data, code),
        "websites": derive.vyncke_for(data, code),
        "allocation": derive.country_allocation(data, code),
        "detail": detail,
        "detail_missing": missing is not None,
        "top_economies": TOP_ECONOMIES,
        "history_chart": charts.multi_line_chart(_history(detail), title="Users able to use and preferring IPv6",
                                                 y_title="Percent"),
        "networks": field(detail, "networks"),
        "nist": nist,
        "nist_web": nist_count("web"),
        "nist_mail": nist_count("mail"),
        "nist_dns": nist_count("dns"),
        "nist_agencies": None if nist is None else replace(nist, value=nist.value["agencies"][:NIST_AGENCIES]),
    }


def pages(data: Data) -> list[tuple[str, dict]]:
    index = derive.economy_index(data)
    if index is None:
        return []
    return [(e["slug"], context(data, e["code"])) for e in index.value]
```

`web/templates/country.html`:

```html
{% extends "base.html" %}
{% from "macros.html" import metric, provenance, unavailable, reference %}
{% block content %}
<p><a href="{{ base }}country-analysis/">← Country Analysis</a></p>
<h1>{{ page_title }}</h1>

<section class="metric-row" aria-label="Headline numbers">
  {{ metric("Users able to use IPv6 (APNIC)", capable, "pct") }}
  {{ metric("Users preferring IPv6 (APNIC)", preferred, "pct") }}
  {{ metric("APNIC measurement samples", samples, "int") }}
  {{ metric("IPv6 users (Cisco 6lab)", sixlab, "pct") }}
  {% if allocation %}
  <div class="metric">
    <div class="metric-label">IPv6 allocated (/32 equivalents)</div>
    <div class="metric-value">{{ allocation.value.blocks_32 | format_value("int") }}</div>
    <div class="metric-note">{{ allocation.value.registries | join(", ") }}</div>
    {{ provenance(allocation) }}
  </div>
  {% else %}
  <div class="metric"><div class="metric-label">IPv6 allocated (/32 equivalents)</div><div class="metric-value missing">—</div></div>
  {% endif %}
</section>

<h2>Top websites on IPv6</h2>
{% if websites %}
<p>Share of the country's top websites fully reachable over IPv6: web {{ websites.value.web | format_value("pct") if websites.value.web is not none else "—" }}, email {{ websites.value.email | format_value("pct") if websites.value.email is not none else "—" }}, DNS {{ websites.value.dns | format_value("pct") if websites.value.dns is not none else "—" }}.</p>
{{ provenance(websites) }}
{% else %}<p class="missing">—</p>{% endif %}

<h2>History</h2>
{% if history_chart %}
<div class="chart">{{ history_chart }}</div>
{{ provenance(detail) }}
{% elif detail_missing %}
<p class="missing">History for this economy could not be fetched from APNIC this month.</p>
{% else %}
<p class="missing">History is collected for the {{ top_economies }} economies with the most APNIC samples.</p>
{% endif %}

{% if networks %}
<h2>Largest networks</h2>
<div class="table-wrap"><table>
  <thead><tr><th>Network</th><th>IPv6-capable</th><th>Prefers IPv6</th><th>Samples</th></tr></thead>
  <tbody>
  {% for n in networks.value %}
    <tr><td>AS{{ n.asn }} {{ n.name }}</td><td>{{ n.capable | format_value("pct") }}</td><td>{{ n.preferred | format_value("pct") }}</td><td>{{ n.samples | format_value("int") }}</td></tr>
  {% endfor %}
  </tbody>
</table></div>
{{ provenance(networks) }}
{% endif %}

{% if nist %}
<h2>Federal government (NIST USGv6)</h2>
<p>NIST tests {{ nist.value.domains | format_value("int") }} federal .gov domains for IPv6 on their DNS, mail and web services.</p>
<section class="metric-row">
  {{ metric("Domains with IPv6 web", nist_web, "int") }}
  {{ metric("Domains with IPv6 mail", nist_mail, "int") }}
  {{ metric("Domains with IPv6 DNS", nist_dns, "int") }}
</section>
<div class="table-wrap"><table>
  <thead><tr><th>Agency</th><th>Domains</th><th>IPv6 web</th><th>IPv6 mail</th><th>IPv6 DNS</th></tr></thead>
  <tbody>
  {% for a in nist_agencies.value %}
    <tr><td>{{ a.name }}</td><td>{{ a.domains }}</td><td>{{ a.web.get("operational", 0) }}</td><td>{{ a.mail.get("operational", 0) }}</td><td>{{ a.dns.get("operational", 0) }}</td></tr>
  {% endfor %}
  </tbody>
</table></div>
{{ provenance(nist) }}
{% call reference(reviewed="2026-10-14") %}
<p>OMB memorandum M-21-07 (November 2020) directs federal agencies to have at least 20% of IP-enabled assets on federal networks operating IPv6-only by the end of FY2023, 50% by the end of FY2024 and 80% by the end of FY2025.</p>
{% endcall %}
{% endif %}
{% endblock %}
```

In `web/build.py`: change the page import to `from web.pages import country, country_analysis, overview`; add `Page("country-analysis", "Country Analysis", country_analysis.context),` as the last entry of `PAGES`; add `"Country Analysis": "country-analysis/",` as the last entry of `LEGACY_PAGES`; and insert before `return check_reference_dates(TEMPLATES, now)`:

```python
    country_template = env.get_template("country.html")
    for slug, page_context in country.pages(data):
        context = {**common, "current": "country-analysis", **page_context}
        _write(out_dir / "country" / slug / "index.html", country_template.render(context, base="../../"))
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_country_analysis.py tests/test_country_pages.py -q && uv run pytest -q`
Expected: all pass, including `test_internal_links_are_relative_and_resolve` from Plan 1.

- [ ] **Step 8: Commit**

```bash
git add web/ tests/test_country_analysis.py tests/test_country_pages.py
git commit -m "Add Country Analysis with a self-hosted world map, and a page per economy"
```

---

### Task 9: Global Adoption page

**Files:**
- Create: `web/pages/global_adoption.py`, `web/templates/global-adoption.html`, `tests/test_global_adoption.py`
- Modify: `web/build.py` (imports, `PAGES`, `LEGACY_PAGES`)

**Interfaces:**
- Consumes: Task 6 derive functions; Task 8 country pages (links); Plan 1 `derive.consensus*`, `economies_above`, `economies_considered`, `top_economy`, `regions`, `MIN_SAMPLES`; Task 7 charts.
- Produces: `web.pages.global_adoption.context(data) -> dict`; `TOP_TABLE = 20`; page at `/global-adoption/`.

- [ ] **Step 1: Write the failing tests** — `tests/test_global_adoption.py`:

```python
from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "global-adoption" / "index.html").read_text()


def test_headline_numbers(tmp_path):
    _, html = render(tmp_path)
    assert '<div class="metric-value">47.7%</div>' in html          # consensus
    assert '<div class="metric-value">85.6%</div>' in html          # highest capability
    assert "France" in html
    assert '<div class="metric-value">171,550</div>' in html        # five RIRs
    assert "5 of 5 registries" in html


def test_top_table_joins_sources(tmp_path):
    _, html = render(tmp_path)
    table = html[html.index("Top economies"):html.index("Address allocations")]
    assert table.index("France") < table.index("United States of America") < table.index("Germany")
    assert "39.0%" in table and "44.0%" in table and "57.2%" in table
    assert 'href="../country/fr/"' in table
    assert "Saint Barthelemy" not in table


def test_missing_optional_source_shows_dash(tmp_path):
    _, html = render(tmp_path, omit=("cisco_6lab",))
    table = html[html.index("Top economies"):html.index("Address allocations")]
    assert "—" in table and "57.2%" not in table


def test_rir_and_website_sections(tmp_path):
    _, html = render(tmp_path)
    assert "RIPE NCC" in html and "52,000" in html
    assert html.count("Plotly.newPlot") >= 2   # regions bar + RIR growth
    sites = html[html.index("Websites on IPv6"):]
    assert sites.index("United States of America") < sites.index("France")


def test_nav_and_legacy_redirect(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">Global Adoption' in html
    assert '"Global Adoption": "global-adoption/"' in (out / "index.html").read_text()


def test_global_adoption_without_any_data(tmp_path):
    out = tmp_path / "dist"
    build(tmp_path / "no-data", out, NOW)
    assert "— source unavailable" in (out / "global-adoption" / "index.html").read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_global_adoption.py -q`
Expected: FAIL (`FileNotFoundError` for `global-adoption/index.html`).

- [ ] **Step 3: Implement** — `web/pages/global_adoption.py`:

```python
"""Global Adoption: who has IPv6, by economy, region and registry."""
from dataclasses import replace

from web import charts, derive
from web.data import Data, field
from web.pages.overview import ABOVE_THRESHOLD

TOP_TABLE = 20


def _rir_history(rirs):
    if rirs is None:
        return None
    return replace(rirs, value=[{"name": r["name"], "points": [{"x": h["year"], "y": h["blocks_32"]}
                                                              for h in r["history"]]} for r in rirs.value])


def context(data: Data) -> dict:
    components = derive.consensus_components(data)
    present = sum(1 for _, d in components if d is not None)
    top = derive.top_economy(data)
    regions = derive.regions(data)
    rirs = derive.rir_comparison(data)
    return {
        "consensus": derive.consensus(components),
        "consensus_note": f"{present} of {len(components)} sources",
        "above_threshold": ABOVE_THRESHOLD,
        "above": derive.economies_above(data, ABOVE_THRESHOLD),
        "considered": derive.economies_considered(data),
        "min_samples_label": f"{derive.MIN_SAMPLES:,}",
        "top_economy": top,
        "top_capable": field(top, "capable"),
        "rir_total": derive.rir_total(data),
        "rir_count_note": f"{len(rirs.value) if rirs else 0} of {len(derive.RIR_SOURCES)} registries",
        "regions": regions,
        "regions_chart": charts.bar_chart(regions, x="name", y="capable",
                                          title="Users able to use IPv6, by region", y_title="Percent"),
        "top_table_size": TOP_TABLE,
        "top_table": derive.economy_table(data, TOP_TABLE),
        "rirs": rirs,
        "rir_chart": charts.multi_line_chart(_rir_history(rirs), title="IPv6 allocated over time (/32 equivalents)",
                                             y_title="/32 equivalents", x_type="linear"),
        "websites": derive.website_table(data, TOP_TABLE),
        "cf_ipv6": data.datum("cloudflare_ip_version", lambda p: p["latest_ipv6"]),
        "sites": data.datum("tranco_aaaa", lambda p: p["percentage"]),
    }
```

`web/templates/global-adoption.html`:

```html
{% extends "base.html" %}
{% from "macros.html" import metric, provenance, unavailable, freshness_table %}
{% block content %}
<h1>Global IPv6 Adoption</h1>

<section class="metric-row" aria-label="Headline numbers">
  {{ metric("Global IPv6 adoption (consensus)", consensus, "pct", note=consensus_note) }}
  {{ metric("Economies ≥ " ~ above_threshold ~ "% IPv6-capable", above, "int",
            note="of " ~ considered.value ~ " with at least " ~ min_samples_label ~ " APNIC samples" if considered else None) }}
  {{ metric("Highest share of IPv6-capable users", top_capable, "pct", note=top_economy.value.name if top_economy else None) }}
  {{ metric("IPv6 allocated by the RIRs (/32 equivalents)", rir_total, "int", note=rir_count_note) }}
  {{ metric("Cloudflare HTTP requests over IPv6", cf_ipv6, "pct") }}
  {{ metric("Top sites with IPv6 (AAAA)", sites, "pct") }}
</section>

<h2>By region</h2>
{% if regions_chart %}<div class="chart">{{ regions_chart }}</div>{{ provenance(regions) }}{% else %}{{ unavailable() }}{% endif %}

<h2>Top economies</h2>
<p>The {{ top_table_size }} economies with the highest share of IPv6-capable users (APNIC), among those with at least {{ min_samples_label }} samples. 6lab is a second measurement of IPv6 users; the last column is the share of the country's top websites fully reachable over IPv6 (Vyncke).</p>
{% if top_table %}
<div class="table-wrap"><table>
  <thead><tr><th>#</th><th>Economy</th><th>IPv6-capable</th><th>Prefers IPv6</th><th>Samples</th><th>IPv6 users (6lab)</th><th>Top websites on IPv6</th></tr></thead>
  <tbody>
  {% for r in top_table.value %}
    <tr><td>{{ loop.index }}</td><td><a href="{{ base }}country/{{ r.slug }}/">{{ r.name }}</a></td>
      <td>{{ r.capable | format_value("pct") }}</td><td>{{ r.preferred | format_value("pct") }}</td>
      <td>{{ r.samples | format_value("int") }}</td>
      <td>{{ r.sixlab | format_value("pct") if r.sixlab is not none else "—" }}</td>
      <td>{{ r.web | format_value("pct") if r.web is not none else "—" }}</td></tr>
  {% endfor %}
  </tbody>
</table></div>
{{ provenance(top_table) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Address allocations by registry</h2>
{% if rirs %}
<div class="table-wrap"><table>
  <thead><tr><th>Registry</th><th>IPv6 /32 equivalents</th><th>Economies</th><th>Registry file</th></tr></thead>
  <tbody>
  {% for r in rirs.value %}
    <tr><td>{{ r.name }}</td><td>{{ r.total | format_value("int") }}</td><td>{{ r.countries }}</td><td>{{ r.file_date }}</td></tr>
  {% endfor %}
  </tbody>
</table></div>
{% if rir_chart %}<div class="chart">{{ rir_chart }}</div>{% endif %}
<p class="provenance">Growth is plotted by each record's allocation date; records without a date count in the totals but not in the chart.</p>
{{ provenance(rirs) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Websites on IPv6 by country</h2>
<p>Share of each country's top websites (by country-code domain) whose web, email and DNS services are fully reachable over IPv6.</p>
{% if websites %}
<div class="table-wrap"><table>
  <thead><tr><th>Country</th><th>Web</th><th>Email</th><th>DNS</th></tr></thead>
  <tbody>
  {% for r in websites.value %}
    <tr><td>{{ r.name }}</td>
      <td>{{ r.web | format_value("pct") if r.web is not none else "—" }}</td>
      <td>{{ r.email | format_value("pct") if r.email is not none else "—" }}</td>
      <td>{{ r.dns | format_value("pct") if r.dns is not none else "—" }}</td></tr>
  {% endfor %}
  </tbody>
</table></div>
{{ provenance(websites) }}
{% else %}{{ unavailable() }}{% endif %}

<h2>Data freshness</h2>
{{ freshness_table(freshness) }}
{% endblock %}
```

In `web/build.py`: change the page import to `from web.pages import country, country_analysis, global_adoption, overview`; replace the `PAGES` and `LEGACY_PAGES` definitions with:

```python
PAGES = (
    Page("overview", "Overview", overview.context),
    Page("global-adoption", "Global Adoption", global_adoption.context),
    Page("country-analysis", "Country Analysis", country_analysis.context),
)

# Old Streamlit ?page= names -> new paths. Later plans add the remaining pages;
# names not listed here land on the Overview.
LEGACY_PAGES = {
    "Overview": "overview/",
    "Combined View": "overview/",
    "Global Adoption": "global-adoption/",
    "Country Analysis": "country-analysis/",
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_global_adoption.py -q && uv run pytest -q`
Expected: all pass (country pages exist since Task 8, so the link test resolves `../country/<cc>/`).

- [ ] **Step 5: Commit**

```bash
git add web/ tests/test_global_adoption.py
git commit -m "Add Global Adoption page built from APNIC, 6lab, Vyncke and RIR data"
```

---

### Task 10: End-to-end run, visual check, docs

**Files:**
- Modify: `README.md` (page list in the "Static site" section)

- [ ] **Step 1: Run every source against the live sites and time it**

```bash
time uv run python -m collect.run --data-dir data --force > /tmp/collect.log 2>&1; tail -3 /tmp/collect.log
python3 -c "import json;[print(k, v['status'], (v.get('error') or '')[:120]) for k, v in json.load(open('data/manifest.json')).items()]"
```
Expected: every new source `ok` (Cloudflare `error` or `not_configured` until its key works; ISOC `not_configured`); total time well under 30 minutes. If a new source fails, read its error, fix the parser against the live page with a new failing test first, and re-run.

- [ ] **Step 2: Sanity-check values against the sources**

```bash
python3 - <<'EOF'
import json
nist = json.load(open("data/nist_usgv6.json")); print("NIST", nist["domains"], nist["totals"]["web"])
det = json.load(open("data/apnic_economy_detail.json")); print("detail", len(det["economies"]), det["missing"])
for k in ("ripe_delegations", "arin_delegations", "apnic_delegations"):
    d = json.load(open(f"data/{k}.json")); print(k, d["file_date"], d["total_blocks_32"], d["countries"], d["history"][-1])
print("6lab", len(json.load(open("data/cisco_6lab.json"))["countries"]))
print("vyncke", {s: len(json.load(open("data/vyncke.json"))[s]) for s in ("web", "email", "dns")})
EOF
```
Expected: NIST web `operational` equals the "N Domains with IPv6 Operational Web Service" headline at https://usgv6-deploymon.nist.gov/cgi-bin/generate-all.www; RIR file dates are this week; 50 detail economies with at most 5 missing.

- [ ] **Step 3: Build and look at the pages**

```bash
uv run python -m web.build --data-dir data --out dist
uv run python -m http.server 8765 --directory dist &
```
Open `http://localhost:8765/global-adoption/`, `/country-analysis/`, `/country/us/`, `/country/fr/` and `/?page=Country%20Analysis`. Check: the map draws countries (the geography file loads from `/static/topojson/`, no request to cdn.plot.ly in the browser's network tab); tables link to country pages; the US page shows NIST agencies and the reference note; theme toggle works; layout fits 375px. Stop the server.

- [ ] **Step 4: Update the README page list** — in the "Static site (GitHub Pages)" section, after the `web/` bullet, add:

```markdown
- Pages so far: Overview, Global Adoption, Country Analysis, and one page per economy
  (`/country/<code>/`). The remaining Streamlit pages are converted in later plans.
```

- [ ] **Step 5: Full suite and commit**

Run: `uv run pytest -q`
Expected: all pass.

```bash
git add README.md
git commit -m "Document the Global Adoption, Country Analysis and per-country pages"
```
