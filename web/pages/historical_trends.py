"""Historical Trends: real time series only, plus this site's own daily snapshots."""
from dataclasses import replace

from collect.sources.isoc import TOPSITES
from collect.sources.tranco import TOP_N
from web import charts, derive
from web.data import Data, Datum, combine
from web.pages.global_adoption import _rir_history

MIN_SNAPSHOT_DAYS = 2
SNAPSHOT_LABELS = {
    "apnic_world_capable": "Users able to use IPv6 (APNIC)",
    "cloudflare_ipv6": "HTTP requests over IPv6 (Cloudflare)",
    "tranco_aaaa": f"Top {TOP_N} sites with AAAA (Tranco)",
    "isoc_top_sites": f"Top {TOPSITES:,} sites with IPv6 (ISOC Pulse)",
}


def _series(name, points, x="date", y="capable"):
    return {"name": name, "points": [{"x": p[x], "y": p[y]} for p in points]}


def _world(data: Data):
    regions = data.datum("apnic_region_history", lambda p: p["regions"])
    isoc = data.datum("isoc_pulse", lambda p: p["users_ipv6"]["series"])
    parts = [d for d in (regions, isoc) if d is not None]
    if not parts:
        return None
    lines = []
    if regions:
        world = regions.value["XA"]["history"]
        lines += [_series("Able to use IPv6 (APNIC)", world), _series("Prefer IPv6 (APNIC)", world, y="preferred")]
    if isoc:
        lines.append(_series("Global IPv6 adoption (ISOC Pulse)", isoc.value, y="value"))
    return combine(lines, parts)


def _regions(data: Data):
    return data.datum("apnic_region_history", lambda p: [
        _series(r["name"], r["history"]) for code, r in sorted(p["regions"].items()) if code != "XA"])


def _snapshots(data: Data):
    days = data.history()
    if len(days) < MIN_SNAPSHOT_DAYS:
        return None, days
    lines = [{"name": label, "points": [{"x": d["date"], "y": d["values"][key]} for d in days if key in d["values"]]}
             for key, label in SNAPSHOT_LABELS.items()]
    lines = [line for line in lines if line["points"]]
    return Datum(lines, (), data.now, False), days


def context(data: Data) -> dict:
    snapshots, days = _snapshots(data)
    rirs = derive.rir_comparison(data)
    cf = data.datum("cloudflare_ip_version", lambda p: p["series"])
    world = _world(data)
    regions = _regions(data)
    return {
        "world": world,
        "world_chart": charts.multi_line_chart(world, title="IPv6 adoption worldwide", y_title="Percent"),
        "regions": regions,
        "regions_chart": charts.multi_line_chart(regions, title="Users able to use IPv6, by region", y_title="Percent"),
        "bgp": derive.bgp_current(data),
        "bgp_chart": charts.line_chart(data.datum("bgp_v6_table", lambda p: p["daily"]),
                                       x="date", y="prefixes", title="IPv6 BGP table size", y_title="Prefixes"),
        "ases": data.datum("bgp_v6_ases", lambda p: p["current"]),
        "ases_chart": charts.line_chart(data.datum("bgp_v6_ases", lambda p: p["daily"]),
                                        x="date", y="ases", title="ASes in the IPv6 routing table", y_title="ASes"),
        "rirs": rirs,
        "rir_chart": charts.multi_line_chart(_rir_history(rirs), title="IPv6 allocated over time (/32 equivalents)",
                                             y_title="/32 equivalents", x_type="linear"),
        "cloudflare": cf,
        "cloudflare_chart": charts.line_chart(cf, x="t", y="ipv6", title="HTTP requests over IPv6 (Cloudflare)",
                                              y_title="Percent"),
        "snapshots_chart": charts.multi_line_chart(snapshots, title="Recorded daily by this site", y_title="Percent"),
        "snapshot_days": len(days),
        "snapshot_start": days[0]["date"] if days else None,
    }
