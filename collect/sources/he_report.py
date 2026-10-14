"""Hurricane Electric's global IPv6 deployment progress report: TLD nameservers and AAAA domains."""
import re
from datetime import datetime, timedelta

from collect.registry import MONTH, Context, source

URL = "https://bgp.he.net/ipv6-progress-report.cgi"
DATE = r"(\w{3} \w{3} +\d{1,2} [\d:]+ \d{4})"
STATS = {
    "tlds": re.compile(r"Top Level Domains \(TLDs\): (\d+)"),
    "tlds_ipv6_ns": re.compile(r"TLDs with IPv6 nameservers: (\d+)"),
    "tlds_ipv6_glue": re.compile(r"TLDs with nameservers with IPv6 glue in the root zone: (\d+)"),
}
PROCESSED = re.compile(r"Root Zone Processed: " + DATE)
# <pre> table: TLD domains A AAAA A-glue AAAA-glue (downloaded) (processed)
ROW = re.compile(r"^\s*([a-z0-9-]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+\(" + DATE + r"\)", re.M)
TOTAL = re.compile(r"^\s*total\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.M)
MIN_ROWS = 100
TOP = 20
MAX_AGE = timedelta(days=3)


def _date(text: str) -> str:
    return datetime.strptime(" ".join(text.split()), "%a %b %d %H:%M:%S %Y").date().isoformat()


def parse(page: str, now: datetime | None = None, min_rows: int = MIN_ROWS) -> dict:
    stats = {k: int(m.group(1)) for k, rx in STATS.items() if (m := rx.search(page))}
    processed, total = PROCESSED.search(page), TOTAL.search(page)
    rows = [{"tld": t, "domains": int(d), "aaaa": int(aaaa), "downloaded": _date(dl)}
            for t, d, _a, aaaa, _ag, _aaaag, dl in ROW.findall(page)]
    if len(stats) < len(STATS) or not processed or not total or len(rows) < min_rows:
        raise ValueError(f"HE report format changed: stats={sorted(stats)}, rows={len(rows)}")
    processed_date = _date(processed.group(1))
    if now is not None and now.date() - datetime.fromisoformat(processed_date).date() > MAX_AGE:
        raise ValueError(f"HE report stopped updating: root zone processed {processed_date}")
    domains = dict(zip(("domains", "a", "aaaa", "a_glue", "aaaa_glue"), map(int, total.groups())))
    rows.sort(key=lambda r: r["domains"], reverse=True)
    return {**stats, "root_zone_processed": processed_date, "domains": domains, "top_tlds": rows[:TOP], "url": URL}


@source("he_progress", MONTH, title="Hurricane Electric IPv6 progress report", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text, now=ctx.now)
