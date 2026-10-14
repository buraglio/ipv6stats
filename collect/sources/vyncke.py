"""Per-country IPv6 support among top websites, from Eric Vyncke's IPv6 deployment status."""
import html
import re

from collect.registry import MONTH, Context, source

URL = "https://www.vyncke.org/ipv6status/"
SERVICES = ("web", "email", "dns")
TITLES = {"web": "Web", "email": "Email", "dns": "DNS"}
# Rows (HTML rows are not closed):
# <tr><td>1<td><a href=detailed.php?country=no><img ...> Norway</a>
#     <td align=right>50 <td align=right>55.54% <td align=right>68.0% (34) <td align=right>0.0% (0)
ROW = re.compile(
    r"<tr><td>\d+<td><a href=detailed\.php\?country=([a-z]{2})>.*?>\s*([^<]+?)</a>\s*"
    r"<td align=right>(\d+)\s*<td align=right>([\d.]+)%\s*<td align=right>([\d.]+)% \(\d+\)",
    re.S,
)
CCTLD_TO_ISO = {"uk": "GB"}
NOT_A_COUNTRY = {"eu"}
MIN_ROWS = 50


def _section(page: str, title: str) -> str:
    match = re.search(rf"<h3>{title} \(Umbrella\)</h3>(.*?)</table>", page, re.S)
    return match.group(1) if match else ""


def parse(page: str, min_rows: int = MIN_ROWS) -> dict:
    result = {"url": URL}
    for service in SERVICES:
        rows = []
        for cc, name, sites, weighted, green in ROW.findall(_section(page, TITLES[service])):
            if cc in NOT_A_COUNTRY:
                continue
            rows.append({"code": CCTLD_TO_ISO.get(cc, cc.upper()), "name": html.unescape(name.strip()),
                         "sites": int(sites), "weighted_pct": float(weighted), "green_pct": float(green)})
        if len(rows) < min_rows:
            raise ValueError(f"Vyncke page format changed: {len(rows)} rows in the {service} table")
        result[service] = rows
    return result


@source("vyncke", MONTH, title="Vyncke IPv6 deployment status (top websites per country)", url=URL)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)
