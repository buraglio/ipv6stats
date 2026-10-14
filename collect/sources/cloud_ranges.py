"""IPv4 and IPv6 prefix counts from cloud providers' published IP-range files.

One source per provider, so one broken file only affects that provider.
"""
import json

from collect.registry import MONTH, Context, source


def _counts(v4: int, v6: int, **extra) -> dict:
    if v4 + v6 == 0:
        raise ValueError("IP range file format changed: no prefixes found")
    return {"ipv4_prefixes": v4, "ipv6_prefixes": v6, **extra}


def _aws(texts):
    d = json.loads(texts[0])
    v4_services = {p["service"] for p in d["prefixes"]}
    v6_services = {p["service"] for p in d["ipv6_prefixes"]}
    return _counts(len(d["prefixes"]), len(d["ipv6_prefixes"]),
                   services=len(v4_services | v6_services), services_with_ipv6=len(v6_services))


def _gcp(texts):
    prefixes = json.loads(texts[0])["prefixes"]
    return _counts(sum("ipv4Prefix" in p for p in prefixes), sum("ipv6Prefix" in p for p in prefixes))


def _oracle(texts):
    cidrs = [c["cidr"] for region in json.loads(texts[0])["regions"] for c in region["cidrs"]]
    return _counts(sum(":" not in c for c in cidrs), sum(":" in c for c in cidrs))


def _first_column(texts):  # CSV geofeeds: prefix,country,region,city,postal
    prefixes = [line.split(",")[0].strip() for line in texts[0].splitlines()
                if line.strip() and not line.startswith("#")]
    return _counts(sum(":" not in p for p in prefixes), sum(":" in p for p in prefixes))


def _cloudflare(texts):
    return _counts(len(texts[0].split()), len(texts[1].split()))


def _fastly(texts):
    d = json.loads(texts[0])
    return _counts(len(d["addresses"]), len(d["ipv6_addresses"]))


PROVIDERS = {
    "aws": ("AWS published IP ranges", ("https://ip-ranges.amazonaws.com/ip-ranges.json",), _aws),
    "gcp": ("Google Cloud published IP ranges", ("https://www.gstatic.com/ipranges/cloud.json",), _gcp),
    "oracle": ("Oracle Cloud published IP ranges", ("https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json",), _oracle),
    "digitalocean": ("DigitalOcean published IP ranges", ("https://digitalocean.com/geo/google.csv",), _first_column),
    "linode": ("Linode published IP ranges", ("https://geoip.linode.com/",), _first_column),
    "cloudflare": ("Cloudflare published IP ranges", ("https://www.cloudflare.com/ips-v4", "https://www.cloudflare.com/ips-v6"), _cloudflare),
    "fastly": ("Fastly published IP ranges", ("https://api.fastly.com/public-ip-list",), _fastly),
}


def _register(key: str, title: str, urls: tuple, parser) -> None:
    def fetch(ctx: Context) -> dict:
        texts = []
        for url in urls:
            response = ctx.session.get(url, timeout=60)
            response.raise_for_status()
            texts.append(response.text)
        return {**parser(texts), "url": urls[0]}

    source(f"ip_ranges_{key}", MONTH, title=title, url=urls[0])(fetch)


for _key, (_title, _urls, _parser) in PROVIDERS.items():
    _register(_key, _title, _urls, _parser)
