"""IPv6 users per country from the Cisco 6lab statistics mirror (6lab-stats.com)."""
import re

from collect.registry import MONTH, Context, source

URL = "https://6lab-stats.com/6lab-stats/curr/users.js"
HOME = "https://6lab-stats.com/"
# Rows: ["US", "United States of America",0.546,1.36532176E8,57.2],
# Only the last column (IPv6 users %) is used; the meaning of the middle two is not documented.
ROW = re.compile(r'^\["([A-Z]{2})",\s*"([^"]*)",\s*([-\d.Ee+]+),\s*([-\d.Ee+]+),\s*([\d.]+)\]', re.M)
MIN_COUNTRIES = 150


def parse(text: str, min_countries: int = MIN_COUNTRIES) -> dict:
    # Rows that are 0.0,0.0,0.0 mean "no data" for that territory, not zero IPv6 users.
    countries = [{"code": code, "name": name, "ipv6_users_pct": float(pct)}
                 for code, name, first, second, pct in ROW.findall(text)
                 if any(float(v) for v in (first, second, pct))]
    if len(countries) < min_countries:
        raise ValueError(f"6lab users.js format changed: {len(countries)} countries")
    return {"countries": countries, "url": HOME}


@source("cisco_6lab", MONTH, title="Cisco 6lab statistics (community mirror)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(URL, timeout=30)
    response.raise_for_status()
    return parse(response.text)
