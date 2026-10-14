"""PeeringDB: networks that list IPv6 traffic (info_ipv6)."""
from collect.registry import MONTH, Context, source

API = "https://www.peeringdb.com/api/net?fields=info_ipv6&depth=0"
HOME = "https://www.peeringdb.com/"
MIN_NETWORKS = 10_000


@source("peeringdb_networks", MONTH, title="PeeringDB networks (API)", url=HOME)
def fetch(ctx: Context) -> dict:
    response = ctx.session.get(API, timeout=120)
    response.raise_for_status()
    networks = response.json().get("data", [])
    if len(networks) < MIN_NETWORKS:
        raise ValueError(f"PeeringDB API format changed: {len(networks)} networks")
    return {"networks": len(networks), "ipv6_networks": sum(1 for n in networks if n.get("info_ipv6")), "url": HOME}
