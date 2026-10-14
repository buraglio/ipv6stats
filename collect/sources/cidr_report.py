"""CIDR Report (IPv6): ASes that could shrink the routing table most by aggregating."""
import logging
import re
import time
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
# Names are optional labels: a slow or failing RIPEstat must not stall the daily run.
MAX_NAME_FAILURES = 2
NAME_BUDGET_SECONDS = 60
NAME_TIMEOUT_SECONDS = 10
clock = time.monotonic  # replaced in tests


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


def _name(ctx: Context, asn: int) -> tuple[str | None, bool]:
    """(name, lookup_ok). A missing name is only a missing label."""
    try:
        response = ctx.session.get(f"{NAMES_URL}?resource=AS{asn}&sourceapp=ipv6stats",
                                   timeout=NAME_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()["data"].get("holder") or None, True
    except Exception as exc:
        logger.info("no RIPEstat name for AS%s: %s", asn, exc)
        return None, False


@source("cidr_report_aggregation", DAY, title="CIDR Report IPv6 aggregation summary", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    parsed = parse(response.text)
    started, failures = clock(), 0
    for row in parsed["ases"]:
        if failures >= MAX_NAME_FAILURES or clock() - started > NAME_BUDGET_SECONDS:
            logger.warning("skipping remaining AS name lookups after %s failures", failures)
            break
        row["name"], ok = _name(ctx, row["asn"])
        failures += not ok
    return parsed
