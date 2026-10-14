"""BGP Statistics: routing table size and growth, ASes, prefix lengths, aggregation, collectors."""
from dataclasses import replace

from web import charts, derive
from web.data import Data, field

SIXLAB_TOP = 10


def context(data: Data) -> dict:
    summary = data.datum("bgp_v6_summary", lambda p: p["stats"])
    lengths = data.datum("bgp_v6_summary", lambda p: [r for r in p["prefix_lengths"] if r["prefixes"]])
    ases = data.datum("bgp_v6_ases", lambda p: p["current"])
    return {
        "fib": derive.bgp_current(data),
        "fib_year": derive.bgp_change(data, 365),
        "ases": ases,
        "ases_year": derive.series_change(data, "bgp_v6_ases", "ases", 365),
        "origin_only": field(summary, "origin_only_ases"),
        "transit_only": field(summary, "transit_only_ases"),
        "avg_prefix": field(summary, "average_prefix_length"),
        "avg_path": field(summary, "average_as_path_length"),
        "rib": field(summary, "rib_entries"),
        # Potaroo expresses all advertised IPv6 space as the length of one equivalent prefix.
        "space": None if field(summary, "address_space_prefix") is None
        else replace(summary, value=f"/{summary.value['address_space_prefix']:.2f}"),
        "table_chart": charts.line_chart(data.datum("bgp_v6_table", lambda p: p["daily"]),
                                         x="date", y="prefixes", title="IPv6 BGP table size", y_title="Prefixes"),
        "ases_chart": charts.line_chart(data.datum("bgp_v6_ases", lambda p: p["daily"]),
                                        x="date", y="ases", title="ASes in the IPv6 routing table", y_title="ASes"),
        "lengths": lengths,
        "lengths_chart": charts.bar_chart(
            None if lengths is None else replace(lengths, value=[{"length": f"/{r['length']}", "prefixes": r["prefixes"]}
                                                                for r in lengths.value]),
            x="length", y="prefixes", title="IPv6 prefixes by prefix length", y_title="Prefixes"),
        "aggregation": data.datum("cidr_report_aggregation", lambda p: p),
        "routeviews": data.datum("routeviews_collectors", lambda p: p),
        "sixlab_top": SIXLAB_TOP,
        "sixlab": data.datum("cisco_6lab", lambda p: sorted(p["countries"], key=lambda c: c["ipv6_users_pct"],
                                                              reverse=True)[:SIXLAB_TOP]),
    }
