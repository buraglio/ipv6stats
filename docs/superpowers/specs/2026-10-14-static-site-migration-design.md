# Static Site Migration (GitHub Pages) — Design

**Date:** 2026-10-14
**Branch:** `static-site` (from `staging`)
**Status:** Approved in brainstorming; awaiting written-spec review

## Goal

Replace the self-hosted Streamlit server (systemd unit on a Linux container) with a
static site on GitHub Pages, rebuilt daily from freshly collected data by GitHub
Actions. Every statistic on the site must come from data collected by the pipeline;
nothing is hard-coded except clearly labeled reference material.

## Success criteria

1. stats.ipv6.army is served from GitHub Pages over IPv4 and IPv6.
2. A scheduled workflow runs daily at 00:00 UTC, collects data, builds, and deploys
   without manual intervention.
3. A failed source never removes or fabricates data: the page shows the last good
   value with its real date, or "source unavailable".
4. No statistic is a literal in templates, page code, or collectors. Enforced by
   tests and by the build.
5. All existing pages are present (Combined View merged into Overview), and old
   `?page=` URLs redirect to the new paths.
6. The workflow fails visibly (GitHub email) and does not publish when too many
   sources fail.

## Non-goals

- Live/on-request data fetching in the browser.
- A JavaScript front-end framework or front-end build tooling.
- New data sources beyond what is needed to replace hard-coded numbers.
- Netlify support (ruled out: Python collectors can't run in Netlify functions; IPv6
  on Netlify custom domains is unreliable).

## Current state (relevant findings)

- `app.py` (4.9k lines) holds all 9 pages, selected by `if current_view == ...`
  blocks (`app.py:662`–`4747`), with `?page=` navigation and a theme toggle.
- `page_modules/` and `data_manager.py` are not imported by `app.py` (dead code).
- `data_sources.py` uses Streamlit only for 51 `@st.cache_data` decorators.
  `visualization.py` has no Streamlit dependency.
- Page code calls 45 distinct `data_collector.*` methods directly, some with
  arguments (`get_global_historical_data(time_range)`,
  `get_facebook_historical_stats(time_range)`, `get_country_code_from_name(...)`).
- 10 collector paths return hard-coded data marked `'fallback': True`, including
  `_get_fallback_asn_data`.
- Hard-coded statistics exist in page code (e.g. Combined View at `app.py:679`–`695`:
  "49%", "228,789", "12%") and in collectors (e.g. `get_cloud_ipv6_status`,
  `data_sources.py:1065`).
- Overview uses `get_bgp_stats()`; Combined View uses `get_current_bgp_stats()`.
- One secret: `CLOUDFLARE_API_KEY` (read via `os.environ`).

## Architecture

```
ipv6stats/
  collect/
    sources.py        # collectors, ported from data_sources.py, no Streamlit
    registry.py       # @source(key, ttl) decorator + registry
    run.py            # runs due collectors → data/<key>.json + data/manifest.json
  web/                # not `site/`: that name is taken by Python's stdlib
    build.py          # data/*.json → dist/ (no network access)
    charts.py         # ported from visualization.py
    derive.py         # derived values computed from collected data
    pages/<slug>.py   # one per page: context(data) -> dict
    templates/        # base.html, macros.html, <slug>.html
    static/           # CSS, plotly.min.js, Leaflet, small JS (toggles, theme, redirect)
  tests/
    fixtures/<key>/   # recorded real responses per source
  data/               # working copy of the `data` branch (gitignored on code branches)
  .github/workflows/publish.yml
```

The only interface between `collect/` and `web/` is the JSON in `data/`.
`web/build.py` makes no network requests, so the site can be rebuilt locally from
saved data in seconds.

**Removed:** Streamlit, streamlit-folium, `ipv6stats.service`, `start_ipv6stats.sh`,
`data_manager.py`, `page_modules/`, `performance_config.py`, `components.py`,
`app.py` (after its content is ported), `test_cloudflare_api.py`,
`debug_cloudflare_api.py`, `test_optimizations.py`, `replit.md`,
`repl_nix_workspace.egg-info/`.

**Moved:** helpers in `utils.py` and `dataframe_utils.py` that are still used move
into `collect/` or `web/`; the rest are deleted. `cloud_data.py` becomes reference
content for the Cloud Services page, with its statistics removed or connected to data
per the static data policy.

## Data collection

### Decoupling

- Each `@st.cache_data(ttl=…)` becomes `@source(key, ttl)`. `key` is the JSON
  filename; `ttl` is the re-fetch interval. `_self` becomes `self`. Method bodies
  otherwise stay the same.
- Every one of the 45 methods called from page code becomes either:
  - a **collected source** (fetched by `run.py`), or
  - a **derived value** in `web/derive.py`, computed at build time from collected
    JSON (e.g. `get_global_ipv6_consensus`, `get_country_code_from_name`).
