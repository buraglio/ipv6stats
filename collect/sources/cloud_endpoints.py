"""Whether cloud providers' own default hostnames publish IPv6 (AAAA) records.

Measured from GitHub's runners, which have no IPv6: this shows published IPv6, not
end-to-end reachability.
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from collect.registry import MONTH, Context, source

METHOD = "https://github.com/buraglio/ipv6stats/blob/main/collect/sources/cloud_endpoints.py"
ROLES = ("website", "console", "api", "docs", "storage", "status")
MAX_UNKNOWN = 0.05
WORKERS = 16

ENDPOINTS = {
    "aws": {"name": "AWS", "hosts": {"website": "aws.amazon.com", "console": "console.aws.amazon.com", "api": "ec2.us-east-1.amazonaws.com", "docs": "docs.aws.amazon.com", "storage": "s3.us-east-1.amazonaws.com", "status": "health.aws.amazon.com"}},
    "azure": {"name": "Microsoft Azure", "hosts": {"website": "azure.microsoft.com", "console": "portal.azure.com", "api": "management.azure.com", "docs": "learn.microsoft.com", "storage": "azureopendatastorage.blob.core.windows.net", "status": "azure.status.microsoft"}},
    "gcp": {"name": "Google Cloud Platform", "hosts": {"website": "cloud.google.com", "console": "console.cloud.google.com", "api": "compute.googleapis.com", "docs": "docs.cloud.google.com", "storage": "storage.googleapis.com", "status": "status.cloud.google.com"}},
    "oracle": {"name": "Oracle Cloud", "hosts": {"website": "www.oracle.com", "console": "cloud.oracle.com", "api": "iaas.us-ashburn-1.oraclecloud.com", "docs": "docs.oracle.com", "storage": "objectstorage.us-ashburn-1.oraclecloud.com", "status": "ocistatus.oraclecloud.com"}},
    "digitalocean": {"name": "DigitalOcean", "hosts": {"website": "www.digitalocean.com", "console": "cloud.digitalocean.com", "api": "api.digitalocean.com", "docs": "docs.digitalocean.com", "storage": "nyc3.digitaloceanspaces.com", "status": "status.digitalocean.com"}},
    "vultr": {"name": "Vultr", "hosts": {"website": "www.vultr.com", "console": "my.vultr.com", "api": "api.vultr.com", "docs": "docs.vultr.com", "storage": "ewr1.vultrobjects.com", "status": "status.vultr.com"}},
    "linode": {"name": "Linode (Akamai)", "hosts": {"website": "www.linode.com", "console": "cloud.linode.com", "api": "api.linode.com", "docs": "techdocs.akamai.com", "storage": "us-east-1.linodeobjects.com", "status": "status.linode.com"}},
    "cloudflare": {"name": "Cloudflare", "hosts": {"website": "www.cloudflare.com", "console": "dash.cloudflare.com", "api": "api.cloudflare.com", "docs": "developers.cloudflare.com", "storage": "r2.cloudflarestorage.com", "status": "www.cloudflarestatus.com"}},
    "mythic-beasts": {"name": "Mythic Beasts", "hosts": {"website": "www.mythic-beasts.com", "api": "api.mythic-beasts.com", "status": "status.mythic-beasts.com"}},
    "hetzner": {"name": "Hetzner", "hosts": {"website": "www.hetzner.com", "console": "console.hetzner.cloud", "api": "api.hetzner.cloud", "docs": "docs.hetzner.com", "storage": "fsn1.your-objectstorage.com", "status": "status.hetzner.com"}},
    "scaleway": {"name": "Scaleway", "hosts": {"website": "www.scaleway.com", "console": "console.scaleway.com", "api": "api.scaleway.com", "storage": "s3.fr-par.scw.cloud", "status": "status.scaleway.com"}},
    "ovhcloud": {"name": "OVHcloud", "hosts": {"website": "www.ovhcloud.com", "console": "www.ovh.com", "api": "eu.api.ovh.com", "docs": "help.ovhcloud.com", "storage": "s3.gra.io.cloud.ovh.net", "status": "public-cloud.status-ovhcloud.com"}},
    "contabo": {"name": "Contabo", "hosts": {"website": "contabo.com", "console": "my.contabo.com", "api": "api.contabo.com", "docs": "docs.contabo.com", "storage": "eu2.contabostorage.com", "status": "contabo-status.com"}},
    "ionos": {"name": "IONOS", "hosts": {"website": "www.ionos.com", "console": "my.ionos.com", "api": "api.ionos.com", "docs": "docs.ionos.com", "storage": "s3.eu-central-1.ionoscloud.com", "status": "status.ionos.cloud"}},
    "upcloud": {"name": "UpCloud", "hosts": {"website": "upcloud.com", "console": "hub.upcloud.com", "api": "api.upcloud.com", "status": "status.upcloud.com"}},
    "binarylane": {"name": "BinaryLane", "hosts": {"website": "www.binarylane.com.au", "console": "home.binarylane.com.au", "api": "api.binarylane.com.au", "docs": "support.binarylane.com.au", "status": "status.binarylane.com.au"}},
    "kamatera": {"name": "Kamatera", "hosts": {"website": "www.kamatera.com", "console": "console.kamatera.com", "api": "cloudcli.cloudwm.com", "status": "status.kamatera.com"}},
    "hostinger": {"name": "Hostinger", "hosts": {"website": "www.hostinger.com", "console": "hpanel.hostinger.com", "api": "developers.hostinger.com", "docs": "support.hostinger.com", "status": "statuspage.hostinger.com"}},
    "fastly": {"name": "Fastly", "hosts": {"website": "www.fastly.com", "console": "manage.fastly.com", "api": "api.fastly.com", "docs": "docs.fastly.com", "status": "www.fastlystatus.com"}},
    "backblaze": {"name": "Backblaze", "hosts": {"website": "www.backblaze.com", "console": "secure.backblaze.com", "api": "api.backblazeb2.com", "storage": "s3.us-west-004.backblazeb2.com", "status": "status.backblaze.com"}},
    "railway": {"name": "Railway", "hosts": {"website": "railway.com", "api": "backboard.railway.com", "docs": "docs.railway.com", "status": "status.railway.com"}},
    "render": {"name": "Render", "hosts": {"website": "render.com", "console": "dashboard.render.com", "api": "api.render.com", "status": "status.render.com"}},
    "fly-io": {"name": "Fly.io", "hosts": {"website": "fly.io", "api": "api.machines.dev", "status": "status.flyio.net"}},
}


def check(host: str, has_aaaa: Callable, has_a: Callable) -> str:
    v6 = has_aaaa(host)
    if v6:
        return "ipv6"
    v4 = has_a(host)
    if v6 is None or not v4:  # lookup failed, or the name no longer resolves at all
        return "unknown"
    return "ipv4_only"


def measure(endpoints: dict, has_aaaa: Callable, has_a: Callable, max_unknown: float = MAX_UNKNOWN) -> dict:
    jobs = [(key, role, host) for key, entry in endpoints.items() for role, host in entry["hosts"].items()]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        statuses = list(pool.map(lambda job: check(job[2], has_aaaa, has_a), jobs))
    unknown = statuses.count("unknown")
    if unknown > max_unknown * len(jobs):
        raise ValueError(f"{unknown} of {len(jobs)} hostname lookups failed; not trusting the result")
    by_key: dict[str, list] = {}
    for (key, role, host), status in zip(jobs, statuses):
        by_key.setdefault(key, []).append({"role": role, "host": host, "status": status})
    providers = [{"key": key, "name": endpoints[key]["name"], "hosts": hosts,
                  "with_ipv6": sum(h["status"] == "ipv6" for h in hosts),
                  "checked": sum(h["status"] != "unknown" for h in hosts)}
                 for key, hosts in by_key.items()]
    return {"providers": providers, "unknown": unknown, "total": len(jobs)}


@source("cloud_endpoints", MONTH, title="Cloud provider hostnames with IPv6 (AAAA lookups, measured)", url=METHOD)
def fetch(ctx: Context) -> dict:
    return measure(ENDPOINTS, ctx.has_aaaa, ctx.has_a)
