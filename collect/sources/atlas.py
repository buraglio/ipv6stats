"""RIPE Atlas: connected probes, and how many have working IPv6 and IPv4."""
from collect.registry import MONTH, Context, source

API = "https://atlas.ripe.net/api/v2/probes/?status=1&page_size=1"
HOME = "https://atlas.ripe.net/"


def _count(ctx: Context, url: str) -> int:
    response = ctx.session.get(url, timeout=60)
    response.raise_for_status()
    return int(response.json()["count"])


@source("ripe_atlas_probes", MONTH, title="RIPE Atlas probes (API)", url=HOME)
def fetch(ctx: Context) -> dict:
    connected = _count(ctx, API)
    v6 = _count(ctx, f"{API}&tags=system-ipv6-works")
    v4 = _count(ctx, f"{API}&tags=system-ipv4-works")
    if not connected or v6 > connected or v4 > connected:
        raise ValueError(f"RIPE Atlas API returned impossible counts: {connected}, {v6}, {v4}")
    return {"connected": connected, "ipv6_works": v6, "ipv4_works": v4, "url": HOME}