- Methods taking arguments are restructured to collect the full dataset once:
  `get_global_historical_data` and `get_facebook_historical_stats` collect all
  history; range filtering happens in the chart.
- BGP data comes only from `get_current_bgp_stats()`. `get_bgp_stats()` is removed
  and its callers switched over.

### No fabricated data

- A collector returns parsed data or raises. All `'fallback': True` paths and
  `_get_fallback_asn_data` are removed.
- Hard-coded statistics in collectors are removed or replaced by collected data (see
  "Static data policy").

### Manifest and re-fetch intervals

`data/manifest.json`, one entry per source:

```json
{
  "cloudflare_stats": {
    "last_attempt": "2026-10-14T00:03:12Z",
    "last_success": "2026-10-14T00:03:12Z",
    "status": "ok",
    "error": null,
    "ttl_seconds": 2592000
  }
}
```

- `run.py` fetches only sources whose `last_success + ttl` has passed, or that have
  never succeeded. Intervals stay as they are today: 24h for BGP-related sources,
  30 days for the rest. `--force` fetches everything; `--only <key>` fetches one.
- A source's JSON is overwritten only after a fetch that succeeds and parses. On
  failure, the previous JSON stays and the manifest records `status: "error"` and the
  message.
- Concurrency: a thread pool with 3 workers (same as today); per-request timeouts kept.

### Failure threshold

- If more than 25% of the sources due in a run fail, `run.py` exits non-zero. The
  workflow then stops before deploy; the live site keeps the previous build and
  GitHub emails the failure.
- Failures under the threshold are logged as workflow warnings (`::warning::`) and
  shown on the site.

## Workflow (`.github/workflows/publish.yml`)

- **Triggers:** `schedule: cron "0 0 * * *"`, `workflow_dispatch` (with a `force`
  input), and `push` to the deploy branch.
- **`concurrency: pages`**, `cancel-in-progress: false`; job `timeout-minutes: 30`.
- **Permissions:** `contents: write` (data branch), `pages: write`, `id-token: write`.
- **Steps:**
  1. Check out code; check out the `data` branch into `data/` (create it as an orphan
     branch on first run).
  2. `astral-sh/setup-uv`; `uv sync --frozen`.
  3. `uv run pytest`.
  4. `uv run python -m collect.run` with `CLOUDFLARE_API_KEY` from secrets. Skipped
     on `push` events, which rebuild from existing data.
  5. Commit changed files in `data/` to the `data` branch and push. The daily
     commits also keep the scheduled workflow active (GitHub turns off scheduled
     workflows after 60 days with no repository activity).
  6. `uv run python -m web.build` → `dist/`.
  7. `actions/upload-pages-artifact` → `actions/deploy-pages`.
- Scheduled runs may start 5–30 minutes late; the footer shows the actual build time.

## Site build

### Pages and URLs

| Old `?page=` | New path |
|---|---|
| Overview, Combined View | `/` and `/overview/` |
| Cloud Services | `/cloud-services/` |
| Extended Data Sources | `/extended-data-sources/` |
| Global Adoption | `/global-adoption/` |
| Country Analysis | `/country-analysis/` |
| BGP Statistics | `/bgp-statistics/` |
| Historical Trends | `/historical-trends/` |
| Data Sources | `/data-sources/` |

A script on `/` redirects `?page=<old name>` to the new path.

### Converting the pages

Each `elif current_view == …` block becomes `web/pages/<slug>.py` with
`context(data) -> dict` plus `templates/<slug>.html`. The Streamlit pieces map as:

| Streamlit | Static version |
|---|---|
| `st.metric` | `metric(label, datum, delta=None)` macro |
| `st.plotly_chart` | `fig.to_html(full_html=False, include_plotlyjs=False)` |
| `st.expander` / `st.tabs` | `<details>` / CSS tabs |
| `st.dataframe` | `df.to_html()` with site table styles |
| `st_folium` map | `m.save()` to `country-analysis/map.html`, shown in an `<iframe>` |
| `st.columns` | CSS grid |

### Overview (merged)

`/overview/` contains everything from Overview and Combined View, with duplicates
removed, in this order:

1. **Headline numbers (one row):** global IPv6 adoption (consensus); BGP IPv6
   prefixes (from `get_current_bgp_stats()`); IPv6 websites (from ISOC Pulse);
   Facebook IPv6 traffic. "IPv6-only Support 12%" is **removed**, since no collected
   data supports it.
2. **Current Trends** (LACNIC, Facebook, Cloudflare).
3. **Detailed Statistics by Source** (Google, ISOC Pulse, BGP routing, Facebook) as
   `<details open>`.
4. **Key Combined Insights.**
5. **Recent Updates.**
6. **Source freshness:** per-source "last updated" notes from the manifest.

