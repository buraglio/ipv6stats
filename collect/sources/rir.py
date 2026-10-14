"""IPv6 allocations from the LACNIC and AFRINIC delegation files, in /32 equivalents."""
from collect.registry import MONTH, Context, source

LACNIC_URL = "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest"
AFRINIC_URL = "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest"
UNIT = 32
COUNTED = {"allocated", "assigned"}
TOP_N = 10


def parse_delegations(text: str, registry: str, url: str) -> dict:
    # Header: version|registry|serial(YYYYMMDD)|records|startdate|enddate|UTCoffset
    # Records: registry|cc|type|start|value|date|status
    file_date, per_country, total = None, {}, 0.0
    for line in text.splitlines():
        parts = line.strip().split("|")
        if file_date is None and len(parts) >= 3 and parts[1] == registry and parts[0][:1].isdigit():
            serial = parts[2]
            file_date = f"{serial[:4]}-{serial[4:6]}-{serial[6:8]}"
            continue
        if (len(parts) < 7 or parts[0] != registry or parts[2] != "ipv6"
                or parts[1] == "*" or parts[6] not in COUNTED):
            continue
        blocks = 2 ** (UNIT - int(parts[4]))  # int base; a negative power gives a float
        per_country[parts[1]] = per_country.get(parts[1], 0.0) + blocks
        total += blocks
    if file_date is None or not per_country:
        raise ValueError(f"{registry} delegation file format changed")
    top = sorted(per_country.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    return {
        "file_date": file_date,
        "total_blocks_32": round(total, 2),
        "countries": len(per_country),
        "top_countries": [{"code": cc, "blocks_32": round(b, 2), "share": round(100 * b / total, 2)}
                          for cc, b in top],
        "url": url,
    }


def _fetch(ctx: Context, registry: str, url: str) -> dict:
    response = ctx.session.get(url, timeout=60)
    response.raise_for_status()
    return parse_delegations(response.text, registry, url)


@source("lacnic_delegations", MONTH, title="LACNIC delegation file", url=LACNIC_URL)
def fetch_lacnic(ctx: Context) -> dict:
    return _fetch(ctx, "lacnic", LACNIC_URL)


@source("afrinic_delegations", MONTH, title="AFRINIC delegation file", url=AFRINIC_URL)
def fetch_afrinic(ctx: Context) -> dict:
    return _fetch(ctx, "afrinic", AFRINIC_URL)
