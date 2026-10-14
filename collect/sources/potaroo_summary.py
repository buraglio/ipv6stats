"""Summary statistics and prefix-length distribution from Potaroo's IPv6 BGP report."""
import re

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
}
COUNT = re.compile(r"bgp-prefix-(\d+)$")
SHARE = re.compile(r"bgp-p-prefix-(\d+)$")
MIN_LENGTHS = 10


def _number(text: str):
    value = float(text)
    return int(value) if value.is_integer() and "." not in text else value


def parse(page: str) -> dict:
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
    return {"stats": stats, "prefix_lengths": lengths, "url": URL}


@source("bgp_v6_summary", DAY, title="Potaroo IPv6 BGP report (summary)", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)
