"""APNIC Labs IPv6 capability measurement for the world, regions and economies."""
import html
import re

from collect.registry import MONTH, Context, source

URL = "https://stats.labs.apnic.net/ipv6/"
# Rows in the page's embedded chart data look like:
#   ["<a href=\"/ipv6/US\">US</a>","<a href=\"/ipv6/US\">United States of America</a>, <a ...>Americas</a>",
#    {v: 61.90, f:'61.90%'}, {v: 59.85, f: '59.85%'},97679957]
# Fields: code, name (+ parent regions for economies), IPv6-capable, IPv6-preferred, samples.
ROW = re.compile(
    r'\["<a href=\\"/ipv6/([A-Z]{2})\\">[^"]*</a>","(.*?)",'
    r"\{v:\s*([\d.]+)[^}]*\},\s*\{v:\s*([\d.]+)[^}]*\},(\d+)\]"
)
LINK_TEXT = re.compile(r">([^<]+)</a>")
WORLD = "XA"
MIN_ECONOMIES = 100  # fewer means the page layout changed


def parse(page: str, min_economies: int = MIN_ECONOMIES) -> dict:
    world, regions, economies, seen = None, [], [], set()
    for match in ROW.finditer(page):
        code, names, capable, preferred, samples = match.groups()
        if code in seen:  # the page repeats rows in several tables; keep the first
            continue
        seen.add(code)
        links = LINK_TEXT.findall(names)
        row = {"code": code, "name": html.unescape(links[0]) if links else code,
               "capable": float(capable), "preferred": float(preferred), "samples": int(samples)}
        if code == WORLD:
            world = row
        elif len(links) == 1:  # regions list only themselves; economies also list parents
            regions.append(row)
        else:
            economies.append(row)
    if world is None or len(economies) < min_economies:
        raise ValueError(f"APNIC page format changed: world={'found' if world else 'missing'}, "
                         f"economies={len(economies)}")
    return {"world": world, "regions": regions,
            "economies": sorted(economies, key=lambda r: r["code"]), "url": URL}


@source("apnic", MONTH, title="APNIC Labs IPv6 measurement", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=30)
    response.raise_for_status()
    return parse(response.text)
