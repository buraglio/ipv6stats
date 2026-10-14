import json

import pytest

from collect.registry import SOURCES
from collect.sources import cloud_ranges as cr
from tests.fakes import FakeResponse, make_ctx

AWS = {"prefixes": [{"ip_prefix": "3.0.0.0/15", "service": "AMAZON"}, {"ip_prefix": "3.2.0.0/16", "service": "EC2"}],
       "ipv6_prefixes": [{"ipv6_prefix": "2600:1f00::/24", "service": "AMAZON"}]}
SAMPLES = {
    "aws": [json.dumps(AWS)],
    "gcp": [json.dumps({"prefixes": [{"ipv4Prefix": "34.1.0.0/16"}, {"ipv6Prefix": "2600:1900::/28"}]})],
    "oracle": [json.dumps({"regions": [{"cidrs": [{"cidr": "129.80.0.0/16"}, {"cidr": "130.35.0.0/16"}]}]})],
    "digitalocean": ["5.101.96.0/21,NL,NL-NH,Amsterdam,1098 XG\n2a03:b0c0::/32,NL,NL-NH,Amsterdam,\n"],
    "linode": ["# comment\n69.164.192.0/18,US,US-NJ,Cedar Knolls,\n2600:3c00::/32,US,US-TX,Richardson,\n"],
    "cloudflare": ["173.245.48.0/20\n103.21.244.0/22\n", "2400:cb00::/32\n"],
    "fastly": [json.dumps({"addresses": ["23.235.32.0/20"], "ipv6_addresses": ["2a04:4e40::/32"]})],
}


def ctx_for(key, bodies):
    return make_ctx(routes={url: FakeResponse(text=body) for url, body in zip(cr.PROVIDERS[key][1], bodies)})


@pytest.mark.parametrize("key,v4,v6", [("aws", 2, 1), ("gcp", 1, 1), ("oracle", 2, 0), ("digitalocean", 1, 1),
                                       ("linode", 1, 1), ("cloudflare", 2, 1), ("fastly", 1, 1)])
def test_counts_per_provider(key, v4, v6):
    payload = SOURCES[f"ip_ranges_{key}"].fetch(ctx_for(key, SAMPLES[key]))
    assert (payload["ipv4_prefixes"], payload["ipv6_prefixes"]) == (v4, v6)


def test_aws_counts_services():
    payload = SOURCES["ip_ranges_aws"].fetch(ctx_for("aws", SAMPLES["aws"]))
    assert (payload["services"], payload["services_with_ipv6"]) == (2, 1)


def test_rejects_empty_or_changed_file():
    with pytest.raises(ValueError, match="format changed"):
        SOURCES["ip_ranges_gcp"].fetch(ctx_for("gcp", [json.dumps({"prefixes": []})]))
    with pytest.raises(Exception):
        SOURCES["ip_ranges_aws"].fetch(ctx_for("aws", ["<html>moved</html>"]))


def test_each_provider_is_its_own_source():
    assert {f"ip_ranges_{k}" for k in cr.PROVIDERS} <= set(SOURCES)
