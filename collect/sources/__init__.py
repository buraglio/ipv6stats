"""Importing this package registers every source with collect.registry."""
from collect.sources import (  # noqa: F401
    apnic, apnic_detail, aws_ipv6, bgp, cidr_report, cloud_endpoints, cloud_ranges,
    cloudflare, isoc, nist, potaroo_summary, rir, sixlab, tranco, vyncke,
)
