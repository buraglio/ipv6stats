"""Cloud Services: measured IPv6 for 23 providers next to a dated, curated reference."""
from collect.sources.cloud_ranges import PROVIDERS as RANGE_PROVIDERS
from web import reference
from web.data import Data, combine


def context(data: Data) -> dict:
    providers = reference.load_cloud_providers()
    endpoints = data.datum("cloud_endpoints", lambda p: {e["key"]: e for e in p["providers"]})
    ranges = {key: data.datum(f"ip_ranges_{key}", lambda p: p) for key in RANGE_PROVIDERS}
    present = [d for d in ranges.values() if d is not None]
    rows = [{"key": p["key"], "name": p["name"],
             "endpoints": endpoints.value.get(p["key"]) if endpoints else None,
             "ranges": ranges.get(p["key"]),  # this provider's own Datum: its own date and stale flag
             "publishes_ranges": p["key"] in RANGE_PROVIDERS,
             "reference": p}
            for p in providers]
    return {
        "rows": rows,
        "providers_count": len(providers),
        "endpoints": endpoints,
        "ranges": combine({k: d.value for k, d in ranges.items() if d}, present) if present else None,
        "aws": data.datum("aws_ipv6_services", lambda p: p),
    }
