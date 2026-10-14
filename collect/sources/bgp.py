"""IPv6 BGP table size history from Geoff Huston's Potaroo reports."""
from datetime import datetime, timezone

from collect.registry import DAY, Context, source

URL = "https://bgp.potaroo.net/v6/as2.0/bgp-active.txt"  # "<unix time> <active entries>" hourly
PAGE = "https://bgp.potaroo.net/v6/as2.0/index.html"
MIN_DAYS = 365


def parse(text: str, min_days: int = MIN_DAYS) -> dict:
    latest_per_day: dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        ts, count = int(parts[0]), int(parts[1])
        day = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
        if day not in latest_per_day or ts > latest_per_day[day][0]:
            latest_per_day[day] = (ts, count)
    if len(latest_per_day) < min_days:
        raise ValueError(f"Potaroo file format changed: only {len(latest_per_day)} days parsed")
    daily = [{"date": day, "prefixes": count} for day, (_, count) in sorted(latest_per_day.items())]
    last_ts, last_count = latest_per_day[daily[-1]["date"]]
    return {"daily": daily, "current": last_count,
            "current_at": datetime.fromtimestamp(last_ts, timezone.utc).isoformat(timespec="seconds"),
            "url": PAGE}


@source("bgp_v6_table", DAY, title="Potaroo IPv6 BGP table report", url=PAGE)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)
