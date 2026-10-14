"""A complete, realistic data directory for web tests."""
import json
from datetime import datetime, timezone
from pathlib import Path

import collect.sources  # noqa: F401  (registers sources)
from collect.manifest import save
from collect.registry import SOURCES

NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)
FETCHED = "2026-10-14T00:05:00+00:00"

PAYLOADS = {
    "apnic": {
        "world": {"code": "XA", "name": "World", "capable": 43.6, "preferred": 41.0, "samples": 972331706},
        "regions": [
            {"code": "XC", "name": "Americas", "capable": 51.0, "preferred": 49.6, "samples": 171761189},
            {"code": "XE", "name": "Europe", "capable": 36.9, "preferred": 35.7, "samples": 134455991},
            {"code": "XG", "name": "Unclassified", "capable": 1.9, "preferred": 1.7, "samples": 16151},
        ],
        "economies": [
            {"code": "BL", "name": "Saint Barthelemy", "capable": 97.1, "preferred": 90.0, "samples": 2000},
            {"code": "DE", "name": "Germany", "capable": 49.5, "preferred": 48.0, "samples": 30000000},
            {"code": "FR", "name": "France", "capable": 85.6, "preferred": 80.0, "samples": 20000000},
            {"code": "US", "name": "United States of America", "capable": 61.9, "preferred": 59.9,
             "samples": 97679957},
        ],
        "url": "https://stats.labs.apnic.net/ipv6/",
    },
    "bgp_v6_table": {
        "daily": [
            {"date": "2025-10-01", "prefixes": 230000},
            {"date": "2025-10-14", "prefixes": 231000},
            {"date": "2026-09-14", "prefixes": 255000},
            {"date": "2026-10-14", "prefixes": 258009},
        ],
        "current": 258009,
        "current_at": "2026-10-14T00:00:00+00:00",
        "url": "https://bgp.potaroo.net/v6/as2.0/index.html",
    },
    "cloudflare_ip_version": {
        "series": [{"t": "2026-10-06T00:00:00Z", "ipv6": 37.9}, {"t": "2026-10-13T00:00:00Z", "ipv6": 38.4}],
        "latest_ipv6": 38.4,
        "latest_ipv4": 61.6,
        "url": "https://radar.cloudflare.com/adoption-and-usage",
    },
    "tranco_aaaa": {
        "checked": 1000, "with_aaaa": 612, "percentage": 61.2,
        "top": [{"rank": 1, "domain": "google.com", "aaaa": True}],
        "list_url": "https://tranco-list.eu/",
    },
    "lacnic_delegations": {
        "file_date": "2026-10-13", "total_blocks_32": 31250.0, "countries": 33,
        "top_countries": [{"code": "BR", "blocks_32": 20000.0, "share": 64.0}],
        "by_country": {"BR": 20000.0, "MX": 4000.0},
        "history": [{"year": 2003, "blocks_32": 100.0}, {"year": 2026, "blocks_32": 31250.0}],
        "url": "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
    },
    "afrinic_delegations": {
        "file_date": "2026-10-14", "total_blocks_32": 11300.0, "countries": 54,
        "top_countries": [{"code": "ZA", "blocks_32": 2500.0, "share": 22.1}],
        "by_country": {"ZA": 2500.0},
        "history": [{"year": 2005, "blocks_32": 10.0}, {"year": 2026, "blocks_32": 11300.0}],
        "url": "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest",
    },
    "apnic_delegations": {
        "file_date": "2026-10-14", "total_blocks_32": 14000.0, "countries": 50,
        "top_countries": [{"code": "JP", "blocks_32": 8000.0, "share": 57.1}],
        "by_country": {"JP": 8000.0, "IN": 6000.0},
        "history": [{"year": 1999, "blocks_32": 50.0}, {"year": 2026, "blocks_32": 14000.0}],
        "url": "https://ftp.apnic.net/stats/apnic/delegated-apnic-latest",
    },
    "arin_delegations": {
        "file_date": "2026-10-14", "total_blocks_32": 63000.0, "countries": 25,
        "top_countries": [{"code": "US", "blocks_32": 60000.0, "share": 95.2}],
        "by_country": {"US": 60000.0, "CA": 3000.0},
        "history": [{"year": 1999, "blocks_32": 40.0}, {"year": 2026, "blocks_32": 63000.0}],
        "url": "https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest",
    },
    "ripe_delegations": {
        "file_date": "2026-10-13", "total_blocks_32": 52000.0, "countries": 70,
        "top_countries": [{"code": "DE", "blocks_32": 9000.0, "share": 17.3}],
        "by_country": {"DE": 9000.0, "FR": 7000.0},
        "history": [{"year": 1999, "blocks_32": 60.0}, {"year": 2026, "blocks_32": 52000.0}],
        "url": "https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest",
    },
    "apnic_economy_detail": {
        "economies": {
            "US": {"history": [{"date": "2025-10-13", "capable": 58.0, "preferred": 56.0},
                               {"date": "2026-10-12", "capable": 61.9, "preferred": 59.9}],
                   "networks": [{"asn": 7922, "name": "COMCAST-7922 - Comcast Cable Communications, LLC",
                                 "capable": 85.28, "preferred": 83.59, "samples": 16629912}]},
            "FR": {"history": [{"date": "2026-10-12", "capable": 85.6, "preferred": 80.0}],
                   "networks": [{"asn": 3215, "name": "FRANCE-TELECOM - Orange", "capable": 90.1,
                                 "preferred": 88.0, "samples": 5000000}]},
        },
        "missing": ["DE"],
    },
    "cisco_6lab": {
        "countries": [{"code": "US", "name": "United States of America", "ipv6_users_pct": 57.2},
                      {"code": "FR", "name": "France", "ipv6_users_pct": 39.0}],
        "url": "https://6lab-stats.com/",
    },
    "vyncke": {
        "web": [{"code": "FR", "name": "France", "sites": 50, "weighted_pct": 57.62, "green_pct": 44.0},
                {"code": "US", "name": "United States of America", "sites": 50, "weighted_pct": 70.51,
                 "green_pct": 50.0}],
        "email": [{"code": "US", "name": "United States of America", "sites": 50, "weighted_pct": 69.89,
                   "green_pct": 52.0}],
        "dns": [{"code": "US", "name": "United States of America", "sites": 50, "weighted_pct": 84.85,
                 "green_pct": 92.0}],
        "url": "https://www.vyncke.org/ipv6status/",
    },
    "nist_usgv6": {
        "domains": 4,
        "totals": {"web": {"operational": 2, "none": 1, "not_applicable": 1},
                   "mail": {"operational": 1, "not_applicable": 3},
                   "dns": {"operational": 4}},
        "agencies": [{"name": "Department of Justice", "domains": 3,
                      "web": {"operational": 2, "none": 1}, "mail": {"operational": 1, "not_applicable": 2},
                      "dns": {"operational": 3}},
                     {"name": "Access Board", "domains": 1, "web": {"not_applicable": 1},
                      "mail": {"not_applicable": 1}, "dns": {"operational": 1}}],
        "url": "https://usgv6-deploymon.nist.gov/",
    },
}


def write_sample_data(data_dir: Path, omit=(), last_success=None) -> Path:
    """Write PAYLOADS and a manifest. Keys in `omit` are recorded as failed;
    `last_success` maps key -> ISO time to override FETCHED (for staleness)."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    overrides = last_success or {}
    manifest = {}
    for key, src in SOURCES.items():
        if key.startswith("test_"):
            continue
        entry = {"ttl_seconds": src.ttl_seconds, "last_attempt": FETCHED}
        if key not in PAYLOADS and src.requires_env:
            entry.update(status="not_configured", error=f"set {', '.join(src.requires_env)} to enable")
        elif key in omit or key not in PAYLOADS:
            entry.update(status="error", error="ConnectionError: sample failure")
        else:
            (data_dir / f"{key}.json").write_text(json.dumps(PAYLOADS[key]))
            entry.update(status="ok", error=None, last_success=overrides.get(key, FETCHED))
        manifest[key] = entry
    save(data_dir, manifest)
    return data_dir
