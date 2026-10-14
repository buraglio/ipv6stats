"""Values computed at build time from collected data. Each returns a Datum or None."""
from __future__ import annotations

from datetime import date, timedelta

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
