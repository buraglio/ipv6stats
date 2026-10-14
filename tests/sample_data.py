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
        "url": "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
    },
    "afrinic_delegations": {
        "file_date": "2026-10-14", "total_blocks_32": 11300.0, "countries": 54,
        "top_countries": [{"code": "ZA", "blocks_32": 2500.0, "share": 22.1}],
        "url": "https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest",
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
