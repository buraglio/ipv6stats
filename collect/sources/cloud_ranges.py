"""IPv4 and IPv6 prefix counts from cloud providers' published IP-range files.

One source per provider, so one broken file only affects that provider.
"""
import ipaddress
import json

from collect.registry import MONTH, Context, source

AWS_AGGREGATE = "AMAZON"  # ip-ranges.json repeats every prefix under this name; it isn't a service


def _counts(prefixes: list[str], **extra) -> dict:
    """Count distinct IPv4 and IPv6 prefixes; anything that isn't a prefix means the file changed."""
    networks = set()
    for text in prefixes:
        try:
            networks.add(ipaddress.ip_network(text.strip(), strict=False))
        except ValueError as exc:
            raise ValueError(f"IP range file format changed: not a prefix: {text.strip()[:60]!r}") from exc
    if not networks:
        raise ValueError("IP range file format changed: no prefixes found")
    return {"ipv4_prefixes": sum(n.version == 4 for n in networks),
            "ipv6_prefixes": sum(n.version == 6 for n in networks), **extra}


def _aws(texts):
    d = json.loads(texts[0])
    v4 = [(p["ip_prefix"], p["service"]) for p in d["prefixes"]]
    v6 = [(p["ipv6_prefix"], p["service"]) for p in d["ipv6_prefixes"]]
    services = {svc for _, svc in v4 + v6 if svc != AWS_AGGREGATE}
    v6_services = {svc for _, svc in v6 if svc != AWS_AGGREGATE}
    return _counts([prefix for prefix, _ in v4 + v6], services=len(services), services_with_ipv6=len(v6_services))


def _gcp(texts):
    prefixes = json.loads(texts[0])["prefixes"]
    return _counts([p.get("ipv4Prefix") or p.get("ipv6Prefix") or "" for p in prefixes])


def _oracle(texts):
    return _counts([c["cidr"] for region in json.loads(texts[0])["regions"] for c in region["cidrs"]])


def _first_column(texts):  # CSV geofeeds: prefix,country,region,city,postal
    return _counts([line.split(",")[0] for line in texts[0].splitlines()
                    if line.strip() and not line.startswith("#")])


def _cloudflare(texts):
    return _counts(texts[0].split() + texts[1].split())


def _fastly(texts):
    d = json.loads(texts[0])
    return _counts(d["addresses"] + d["ipv6_addresses"])


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
