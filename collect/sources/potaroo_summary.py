"""Summary statistics and prefix-length distribution from Potaroo's IPv6 BGP report."""
import re
from datetime import datetime, timedelta

from collect.registry import DAY, Context, source

URL = "https://bgp.potaroo.net/v6/as2.0/index.html"
# Each statistic links to its own data file: ...>Label</a></td><td><b><a href="bgp-as-count.txt" target="text">37751</a>
STAT = re.compile(r'</a></td><td><b><a href="([a-z0-9.-]+)\.txt" target="text">([^<]+)</a>')
WANTED = {  # data-file stem -> name; the stems are stable, the labels are prose
    "bgp-active": "fib_entries",
    "bgp-all": "rib_entries",
    "bgp-as-count": "unique_ases",
    "bgp-as-term": "origin_only_ases",
    "bgp-transit": "transit_only_ases",
    "bgp-average-prefix": "average_prefix_length",
    "bgp-average-aspath-length": "average_as_path_length",
    "bgp-total-space-prefix": "address_space_prefix",  # all advertised space, as one prefix length
}
COUNT = re.compile(r"bgp-prefix-(\d+)$")
SHARE = re.compile(r"bgp-p-prefix-(\d+)$")
MIN_LENGTHS = 10
# "Report last updated at Wed Oct 14 19:45:06 2026 (Australian Eastern Time)"
REPORT_DATE = re.compile(r"Report last updated at \w{3} (\w{3}) +(\d{1,2}) [\d:]+ (\d{4})")
MAX_AGE = timedelta(days=3)


def _number(text: str):
    value = float(text)
    return int(value) if value.is_integer() and "." not in text else value


def parse(page: str, now: datetime | None = None) -> dict:
    dated = REPORT_DATE.search(page)
    if dated is None:
        raise ValueError("Potaroo report format changed: no 'Report last updated' date")
    report_date = datetime.strptime(" ".join(dated.groups()), "%b %d %Y").date()
    if now is not None and now.date() - report_date > MAX_AGE:  # date in AEST: day-level is enough
        raise ValueError(f"Potaroo report stopped updating: last updated {report_date}")
    stats, counts, shares = {}, {}, {}
    for stem, raw in STAT.findall(page):
        try:
            value = _number(raw.strip())
        except ValueError:  # "(data)" links to whole vectors
            continue
        if stem in WANTED:
            stats[WANTED[stem]] = value
        elif m := COUNT.match(stem):
            counts[int(m.group(1))] = int(value)
        elif m := SHARE.match(stem):
            shares[int(m.group(1))] = float(value)
    missing = sorted(set(WANTED.values()) - set(stats))
    if missing or len(counts) < MIN_LENGTHS:
        raise ValueError(f"Potaroo report format changed: missing {missing}, {len(counts)} prefix lengths")
    lengths = [{"length": n, "prefixes": counts[n], "share": shares.get(n)} for n in sorted(counts)]
    return {"stats": stats, "prefix_lengths": lengths, "report_date": report_date.isoformat(), "url": URL}


@source("bgp_v6_summary", DAY, title="Potaroo IPv6 BGP report (summary)", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text, now=ctx.now)
