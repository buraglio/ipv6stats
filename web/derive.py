"""Values computed at build time from collected data. Each returns a Datum or None."""
from __future__ import annotations

from datetime import date, timedelta

import pycountry

from web.data import Data, Datum, combine

MIN_SAMPLES = 100_000  # APNIC economies with fewer samples are left out of rankings
UNCLASSIFIED = "Unclassified"

CONSENSUS_INPUTS = (
    ("APNIC: users IPv6-capable", "apnic", lambda p: p["world"]["capable"]),
    ("Cloudflare: HTTP requests over IPv6", "cloudflare_ip_version", lambda p: p["latest_ipv6"]),
    ("Tranco top 1000: sites with AAAA", "tranco_aaaa", lambda p: p["percentage"]),
)


def consensus_components(data: Data) -> list[tuple[str, Datum | None]]:
    return [(label, data.datum(key, pick)) for label, key, pick in CONSENSUS_INPUTS]


def consensus(components: list[tuple[str, Datum | None]]) -> Datum | None:
    present = [d for _, d in components if d is not None]
    if not present:
        return None
    return combine(round(sum(d.value for d in present) / len(present), 1), present)


def bgp_current(data: Data) -> Datum | None:
    return data.datum("bgp_v6_table", lambda p: p["current"])


def bgp_change(data: Data, days: int) -> Datum | None:
    def pick(p):
        cutoff = date.fromisoformat(p["daily"][-1]["date"]) - timedelta(days=days)
        earlier = [d for d in p["daily"] if date.fromisoformat(d["date"]) <= cutoff]
        return p["current"] - earlier[-1]["prefixes"] if earlier else None

    return data.datum("bgp_v6_table", pick)


def _ranked(p: dict) -> list[dict]:
    return [e for e in p["economies"] if e["samples"] >= MIN_SAMPLES]


def economies_above(data: Data, threshold: float) -> Datum | None:
    return data.datum("apnic", lambda p: sum(1 for e in _ranked(p) if e["capable"] >= threshold))


def economies_considered(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: len(_ranked(p)))


def top_economy(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: max(_ranked(p), key=lambda e: e["capable"], default=None))


def economy(data: Data, code: str) -> Datum | None:
    return data.datum("apnic", lambda p: next((e for e in p["economies"] if e["code"] == code), None))


def regions(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: sorted(
        (r for r in p["regions"] if r["name"] != UNCLASSIFIED), key=lambda r: r["capable"], reverse=True))


RIR_SOURCES = (
    ("afrinic_delegations", "AFRINIC"),
    ("apnic_delegations", "APNIC"),
    ("arin_delegations", "ARIN"),
    ("lacnic_delegations", "LACNIC"),
    ("ripe_delegations", "RIPE NCC"),
)
VYNCKE_SERVICES = ("web", "email", "dns")


def iso3(code: str) -> str | None:
    country = pycountry.countries.get(alpha_2=code)
    return country.alpha_3 if country else None


def _present(*datums):
    return [d for d in datums if d is not None]


def economy_table(data: Data, limit: int | None = None) -> Datum | None:
    apnic = data.datum("apnic", _ranked)
    if apnic is None:
        return None
    sixlab = data.datum("cisco_6lab", lambda p: {c["code"]: c["ipv6_users_pct"] for c in p["countries"]})
    web = data.datum("vyncke", lambda p: {r["code"]: r["green_pct"] for r in p["web"]})
    rows = [{**e, "slug": e["code"].lower(),
             "sixlab": sixlab.value.get(e["code"]) if sixlab else None,
             "web": web.value.get(e["code"]) if web else None}
            for e in sorted(apnic.value, key=lambda e: e["capable"], reverse=True)[:limit]]
    return combine(rows, _present(apnic, sixlab, web))


def economy_index(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: sorted(
        ({"code": e["code"], "name": e["name"], "slug": e["code"].lower()} for e in p["economies"]),
        key=lambda e: e["name"]))


def map_points(data: Data) -> Datum | None:
    return data.datum("apnic", lambda p: [
        {"iso3": iso3(e["code"]), "code": e["code"], "name": e["name"], "capable": e["capable"]}
        for e in p["economies"] if iso3(e["code"])])


def rir_comparison(data: Data) -> Datum | None:
    rows, inputs = [], []
    for key, name in RIR_SOURCES:
        d = data.datum(key, lambda p: p)
        if d is None:
            continue
        inputs.append(d)
        rows.append({"name": name, "total": d.value["total_blocks_32"], "countries": d.value["countries"],
                     "file_date": d.value["file_date"], "history": d.value["history"]})
    return combine(rows, inputs) if inputs else None


def rir_total(data: Data) -> Datum | None:
    rirs = rir_comparison(data)
    return None if rirs is None else combine(sum(r["total"] for r in rirs.value), [rirs])


def country_allocation(data: Data, code: str) -> Datum | None:
    hits = [(name, d) for key, name in RIR_SOURCES
            if (d := data.datum(key, lambda p: p["by_country"].get(code))) is not None]
    if not hits:
        return None
    return combine({"blocks_32": sum(d.value for _, d in hits), "registries": [name for name, _ in hits]},
                   [d for _, d in hits])


def sixlab_for(data: Data, code: str) -> Datum | None:
    return data.datum("cisco_6lab", lambda p: next(
        (c["ipv6_users_pct"] for c in p["countries"] if c["code"] == code), None))


def _vyncke_row(p: dict, code: str) -> dict | None:
    values = {s: next((r["green_pct"] for r in p[s] if r["code"] == code), None) for s in VYNCKE_SERVICES}
    return values if any(v is not None for v in values.values()) else None


def vyncke_for(data: Data, code: str) -> Datum | None:
    return data.datum("vyncke", lambda p: _vyncke_row(p, code))


def website_table(data: Data, limit: int) -> Datum | None:
    def pick(p):
        names = {r["code"]: r["name"] for s in VYNCKE_SERVICES for r in p[s]}
        rows = [{"code": code, "name": names[code], **_vyncke_row(p, code)} for code in names]
        return sorted(rows, key=lambda r: (r["web"] is None, -(r["web"] or 0)))[:limit]

    return data.datum("vyncke", pick)


def nist(data: Data) -> Datum | None:
    return data.datum("nist_usgv6", lambda p: p)
