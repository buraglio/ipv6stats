"""IPv6 Matrix: share of crawled hosts reachable over IPv6, globally and by country."""
import re
from datetime import datetime

from collect.registry import MONTH, Context, source

URL = "https://ipv6matrix.com/json/hosts/group-country"
HOME = "https://ipv6matrix.com/"
COUNTRY = re.compile(r"^[A-Z]{2}$")
NOT_COUNTRIES = {"A1", "A2", "AP", "EU"}  # GeoIP pseudo-codes
TOP = 20


def _share(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def parse(body: dict) -> dict:
    if not isinstance(body, dict) or not body:
        raise ValueError("IPv6 Matrix format changed: expected crawls keyed by date")
    crawls = []
    for key, countries in body.items():
        try:
            day = datetime.strptime(key[:15], "%a %b %d %Y").date().isoformat()
            hosts = sum(int(c["hosts"]) for c in countries.values())
            hosts6 = sum(int(c["hosts6"]) for c in countries.values())
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"IPv6 Matrix format changed: {exc}") from exc
        crawls.append((day, hosts, hosts6, countries))
    crawls.sort()
    day, hosts, hosts6, countries = crawls[-1]
    table = sorted(({"code": code, "hosts": int(c["hosts"]), "hosts_ipv6": int(c["hosts6"]),
                     "share": _share(int(c["hosts6"]), int(c["hosts"]))}
                    for code, c in countries.items() if COUNTRY.match(code) and code not in NOT_COUNTRIES),
                   key=lambda c: c["hosts"], reverse=True)[:TOP]
    return {"latest": {"date": day, "hosts": hosts, "hosts_ipv6": hosts6, "share": _share(hosts6, hosts)},
            "series": [{"date": d, "share": _share(h6, h)} for d, h, h6, _ in crawls],
            "countries": table, "url": HOME}


@source("ipv6matrix_hosts", MONTH, title="IPv6 Matrix host crawl (API)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=120)
    response.raise_for_status()
    return parse(response.json())
