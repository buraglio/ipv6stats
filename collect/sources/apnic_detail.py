"""APNIC per-economy pages: weekly IPv6 capability history and the per-network (AS) table."""
import html
import logging
import re
import time
from datetime import date

from collect.registry import MONTH, Context, source
from collect.sources import apnic

logger = logging.getLogger(__name__)

TOP_ECONOMIES = 50
TOP_NETWORKS = 20
MAX_MISSING = 5
DEADLINE_SECONDS = 600  # stop well inside the workflow's 30-minute limit
clock = time.monotonic  # replaced in tests
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
    started = clock()
    economies, missing = {}, []
    for economy in ranked[:TOP_ECONOMIES]:
        code = economy["code"]
        if clock() - started > DEADLINE_SECONDS:  # out of time: count the rest as missing
            missing.append(code)
        else:
            try:
                page = ctx.session.get(f"{apnic.URL}{code}", timeout=60)
                page.raise_for_status()
                economies[code] = parse_economy(page.text)
            except Exception as exc:  # one bad page must not discard the others
                logger.warning("APNIC page for %s failed: %s", code, exc)
                missing.append(code)
        if len(missing) > MAX_MISSING:  # the result will be discarded; stop fetching
            raise ValueError(f"{len(missing)} APNIC economy pages failed: {', '.join(missing)}")
    return {"economies": economies, "missing": missing}
