# IPv6 Statistics

A static site of global IPv6 adoption, routing and deployment data, rebuilt every day from
the sources it collects: https://stats.ipv6.army

Every measured number on the site comes from a collected source and shows where it came from
and how fresh it is. Nothing is estimated. Hand-maintained content (the reference lists and a few
"Reference" boxes, such as historical milestones and policy targets) shows when it was last reviewed.

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