### Dropdowns

- **Global Adoption source picker (11 options):** all sections rendered; a `<select>`
  shows one at a time and calls `Plotly.Plots.resize` on the charts it reveals.
- **Country picker:** one hidden card of numbers per country, same JavaScript
  pattern.
- **Historical time range:** removed; the timeline charts use Plotly `rangeselector`
  buttons (6m / 1y / 2y / 5y / All) on the full history.

### Assets and IPv6

- `plotly.min.js` and Leaflet are served from `static/` (version-pinned, copied in
  at build time from the Python packages or a pinned download), not from a
  third-party CDN.
- The only outside requests are OpenStreetMap tiles (IPv6-capable) and the existing
  logo on ipv6.army.

### Theme

CSS variables, defaulting to `prefers-color-scheme`, with the toggle saved in
`localStorage`. Charts use transparent backgrounds; the toggle calls
`Plotly.relayout` to change font and grid colors.

### Footer / disclaimer

Every page: "Data refreshed daily at 00:00 UTC · Last build: <UTC timestamp>".
The Data Sources page lists each source with its status, last success, last
attempt, and re-fetch interval, from the manifest.

## Static data policy

**Rule:** every statistic shown on the site comes from collected data, refreshed by
the pipeline. The only exception is reference material.

- **Statistics** (percentages, counts, rankings, growth figures, "as of now" claims)
  must come from a `datum`. Any hard-coded statistic found while converting a page is
  either connected to a collected source or removed. This applies to page code,
  collectors (e.g. `get_cloud_ipv6_status`), and `cloud_data.py`.
- **Reference material** (provider feature descriptions, policy and mandate text,
  explanations of methods) may be hand-maintained. It is wrapped in
  `{% call reference(reviewed="YYYY-MM-DD") %}`, displayed with a "Reference — last
  reviewed <date>" note, and must not contain statistics presented as current.

### Enforcement

- `datum` = `{value, source, fetched_at}`, created only by `web/build.py` from
  manifest-backed JSON or by `web/derive.py` from such data (a derived datum's
  `fetched_at` is the oldest of its inputs).
- `metric()` and chart helpers accept only datums. `build.py` stops if a datum is
  missing or its `source` is not in the manifest.
- A test scans `web/templates/`, `web/pages/`, and `collect/` for statistic-like
  literals in displayed strings (`\d+(\.\d+)?%` and numbers with thousands
  separators such as `228,789`) and fails on any outside `reference` blocks
  or an explicit allowlist (e.g. port numbers, years in dates).
- `build.py` prints a warning for any `reference` block reviewed more than 180 days
  ago (does not fail the build).

### Missing and stale data

- Never succeeded: shown as "— source unavailable".
- Last success older than 2× the re-fetch interval: values shown with a ⚠
  "stale since <date>" marker.

## Testing

- **Parser tests:** for each collector, a recorded real response in
  `tests/fixtures/<key>/` and a pytest checking the parsed output. Collectors take an
  injectable HTTP session so tests run offline. A format change at a source is
  handled by adding a new fixture and updating the parser.
- **Build test:** build the full site from fixture data into a temp directory;
  check that every page renders, every datum resolves, and all internal links work.
- **Static-data test:** as described under Enforcement.
- **Collector run test:** `run.py` with a stub that fails some sources; check that
  previous JSON is kept, the manifest is updated, and the 25% threshold triggers a
  non-zero exit.
- Tests run on every push and before collection on scheduled runs.

## Switch-over

1. Develop on `static-site`. Allow `static-site` in the `github-pages` environment's
   deployment branch rules; deploy a preview to `buraglio.github.io/ipv6stats` (no
   custom domain).
2. Add the `CLOUDFLARE_API_KEY` repository secret.
3. Run alongside the container for several days; compare numbers with
   stats.ipv6.army.
4. Merge `static-site` → `staging` → `main`. Point the deploy trigger at `main`,
   remove `static-site` from the environment rules.
5. Add the `CNAME` file (`stats.ipv6.army`) and set the custom domain in Pages
   settings. In DNS, replace the existing `stats` records with
   `stats.ipv6.army. CNAME buraglio.github.io.` (GitHub Pages answers on both IPv4
   and IPv6). Enable "Enforce HTTPS" once the certificate is issued. Lower the
   record's TTL a day ahead so rollback is quick.
6. Keep the container running for one week in case a rollback is needed (switch DNS
   back), then retire it.

## Risks

- **Size of the conversion:** `app.py` is large, and the static-data audit touches
  every page. Mitigation: convert and verify one page at a time; the plan orders
  pages so Overview ships first.
- **Sources blocking GitHub runner IPs or needing IPv6:** runners are IPv4-only and
  share IP ranges. Mitigation: per-source failures are kept separate and visible; if
  a source consistently fails from Actions, decide case by case (different
  endpoint, self-hosted runner, or drop the source).
