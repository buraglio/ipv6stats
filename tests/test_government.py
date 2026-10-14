import pytest

from collect.registry import SOURCES
from collect.sources import government as gov
from tests.fakes import make_ctx

LIST = {"group": [{"name": "Test", "domains": ["a.example", "b.example", "c.example"]}]}


def test_measure_apex_or_www():
    result = gov.measure(LIST, {"a.example", "www.b.example"}.__contains__,
                         {"a.example", "b.example", "c.example", "www.b.example"}.__contains__)
    g = result["groups"][0]
    assert [d["status"] for d in g["domains"]] == ["ipv6", "ipv6", "ipv4_only"]
    assert (g["with_ipv6"], g["checked"]) == (2, 3)


def test_government_lookup_failures_fail_the_source():
    with pytest.raises(ValueError, match="lookups failed"):
        gov.measure(LIST, lambda n: None, lambda n: None)


def test_fetch_reads_reference_list():
    hosts = {d for g in gov.load_list()["group"] for d in g["domains"]}
    result = SOURCES["government_domains"].fetch(make_ctx(aaaa=hosts))
    assert result["total"] == len(hosts) and result["unknown"] == 0
