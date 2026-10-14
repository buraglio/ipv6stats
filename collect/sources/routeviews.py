"""RouteViews: active collectors and each one's latest IPv6 table size and peer count."""
from collect.registry import DAY, Context, source

BASE = "https://api.routeviews.org"
HOME = "https://www.routeviews.org/"
MIN_COLLECTORS = 10


def _get(ctx: Context, path: str) -> dict:
    response = ctx.session.get(f"{BASE}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def collect(ctx: Context, min_collectors: int = MIN_COLLECTORS) -> dict:
    listing = _get(ctx, "/collector/")
    if "results" not in listing:
        raise ValueError(f"RouteViews API format changed: collector keys {sorted(listing)}")
    active = {c["name"]: c for c in listing["results"] if not c.get("removed")}
    first = _get(ctx, "/timeseries/")
    size = len(first.get("results", []))
    if not size or "count" not in first:
        raise ValueError("RouteViews API format changed: empty timeseries")
    last_page = (first["count"] + size - 1) // size
    entries = []
    for page in range(max(1, last_page - 1), last_page + 1):  # a collector's latest may be one page back
        entries += _get(ctx, f"/timeseries/?page={page}")["results"]
    latest: dict[str, dict] = {}
    for e in entries:
        name = e["collector"]
        if name in active and (name not in latest or e["date"] > latest[name]["date"]):
            latest[name] = e
    collectors = sorted(({"name": n, "country": active[n].get("country"), "rir_region": active[n].get("rir_region"),
                          "date": e["date"][:10], "ipv6_prefixes": e["ipv6_prefix_count"],
                          "ipv6_peers": e["ipv6_peer_count"], "ipv4_prefixes": e["ipv4_prefix_count"]}
                         for n, e in latest.items()), key=lambda c: c["ipv6_prefixes"], reverse=True)
    if len(collectors) < min_collectors:
        raise ValueError(f"RouteViews API format changed: only {len(collectors)} collectors with snapshots")
    return {"collectors": collectors, "active": len(active),
            "snapshot_date": max(c["date"] for c in collectors), "url": HOME}


@source("routeviews_collectors", DAY, title="RouteViews collectors (API)", url=HOME)
def fetch(ctx: Context) -> dict:
    return collect(ctx)
