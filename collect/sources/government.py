"""Whether government websites publish IPv6 (AAAA on the domain or its www. name).

The list lives in reference/government_domains.toml. Measured from GitHub's runners (no IPv6),
so this shows published IPv6, not end-to-end reachability.
"""
import tomllib
from pathlib import Path

from collect.registry import MONTH, Context, source
from collect.sources.cloud_endpoints import check

LIST_FILE = Path(__file__).resolve().parents[2] / "reference" / "government_domains.toml"
METHOD = "https://github.com/buraglio/ipv6stats/blob/main/collect/sources/government.py"
MAX_UNKNOWN = 0.1


def load_list(path: Path = LIST_FILE) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _status(domain: str, has_aaaa, has_a) -> str:
    apex = check(domain, has_aaaa, has_a)
    if apex == "ipv6":
        return apex
    www = check(f"www.{domain}", has_aaaa, has_a)
    if www == "ipv6":
        return www
    return "ipv4_only" if "ipv4_only" in (apex, www) else "unknown"


def measure(listing: dict, has_aaaa, has_a) -> dict:
    groups, unknown, total = [], 0, 0
    for group in listing["group"]:
        domains = [{"domain": d, "status": _status(d, has_aaaa, has_a)} for d in group["domains"]]
        unknown += sum(d["status"] == "unknown" for d in domains)
        total += len(domains)
        groups.append({"name": group["name"], "domains": domains,
                       "with_ipv6": sum(d["status"] == "ipv6" for d in domains),
                       "checked": sum(d["status"] != "unknown" for d in domains)})
    if unknown > MAX_UNKNOWN * total:
        raise ValueError(f"{unknown} of {total} government domain lookups failed; not trusting the result")
    return {"groups": groups, "unknown": unknown, "total": total, "url": METHOD}


@source("government_domains", MONTH, title="Government websites with IPv6 (AAAA lookups, measured)", url=METHOD)
def fetch(ctx: Context) -> dict:
    return measure(load_list(), ctx.has_aaaa, ctx.has_a)
