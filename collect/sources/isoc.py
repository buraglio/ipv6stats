"""Internet Society Pulse API: IPv6, HTTPS and TLS 1.3 on the top websites, and Pulse's
global IPv6 user figure.

Needs ISOC_PULSE_API_KEY (account at pulse.internetsociety.org/en/api/).
Docs: https://pulse.internetsociety.org/api/docs
"""
from collect.registry import MONTH, Context, source

API = "https://pulse-api.internetsociety.org"
HOME = "https://pulse.internetsociety.org/"
TOPSITES = 1000  # Pulse's "top sites" series cover the top 1,000 websites
SERIES = (  # (payload key, path); values come back as fractions of 1
    ("websites_ipv6", "/ipv6?topsites=true"),
    ("websites_https", "/https?topsites=true"),
    ("websites_tls13", "/tls13"),
    ("users_ipv6", "/ipv6"),  # blends APNIC, Cloudflare, Facebook and Google measurements
)


def parse_series(body: dict) -> dict:
    rows = body.get("data") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"ISOC Pulse response format changed: keys {sorted(body) if isinstance(body, dict) else body!r}")
    if not rows:
        raise ValueError("ISOC Pulse series is empty")
    points = []
    for row in rows:
        value = float(row["value"])
        if not 0 <= value <= 1:
            raise ValueError(f"ISOC Pulse response format changed: value {value} is not a fraction")
        points.append({"date": row["date"], "value": round(100 * value, 2)})
    points.sort(key=lambda p: p["date"])
    return {"latest": points[-1], "series": points}


@source("isoc_pulse", MONTH, title="Internet Society Pulse API", url=HOME, requires_env=("ISOC_PULSE_API_KEY",))
def fetch(ctx: Context) -> dict:
    headers = {"Authorization": f"Bearer {ctx.env['ISOC_PULSE_API_KEY'].strip()}"}
    payload = {"url": HOME}
    for key, path in SERIES:
        response = ctx.session.get(f"{API}{path}", headers=headers, timeout=60)
        if not response.ok:
            raise ValueError(f"ISOC Pulse API HTTP {response.status_code} for {path}: {response.text[:200]}")
        payload[key] = parse_series(response.json())
    return payload
