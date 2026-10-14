"""Extended Data Sources: DNS, routing security, measurement networks, interconnection,
access networks, government websites and the five registries."""
from dataclasses import replace
from datetime import date

from web import charts, derive, reference
from web.data import Data

OLD_ZONE_DAYS = 365
RIR_TOP = 10


def _carriers(data: Data):
    listing = reference.load_carriers()
    # Key by (economy, ASN): multinational ASNs appear in several economies' tables.
    detail = data.datum("apnic_economy_detail", lambda p: {
        (code, n["asn"]): n for code, e in p["economies"].items() for n in e["networks"]})
    rows = [{**c, "apnic": detail.value.get((c["country"], c["asn"])) if detail else None}
            for c in listing["carrier"]]
    return rows, detail, listing["last_reviewed"]


def context(data: Data) -> dict:
    he = data.datum("he_progress", lambda p: p)
    today = data.now.date()
    tlds = None if he is None else [
        {**t, "old": (today - date.fromisoformat(t["downloaded"])).days > OLD_ZONE_DAYS} for t in he.value["top_tlds"]]
    routing = data.datum("isoc_routing", lambda p: p)
    matrix = data.datum("ipv6matrix_hosts", lambda p: p)
    carriers, carrier_detail, carriers_reviewed = _carriers(data)
    return {
        "he": he, "tlds": tlds,
        "routing": routing,
        "routing_status": data.manifest.get("isoc_routing", {}).get("status"),
        "roa_chart": charts.multi_line_chart(
            None if routing is None else replace(routing, value=[
                {"name": "IPv6 address space covered by ROAs", "points": [{"x": p["date"], "y": p["value"]} for p in routing.value["roa_ipv6"]["series"]]},
                {"name": "IPv4 address space covered by ROAs", "points": [{"x": p["date"], "y": p["value"]} for p in routing.value["roa_ipv4"]["series"]]}]),
            title="RPKI ROA coverage", y_title="Percent"),
        "bogons": data.datum("cymru_bogons", lambda p: p),
        "atlas": data.datum("ripe_atlas_probes", lambda p: p),
        "matrix": matrix,
        "matrix_chart": charts.line_chart(None if matrix is None else replace(matrix, value=matrix.value["series"]),
                                          x="date", y="share", title="Crawled hosts with IPv6 (IPv6 Matrix)",
                                          y_title="Percent"),
        "peeringdb": data.datum("peeringdb_networks", lambda p: p),
        "carriers": carriers, "carrier_detail": carrier_detail, "carriers_reviewed": carriers_reviewed,
        "government": data.datum("government_domains", lambda p: p),
        "government_reviewed": reference.load_government()["last_reviewed"],
        "rirs": derive.rir_comparison(data),
        "rir_details": [(name, data.datum(key, lambda p: p)) for key, name in derive.RIR_SOURCES],
        "rir_top": RIR_TOP,
    }
