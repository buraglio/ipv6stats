"""Importing this package registers every source with collect.registry."""
from collect.sources import (  # noqa: F401
    apnic, apnic_detail, apnic_regions, atlas, aws_ipv6, bgp, cidr_report, cloud_endpoints,
    cloud_ranges, cloudflare, cymru, he_report, isoc, nist, peeringdb, potaroo_summary, rir,
    routeviews, sixlab, tranco, vyncke,
)
