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

from web import reference
from web.data import Data
from web.format import date_only, format_value, provenance_text
from web.pages import bgp_statistics, cloud_services, country, country_analysis, data_sources, extended_data_sources, global_adoption, historical_trends, overview

HERE = Path(__file__).parent
TEMPLATES = HERE / "templates"
STATIC = HERE / "static"
REFERENCE = re.compile(r'reference\(\s*reviewed\s*=\s*"(\d{4}-\d{2}-\d{2})"')


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    context: Callable[[Data], dict]


PAGES = (
    Page("overview", "Overview", overview.context),
    Page("global-adoption", "Global Adoption", global_adoption.context),
    Page("country-analysis", "Country Analysis", country_analysis.context),
    Page("cloud-services", "Cloud Services", cloud_services.context),
    Page("bgp-statistics", "BGP Statistics", bgp_statistics.context),
    Page("historical-trends", "Historical Trends", historical_trends.context),
    Page("extended-data-sources", "Extended Data Sources", extended_data_sources.context),
    Page("data-sources", "Data Sources", data_sources.context),
)

# Old Streamlit ?page= names -> new paths; unknown names land on the Overview.
LEGACY_PAGES = {
    "Overview": "overview/",
    "Combined View": "overview/",
    "Global Adoption": "global-adoption/",
    "Country Analysis": "country-analysis/",
    "Cloud Services": "cloud-services/",
    "BGP Statistics": "bgp-statistics/",
    "Historical Trends": "historical-trends/",
    "Extended Data Sources": "extended-data-sources/",
    "Data Sources": "data-sources/",
}


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
    country_template = env.get_template("country.html")
    for slug, page_context in country.pages(data):
        context = {**common, "current": "country-analysis", **page_context}
        _write(out_dir / "country" / slug / "index.html", country_template.render(context, base="../../"))
    return (check_reference_dates(TEMPLATES, now) + reference.stale_reviews(reference.load_cloud_providers(), now)
            + reference.list_reviews(now))


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
