# Static Site Plan 7: Data Sources Page and Switch-over Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the migration: a Data Sources page generated from the source registry, every old `?page=` name redirected, a 404 page, and the Streamlit app and its dependencies removed.

**Spec:** `docs/superpowers/specs/2026-10-14-static-site-migration-design.md`, **Amendment 4 → Data Sources, Switch-over**. DNS already points at GitHub Pages; the HTTPS certificate and "Enforce HTTPS" are the owner's (Pages settings), and so is retiring the container.

## Global Constraints

- Work on `staging`; no Claude attribution; check that a PR from `staging` is open before pushing (open one if not).
- The Data Sources page states no statistics beyond those already collected; every source description comes from the collector module's own docstring.
- Removing the Streamlit files changes `main`'s Streamlit code, which makes the old container pull on merge. The PR must say so: the owner decides when to merge relative to retiring the container.
- Page `/data-sources/`, last in the nav; legacy `"Data Sources": "data-sources/"`.

## Review Focus

1. **Every old Streamlit page name redirects** (Overview, Combined View, Global Adoption, Country Analysis, Cloud Services, Extended Data Sources, BGP Statistics, Historical Trends, Data Sources). Test: `test_every_old_page_name_redirects`.
2. **The 404 page works at any depth.** It uses root-absolute links (the site is at the domain root), and only it is exempt from the relative-link rule. Test: `test_404_page_uses_root_links`.
3. **Nothing imports a removed module.** Test suite plus `python -m collect.run --help` and a build run after removal.

---

### Task 1: Data Sources page generated from the registry

**Files:** Create `web/pages/data_sources.py`, `web/templates/data-sources.html`, `tests/test_data_sources_page.py`; Modify `web/build.py`

