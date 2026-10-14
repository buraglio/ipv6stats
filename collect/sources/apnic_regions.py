"""APNIC Labs weekly IPv6 capability history for the world and its five regions."""
from collect.registry import MONTH, Context, source
from collect.sources import apnic
from collect.sources.apnic_detail import parse_economy

REGIONS = {"XA": "World", "XB": "Africa", "XC": "Americas", "XD": "Asia", "XE": "Europe", "XF": "Oceania"}


@source("apnic_region_history", MONTH, title="APNIC Labs regional IPv6 history", url=apnic.URL)
def fetch(ctx: Context) -> dict:
    regions = {}
    for code, name in REGIONS.items():  # all or nothing: a partial regional chart would mislead
        response = ctx.session.get(f"{apnic.URL}{code}", timeout=60)
        response.raise_for_status()
        regions[code] = {"name": name, "history": parse_economy(response.text)["history"]}
    return {"regions": regions, "url": apnic.URL}
