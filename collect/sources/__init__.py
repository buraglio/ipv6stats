"""Importing this package registers every source with collect.registry."""
from collect.sources import (  # noqa: F401
    apnic, apnic_detail, aws_ipv6, bgp, cloud_endpoints, cloudflare, isoc, nist, rir,
    sixlab, tranco, vyncke,
)