**Interfaces:** `web.pages.data_sources.describe(src) -> str` (first paragraph of the collector module's docstring, whitespace-collapsed); `context(data) -> dict` with `sources` (status rows plus `description`, `requires_env`), `references` (`[{"file","what","last_reviewed"}]`).

- [ ] **Step 1: Failing tests** — `tests/test_data_sources_page.py`:

```python
from collect.registry import SOURCES
from tests.sample_data import NOW, write_sample_data
from web.build import LEGACY_PAGES, build
from web.pages.data_sources import describe

OLD_PAGES = ["Overview", "Combined View", "Global Adoption", "Country Analysis", "Cloud Services",
             "Extended Data Sources", "BGP Statistics", "Historical Trends", "Data Sources"]


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "data-sources" / "index.html").read_text()


def test_every_source_is_described(tmp_path):
    _, html = render(tmp_path)
    for key, src in SOURCES.items():
        if key.startswith("test_"):
            continue
        assert src.title in html, key
        assert describe(src), key


def test_description_comes_from_the_collector_module():
    assert describe(SOURCES["bgp_v6_table"]).startswith("IPv6 BGP table size history")


def test_reference_files_and_keys(tmp_path):
    _, html = render(tmp_path, not_configured=("isoc_pulse",))
    for name in ("cloud_providers.toml", "carriers.toml", "government_domains.toml"):
        assert name in html
    assert "ISOC_PULSE_API_KEY" in html and "CLOUDFLARE_API_KEY" in html


def test_every_old_page_name_redirects():
    assert set(OLD_PAGES) <= set(LEGACY_PAGES)
    assert LEGACY_PAGES["Data Sources"] == "data-sources/"
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_data_sources_page.py -q` → FAIL (`ImportError`).

- [ ] **Step 3: Implement** — `web/pages/data_sources.py`:

```python
"""Data Sources: every source the site collects, how often, and how it's doing; plus the
hand-maintained reference files. Generated from the registry so it can't drift."""
import inspect
import re

from collect.registry import SOURCES, Source
from web import reference
from web.data import Data


def describe(src: Source) -> str:
    doc = inspect.getmodule(src.fetch).__doc__ or ""
    return re.sub(r"\s+", " ", doc.strip().split("\n\n")[0])


def context(data: Data) -> dict:
    rows = []
    for row in data.status_rows():
        src = SOURCES[row["key"]]
        rows.append({**row, "description": describe(src), "requires_env": src.requires_env})
    return {
        "sources": rows,
        "references": [
            {"file": "reference/cloud_providers.toml", "what": "Curated IPv6 support details for cloud providers",
             "last_reviewed": min(p["last_reviewed"] for p in reference.load_cloud_providers())},
            {"file": "reference/carriers.toml", "what": "Which access networks are shown",
             "last_reviewed": reference.load_carriers()["last_reviewed"]},
            {"file": "reference/government_domains.toml", "what": "Which government websites are checked",
             "last_reviewed": reference.load_government()["last_reviewed"]},
        ],
    }
```

`web/templates/data-sources.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>Data Sources</h1>
<p>Every number on this site comes from one of the sources below. A daily job at 00:00 UTC fetches each source that is due, keeps the last good copy when a fetch fails, and rebuilds the site. A value whose source has not updated for twice its usual interval is marked stale. Nothing is estimated or typed in by hand except the reference lists at the end, which are labelled with their review dates.</p>

<h2>Collected sources</h2>
{% for s in sources %}
<details class="source" id="{{ s.key }}">
  <summary>{{ s.title }} — {{ s.status | replace("_", " ") }}{% if s.stale %} <span class="stale">⚠ stale</span>{% endif %}</summary>
  <p>{{ s.description }}</p>
  <ul>
    <li>Link: <a href="{{ s.url }}">{{ s.url }}</a></li>
    <li>Re-fetched every {{ s.ttl_days }} day{{ "s" if s.ttl_days != 1 else "" }}; last success {{ s.last_success | date_only }}, last attempt {{ s.last_attempt | date_only }}</li>
    {% if s.requires_env %}<li>Needs the secret {{ s.requires_env | join(", ") }}</li>{% endif %}
    {% if s.error %}<li class="provenance">Last error: {{ s.error }}</li>{% endif %}
  </ul>
</details>
{% endfor %}

<h2>Reference lists</h2>
<div class="table-wrap"><table>
  <thead><tr><th>File</th><th>What it holds</th><th>Last reviewed</th></tr></thead>
  <tbody>{% for r in references %}<tr><td><code>{{ r.file }}</code></td><td>{{ r.what }}</td><td>{{ r.last_reviewed }}</td></tr>{% endfor %}</tbody>
</table></div>

<h2>Source code</h2>
<p>The collectors, page templates and tests are on <a href="https://github.com/buraglio/ipv6stats">GitHub</a>.</p>
{% endblock %}
```

In `web/build.py`: add `data_sources` to the `from web.pages import ...` line; append `Page("data-sources", "Data Sources", data_sources.context),` as the last `PAGES` entry and `"Data Sources": "data-sources/",` as the last `LEGACY_PAGES` entry; change the `LEGACY_PAGES` comment to `# Old Streamlit ?page= names -> new paths; unknown names land on the Overview.`

- [ ] **Step 4: Verify** — `uv run pytest tests/test_data_sources_page.py -q && uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add web/ tests/ && git commit -m "Add a Data Sources page generated from the source registry"`

---

### Task 2: 404 page

**Files:** Create `web/templates/404.html`; Modify `web/build.py`, `tests/test_build.py`

**Interfaces:** `build()` writes `dist/404.html` rendered with `base="/"`; the relative-link test skips `404.html`.

- [ ] **Step 1: Failing test** — append to `tests/test_build.py`:

```python


def test_404_page_uses_root_links(tmp_path):
    # GitHub Pages serves 404.html at any depth, so its links must be root-absolute.
    page = (built(tmp_path) / "404.html").read_text()
    assert 'href="/static/site.css"' in page and 'href="/overview/"' in page
    assert "Page not found" in page
```

and change the loop in `test_internal_links_are_relative_and_resolve` from `for page in out.rglob("*.html"):` to:

```python
    for page in out.rglob("*.html"):
        if page.name == "404.html":
            continue
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_build.py -q` → FAIL (`FileNotFoundError: .../404.html`).

- [ ] **Step 3: Implement** — `web/templates/404.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>Page not found</h1>
<p>That page doesn't exist. Try the <a href="{{ base }}overview/">Overview</a> or the menu above.</p>
{% endblock %}
```

In `web/build.py`, before the final `return`, add:

```python
    not_found = env.get_template("404.html")
    _write(out_dir / "404.html", not_found.render({**common, "page_title": "Page not found", "current": ""}, base="/"))
```

- [ ] **Step 4: Verify** — `uv run pytest -q` → all pass.
- [ ] **Step 5: Commit** — `git add web/ tests/test_build.py && git commit -m "Add a 404 page"`

---

### Task 3: Remove the Streamlit app and rewrite the README

**Files:** Delete `app.py`, `cloud_data.py`, `components.py`, `data_manager.py`, `data_sources.py`, `dataframe_utils.py`, `debug_cloudflare_api.py`, `performance_config.py`, `utils.py`, `visualization.py`, `page_modules/`, `requirements.txt`, `ipv6stats.service`, `start_ipv6stats.sh`, `replit.md`, `repl_nix_workspace.egg-info/`, `test_cloudflare_api.py`, `test_optimizations.py`, `add-cloudflare-api-token.md`, `.streamlit/`, `img/v6stats-clouddash.png`; Modify `pyproject.toml`, `uv.lock`, `.env.example`, `README.md`

- [ ] **Step 1: Remove the files** — `git rm -rq app.py cloud_data.py components.py data_manager.py data_sources.py dataframe_utils.py debug_cloudflare_api.py performance_config.py utils.py visualization.py page_modules requirements.txt ipv6stats.service start_ipv6stats.sh replit.md repl_nix_workspace.egg-info test_cloudflare_api.py test_optimizations.py add-cloudflare-api-token.md .streamlit img`

- [ ] **Step 2: Dependencies** — in `pyproject.toml`, set `description = "IPv6 Statistics - a static site of global IPv6 adoption, rebuilt daily from collected data"` and replace the dependency list with:

```toml
dependencies = [
    "requests>=2.32.4",
    "plotly>=6.3.0",
    "python-dotenv>=1.0.0",
    "jinja2>=3.1.4",
    "dnspython>=2.6.1",
    "pycountry>=24.6.1",
]
```

Run: `uv lock && uv sync`.

- [ ] **Step 3: `.env.example`** — replace with:

```bash
# Local secrets for `python -m collect.run`. Copy to .env (it is gitignored).
# In GitHub Actions the same names are repository secrets.

# Cloudflare Radar API token (the ~40-character token secret, not the 32-character token ID).
# Create at https://dash.cloudflare.com/profile/api-tokens with permission Account > Radar > Read.
CLOUDFLARE_API_KEY=

# Internet Society Pulse API key, from https://pulse.internetsociety.org/en/api/
ISOC_PULSE_API_KEY=
```

- [ ] **Step 4: README** — replace `README.md` with:

```markdown
# IPv6 Statistics

A static site of global IPv6 adoption, routing and deployment data, rebuilt every day from
the sources it collects: https://stats.ipv6.army

Every number on the site comes from a collected source and shows where it came from and how
fresh it is. Nothing is estimated or typed in; the only hand-maintained content is a few
reference lists, which show their review dates.

## How it works

- `collect/` — one module per data source (`collect/sources/`). `uv run python -m collect.run --data-dir data`
  fetches the sources that are due and writes `data/<source>.json` and `data/manifest.json`. A failed fetch
  keeps the previous data. `--force` re-fetches everything; `--only <source>` fetches one.
- `web/` — renders the site from that JSON with no network access:
  `uv run python -m web.build --data-dir data --out dist`.
- `reference/` — hand-maintained lists (cloud provider details, carriers, government domains). Update an
  entry's `last_reviewed` when you check it; the build warns after 180 days.
- `.github/workflows/publish.yml` — runs both daily at 00:00 UTC (and on pushes to `main` or "Run workflow"),
  saves the data to the `data` branch, and deploys to GitHub Pages. If more than a quarter of the configured
  sources fail, nothing is published and GitHub emails the failure. `test.yml` runs the tests on `staging`
  and pull requests.
- `data/history.json` (on the `data` branch) holds this site's own measurements over time.

## Local development

    uv sync
    cp .env.example .env     # add keys if you have them
    uv run python -m collect.run --data-dir data
    uv run python -m web.build --data-dir data --out dist
    uv run python -m http.server --directory dist
    uv run pytest

## Secrets

- `CLOUDFLARE_API_KEY` — Cloudflare Radar API token (the ~40-character token secret, not the token ID),
  permission Account > Radar > Read.
- `ISOC_PULSE_API_KEY` — Internet Society Pulse API key.

Without a key, that source shows as "not configured" and isn't counted as a failure.

## Adding a source

Add a module in `collect/sources/` with a `@source(key, interval, title=..., url=...)` fetch function that
returns parsed data or raises, register it in `collect/sources/__init__.py`, record a real response as a
test fixture, and add tests. A test fails if a statistic is typed into the code or templates.

Design notes: `docs/superpowers/specs/2026-10-14-static-site-migration-design.md`.
```

- [ ] **Step 5: Verify** — `uv run pytest -q` → all pass; `uv run python -m collect.run --help` prints usage; `uv run python -m web.build --data-dir data --out dist` builds.
- [ ] **Step 6: Commit** — `git add -A . ':!data' ':!dist' && git commit -m "Remove the Streamlit app and its dependencies; rewrite the README for the static site"`

---

### Task 4: Final check

- [ ] **Step 1:** full build from today's data; serve; click through every nav page, `/?page=Data%20Sources`, a missing path (404), and `/country/us/`.
- [ ] **Step 2:** whole-branch review (fresh reviewer), fix pass, push, PR noting the container pulls on merge.
