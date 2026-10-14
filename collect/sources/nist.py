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
