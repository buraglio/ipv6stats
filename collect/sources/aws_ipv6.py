"""AWS's own table of which services support IPv6 (dual-stack, IPv6-only, endpoints)."""
import html
import re

from collect.registry import MONTH, Context, source

URL = "https://docs.aws.amazon.com/vpc/latest/userguide/aws-ipv6-support.html"
COLUMNS = ("dual_stack", "ipv6_only", "public_endpoints", "private_endpoints")
VALUES = {"yes": "yes", "no": "no", "partial": "partial", "": None}
ROW = re.compile(r"<tr>\s*((?:<td[^>]*>.*?</td>\s*){5})</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
MIN_SERVICES = 100


def _text(cell: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", cell))).strip()


def parse(page: str, min_services: int = MIN_SERVICES) -> dict:
    services = []
    for row in ROW.findall(page):
        name, *flags = (_text(c) for c in CELL.findall(row))
        values = []
        for flag in flags:
            if flag.lower() not in VALUES:
                raise ValueError(f"AWS IPv6 table format changed: unexpected value {flag!r} for {name}")
            values.append(VALUES[flag.lower()])
        services.append({"name": name, **dict(zip(COLUMNS, values))})
    if len(services) < min_services:
        raise ValueError(f"AWS IPv6 table format changed: {len(services)} services")
    counts = {c: {v: sum(1 for s in services if s[c] == v) for v in ("yes", "partial", "no")} for c in COLUMNS}
    return {"services": services, "counts": counts, "total": len(services), "url": URL}


@source("aws_ipv6_services", MONTH, title="AWS services that support IPv6 (AWS documentation)", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)
