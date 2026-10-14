"""Cloudflare Radar: share of HTTP requests over IPv6, 52 weeks of history."""
from collect.registry import MONTH, Context, source

API = "https://api.cloudflare.com/client/v4/radar/http/timeseries_groups/ip_version?dateRange=52w"
PAGE = "https://radar.cloudflare.com/adoption-and-usage"


def parse(body: dict) -> dict:
    if not body.get("success"):
        raise ValueError(f"Cloudflare API error: {body.get('errors')}")
    result = body.get("result") or {}
    # Current shape is result.serie_0; older responses used result.main or top level.
    series = result.get("serie_0") or result.get("main") or (result if "IPv6" in result else None)
    if not series:
        raise ValueError(f"unexpected Cloudflare response keys: {sorted(result)}")
    stamps, ipv6, ipv4 = series["timestamps"], series["IPv6"], series["IPv4"]
    if not ipv6 or len(stamps) != len(ipv6):
        raise ValueError("unexpected Cloudflare response: empty or mismatched series")
    return {
        "series": [{"t": t, "ipv6": round(float(v), 2)} for t, v in zip(stamps, ipv6)],
        "latest_ipv6": round(float(ipv6[-1]), 2),
        "latest_ipv4": round(float(ipv4[-1]), 2),
        "url": PAGE,
    }


@source("cloudflare_ip_version", MONTH, title="Cloudflare Radar HTTP traffic by IP version",
        url=PAGE, requires_env=("CLOUDFLARE_API_KEY",))
def fetch(ctx: Context) -> dict:
    token = ctx.env["CLOUDFLARE_API_KEY"].strip()
    response = ctx.session.get(API, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if not response.ok:
        raise ValueError(f"Cloudflare API HTTP {response.status_code}: {response.text[:300]}")
    return parse(response.json())
