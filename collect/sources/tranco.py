"""Share of the Tranco top sites that publish AAAA records (apex or www), measured by us."""
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from collect.registry import MONTH, Context, source

LIST_URL = "https://tranco-list.eu/top-1m.csv.zip"
HOME = "https://tranco-list.eu/"
TOP_N = 1000
SHOW_N = 100
WORKERS = 32
MAX_UNRESOLVED = 0.02  # above this share of failed lookups, the measurement is not trusted


def top_domains(zip_bytes: bytes, n: int) -> list[str]:
    domains: list[str] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                _, _, domain = line.strip().partition(",")
                if domain:
                    domains.append(domain)
                if len(domains) == n:
                    break
    return domains


def has_ipv6(domain: str, has_aaaa: Callable[[str], bool | None]) -> bool | None:
    """True/False, or None when the lookups failed and the answer is unknown."""
    apex = has_aaaa(domain)
    if apex or domain.startswith("www."):
        return apex
    www = has_aaaa(f"www.{domain}")
    if www:
        return True
    return None if apex is None or www is None else False


def measure(domains: list[str], has_aaaa: Callable[[str], bool | None]) -> dict:
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        flags = list(pool.map(lambda d: has_ipv6(d, has_aaaa), domains))
    unresolved = sum(1 for f in flags if f is None)
    if unresolved > MAX_UNRESOLVED * len(domains):
        raise ValueError(f"{unresolved} of {len(domains)} DNS lookups failed; not trusting the result")
    with_aaaa = sum(1 for f in flags if f is True)
    if with_aaaa == 0:
        raise ValueError("no domain has an AAAA record; DNS resolution is probably broken")
    return {
        "checked": len(domains),
        "unresolved": unresolved,
        "with_aaaa": with_aaaa,
        "percentage": round(100 * with_aaaa / (len(domains) - unresolved), 1),
        "top": [{"rank": i + 1, "domain": d, "aaaa": f}
                for i, (d, f) in enumerate(zip(domains[:SHOW_N], flags))],
        "list_url": HOME,
    }


@source("tranco_aaaa", MONTH, title="Tranco top sites, AAAA lookups (measured)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(LIST_URL, timeout=120)
    response.raise_for_status()
    domains = top_domains(response.content, TOP_N)
    if len(domains) < TOP_N:
        raise ValueError(f"Tranco list has only {len(domains)} domains")
    return measure(domains, ctx.has_aaaa)
