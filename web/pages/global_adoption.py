"""Global Adoption: who has IPv6, by economy, region and registry."""
from dataclasses import replace

from web import charts, derive
from web.data import Data, field
from web.pages.overview import ABOVE_THRESHOLD

TOP_TABLE = 20


def _rir_history(rirs):
    if rirs is None:
        return None
    return replace(rirs, value=[{"name": r["name"], "points": [{"x": h["year"], "y": h["blocks_32"]}
                                                              for h in r["history"]]} for r in rirs.value])


def context(data: Data) -> dict:
    components = derive.consensus_components(data)
    present = sum(1 for _, d in components if d is not None)
    top = derive.top_economy(data)
    regions = derive.regions(data)
    rirs = derive.rir_comparison(data)
    return {
        "consensus": derive.consensus(components),
        "consensus_note": f"{present} of {len(components)} sources",
        "above_threshold": ABOVE_THRESHOLD,
        "above": derive.economies_above(data, ABOVE_THRESHOLD),
        "considered": derive.economies_considered(data),
        "min_samples_label": f"{derive.MIN_SAMPLES:,}",
        "top_economy": top,
        "top_capable": field(top, "capable"),
        "rir_total": derive.rir_total(data),
        "rir_count_note": f"{len(rirs.value) if rirs else 0} of {len(derive.RIR_SOURCES)} registries",
        "regions": regions,
        "regions_chart": charts.bar_chart(regions, x="name", y="capable",
                                          title="Users able to use IPv6, by region", y_title="Percent"),
        "top_table_size": TOP_TABLE,
        "top_table": derive.economy_table(data, TOP_TABLE),
        "rirs": rirs,
        "rir_chart": charts.multi_line_chart(_rir_history(rirs), title="IPv6 allocated over time (/32 equivalents)",
                                             y_title="/32 equivalents", x_type="linear"),
        "websites": derive.website_table(data, TOP_TABLE),
        "cf_ipv6": data.datum("cloudflare_ip_version", lambda p: p["latest_ipv6"]),
        "sites": data.datum("tranco_aaaa", lambda p: p["percentage"]),
    }
