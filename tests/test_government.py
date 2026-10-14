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
    domains = {d for g in gov.load_list()["group"] for d in g["domains"]}
    result = SOURCES["government_domains"].fetch(make_ctx(aaaa=domains | set(gov.CANARIES)))
    assert result["total"] == len(domains) and result["unknown"] == 0


def test_resolver_hiding_aaaa_fails_the_source():
    hosts = {d for g in gov.load_list()["group"] for d in g["domains"]}
    with pytest.raises(ValueError, match="dual-stack"):
        SOURCES["government_domains"].fetch(make_ctx(aaaa=set(), a=hosts))


def test_failed_half_lookup_is_unknown_not_ipv4():
    # apex lookup timed out, www has only IPv4: the apex might have IPv6, so the answer is unknown
    def has_aaaa(name):
        return None if name == "a.example" else False
    assert gov._status("a.example", has_aaaa, lambda n: True) == "unknown"