- **Scraped sources changing format:** handled by parser tests plus last-good data.

## Amendment 1 — findings during planning (2026-10-14)

Reading the collectors closely showed that much of the dashboard's data is generated
in code, not fetched. This amendment records what was found and the decisions made.
Where it conflicts with earlier sections, this amendment wins.

### Findings

- **Generated datasets (no network request):** `get_global_historical_data`,
  `get_regional_trends`, `get_bgp_timeline`, `get_bgp_historical_data` (invented growth
  curves); `get_country_analysis`, `get_country_historical_data`,
  `get_regional_comparison` (hand-typed country tables and invented curves);
  `get_google_country_stats`; `get_prefix_size_distribution`;
  `get_top_asns_by_prefixes`.
- **`get_current_bgp_stats()` is partly made up:** `total_asns: 65000`,
  `monthly_growth: 2100`, and `estimated_growth_yearly: 26000` in every BGP code path.
- **"Facebook" statistics are Cloudflare Radar data.** Meta no longer publishes them.
  When the API call fails, the code falls back to hand-typed estimates.
- **Google's statistics page can't be read reliably** (drawn by JavaScript; its data
  file returns 404). The "Google" number has really been APNIC's.
- **ISOC Pulse has no public feed any more.** The JSON endpoint returns HTML; data
  now needs an account and API key. The live site's "IPv6 Websites 49%" has always
  been the hard-coded fallback.
- **LACNIC and AFRINIC** return hand-typed numbers on failure (marked `error`, not
  `fallback`).

### Real replacements confirmed

- **APNIC** (`stats.labs.apnic.net/ipv6/`): IPv6-capable %, IPv6-preferred % and
  sample count for the world, 6 regions, and 259 economies.
- **Potaroo** (`bgp.potaroo.net/v6/as2.0/bgp-active.txt`): hourly IPv6 BGP table size
  since 2003. Replaces the BGP prefix count, and gives real 30-day and yearly growth.
- **Tranco top 1000 + DNS AAAA lookups** (apex or `www.`), run by us: replaces "IPv6
  Websites".
- **Cloudflare Radar** `timeseries_groups/ip_version` (existing key): IPv6 share of
  HTTP traffic, with 52 weeks of history.

### Decisions

- **Splitting the work.** The migration is delivered as several plans:
  1. Foundation + merged Overview + workflow + preview deploy (Plan 1).
  2. One plan per group of pages (Global Adoption + Country Analysis; BGP Statistics;
     Historical Trends; Cloud Services + Extended Data Sources + Data Sources). Each
     starts with a list, approved by the owner, of which generated datasets get a real
     source and which are removed.
  3. Switch-over plan.
- **Collectors are ported one page group at a time.** The Streamlit app
  (`app.py`, `data_sources.py`) stays untouched until the switch-over plan, so
  production keeps running from `main` on the container.
- **BGP:** the decision "use `get_current_bgp_stats()` everywhere" is carried out
  as a single new BGP source, `bgp_v6_table` (Potaroo), used everywhere.
- **IPv6 websites:** measured from the Tranco top 1000 (`tranco_aaaa`). An
  **ISOC Pulse source is opt-in**: registered with `requires_env=ISOC_PULSE_API_KEY`;
  without the key it shows "not configured" and doesn't count as a failure. Its
  API client is written after the owner has a key (see Follow-ups).
- **Consensus** = average of whichever of APNIC world IPv6-capable, Cloudflare IPv6
  traffic share, and Tranco AAAA share have data.
- **APNIC per-economy rankings** count only economies with at least 100,000 samples,
  so tiny territories don't top the list.
- **"Facebook" labels are dropped.** Cloudflare data is labeled as Cloudflare.
  Cloudflare's `top/locations?ipVersion=IPv6` most likely returns each country's
  share of global IPv6 traffic, not adoption within the country. It is left out of
  Plan 1 until that's checked with a live key.
- **Overview headline row:** consensus; Cloudflare IPv6 traffic share; BGP IPv6
  prefixes (with yearly change); top-1000 sites with AAAA; economies at or above
  50% IPv6-capable.
- **Static Overview text with no data behind it is removed** (e.g. "Mobile traffic
  is 50% more likely…", "US Milestone…", the fixed Key Insights and Recent Updates
  lines). Those sections are generated from data.
- **Datum fields:** `{value, sources: tuple[str, ...], fetched_at, stale}`. A
  derived datum lists every input source.
- **Sources record a title and URL** in the registry, for the provenance shown on
  the site.

### Follow-ups (outside Plan 1)

- ISOC Pulse API client, once the owner has an account and key.
- Check what Cloudflare `top/locations` values mean; use or drop them.
