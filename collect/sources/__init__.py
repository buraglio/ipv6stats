"""Importing this package registers every source with collect.registry."""
from collect.sources import (  # noqa: F401
    apnic, apnic_detail, bgp, cloud_endpoints, cloudflare, isoc, nist, rir, sixlab, tranco,
    vyncke,
)
