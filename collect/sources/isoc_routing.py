"""Internet Society Pulse routing security: ROA coverage by IP version, and ROV adoption."""
from collect.registry import MONTH, Context, source
from collect.sources.isoc import API, HOME, parse_series


def _get(ctx: Context, path: str) -> dict:
    headers = {"Authorization": f"Bearer {ctx.env['ISOC_PULSE_API_KEY'].strip()}"}
    response = ctx.session.get(f"{API}{path}", headers=headers, timeout=60)
    if not response.ok:
        raise ValueError(f"ISOC Pulse API HTTP {response.status_code} for {path}: {response.text[:200]}")
    return response.json()


def parse_rov(body: dict) -> dict:
    rows = body.get("data") if isinstance(body, dict) else None
    if not rows or not all({"date", "partial", "full"} <= set(r) for r in rows):
        raise ValueError("ISOC Pulse response format changed: ROV rows need date, partial and full")
    series = sorted(({"date": r["date"], "partial": round(100 * float(r["partial"]), 2),
                      "full": round(100 * float(r["full"]), 2)} for r in rows), key=lambda r: r["date"])
    return {"latest": series[-1], "series": series}


def without_gaps(series: dict) -> dict:
    """ROA coverage of address space can't drop to zero and recover; zero points are missing data."""
    points = [p for p in series["series"] if p["value"] > 0]
    if not points:
        raise ValueError("ISOC Pulse ROA series has no non-zero values")
    return {"latest": points[-1], "series": points}


@source("isoc_routing", MONTH, title="Internet Society Pulse routing security (API)", url=HOME,
        requires_env=("ISOC_PULSE_API_KEY",))
def fetch(ctx: Context) -> dict:
    return {"roa_ipv6": without_gaps(parse_series(_get(ctx, "/roa?ip_version=6"))),
            "roa_ipv4": without_gaps(parse_series(_get(ctx, "/roa?ip_version=4"))),
            "rov": parse_rov(_get(ctx, "/rov")), "url": HOME}
