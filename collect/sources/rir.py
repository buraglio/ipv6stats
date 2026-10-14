"""IPv6 allocations from the five RIR delegation files, in /32 equivalents."""
from collect.registry import MONTH, Context, source

URLS = {
    "afrinic": "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest",
    "apnic": "https://ftp.apnic.net/stats/apnic/delegated-apnic-latest",
    "arin": "https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest",
    "lacnic": "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
    "ripencc": "https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest",
}
LACNIC_URL = URLS["lacnic"]
AFRINIC_URL = URLS["afrinic"]
REGISTRIES = (  # (source key, registry name used inside the file, title)
    ("afrinic_delegations", "afrinic", "AFRINIC delegation file"),
    ("apnic_delegations", "apnic", "APNIC delegation file"),
    ("arin_delegations", "arin", "ARIN delegation file (extended)"),
    ("lacnic_delegations", "lacnic", "LACNIC delegation file"),
    ("ripe_delegations", "ripencc", "RIPE NCC delegation file"),
)
UNIT = 32
COUNTED = {"allocated", "assigned"}
TOP_N = 10
NO_DATE = "00000000"


def _is_yyyymmdd(text: str) -> bool:
    return len(text) == len("YYYYMMDD") and text.isdigit()


def parse_delegations(text: str, registry: str, url: str) -> dict:
    # Header: version|registry|serial|records|startdate|enddate|UTCoffset. The serial is
    # YYYYMMDD at some RIRs and a Unix timestamp at others; enddate is YYYYMMDD everywhere.
    # Records: registry|cc|type|start|value|date|status[|opaque-id]
    file_date, per_country, per_year, total = None, {}, {}, 0.0
    for line in text.splitlines():
        parts = line.strip().split("|")
        if file_date is None and len(parts) >= 6 and parts[1] == registry and parts[0][:1].isdigit():
            end = parts[5]
            if not _is_yyyymmdd(end):
                raise ValueError(f"{registry} delegation file format changed: header end date {end!r}")
            file_date = f"{end[:4]}-{end[4:6]}-{end[6:]}"
            continue
        if (len(parts) < 7 or parts[0] != registry or parts[2] != "ipv6"
                or parts[1] in ("*", "") or parts[6] not in COUNTED):
            continue
        blocks = 2 ** (UNIT - int(parts[4]))  # int base; a negative power gives a float
        per_country[parts[1]] = per_country.get(parts[1], 0) + blocks
        total += blocks
        if _is_yyyymmdd(parts[5]) and parts[5] != NO_DATE:
            year = int(parts[5][:4])
            per_year[year] = per_year.get(year, 0) + blocks
    if file_date is None or not per_country:
        raise ValueError(f"{registry} delegation file format changed")
    top = sorted(per_country.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    history, running = [], 0.0
    for year in sorted(per_year):
        running += per_year[year]
        history.append({"year": year, "blocks_32": round(running, 2)})
    return {
        "file_date": file_date,
        "total_blocks_32": round(total, 2),
        "countries": len(per_country),
        "top_countries": [{"code": cc, "blocks_32": round(b, 2), "share": round(100 * b / total, 2)}
                          for cc, b in top],
        "by_country": {cc: round(b, 2) for cc, b in sorted(per_country.items())},
        "history": history,
        "url": url,
    }


def _fetch(ctx: Context, registry: str, url: str) -> dict:
    response = ctx.session.get(url, timeout=120)
    response.raise_for_status()
    return parse_delegations(response.text, registry, url)


def _register(key: str, registry: str, title: str) -> None:
    url = URLS[registry]

    def fetch(ctx: Context) -> dict:
        return _fetch(ctx, registry, url)

    source(key, MONTH, title=title, url=url)(fetch)


for _key, _registry, _title in REGISTRIES:
    _register(_key, _registry, _title)
