"""Overview page: the old Overview and Combined View merged, built only from collected data."""
from web import charts, derive
from web.data import Data

ABOVE_THRESHOLD = 50


def context(data: Data) -> dict:
    components = derive.consensus_components(data)
    present = sum(1 for _, d in components if d is not None)
    return {
        "consensus": derive.consensus(components),
        "consensus_note": f"{present} of {len(components)} sources",
        "components": components,
        "cf_ipv6": data.datum("cloudflare_ip_version", lambda p: p["latest_ipv6"]),
        "cf_ipv4": data.datum("cloudflare_ip_version", lambda p: p["latest_ipv4"]),
        "cf_chart": charts.line_chart(
            data.datum("cloudflare_ip_version", lambda p: p["series"]),
            x="t", y="ipv6", title="Cloudflare HTTP requests over IPv6", y_title="Percent"),
        "bgp_current": derive.bgp_current(data),
        "bgp_year": derive.bgp_change(data, 365),
        "bgp_month": derive.bgp_change(data, 30),
        "bgp_chart": charts.line_chart(
            data.datum("bgp_v6_table", lambda p: p["daily"]),
            x="date", y="prefixes", title="IPv6 BGP table size", y_title="Prefixes"),
        "sites": data.datum("tranco_aaaa", lambda p: p["percentage"]),
        "tranco": data.datum("tranco_aaaa", lambda p: p),
        "apnic_world": data.datum("apnic", lambda p: p["world"]),
        "apnic_capable": data.datum("apnic", lambda p: p["world"]["capable"]),
        "above_threshold": ABOVE_THRESHOLD,
        "above": derive.economies_above(data, ABOVE_THRESHOLD),
        "considered": derive.economies_considered(data),
        "min_samples_label": f"{derive.MIN_SAMPLES:,}",
        "top_economy": derive.top_economy(data),
        "us": derive.economy(data, "US"),
        "regions": derive.regions(data),
        "lacnic": data.datum("lacnic_delegations", lambda p: p),
        "afrinic": data.datum("afrinic_delegations", lambda p: p),
    }
