import pytest

from collect.registry import SOURCES
from collect.sources import cloud_endpoints as ce
from tests.fakes import make_ctx

SMALL = {"p": {"name": "P", "hosts": {"website": "www.p.example", "api": "api.p.example", "docs": "docs.p.example"}}}


def test_check_statuses():
    v6, v4 = {"six.example"}.__contains__, {"four.example", "six.example"}.__contains__
    assert ce.check("six.example", v6, v4) == "ipv6"
    assert ce.check("four.example", v6, v4) == "ipv4_only"


def test_unresolvable_name_is_unknown_not_ipv4():
    assert ce.check("gone.example", lambda n: False, lambda n: False) == "unknown"
    assert ce.check("slow.example", lambda n: None, lambda n: True) == "unknown"


def test_measure_counts_known_hosts_only():
    v6 = {"www.p.example"}.__contains__
    result = ce.measure(SMALL, v6, {"www.p.example", "api.p.example"}.__contains__, max_unknown=0.5)
    p = result["providers"][0]
    assert (p["with_ipv6"], p["checked"]) == (1, 2)              # docs.p.example doesn't resolve
    assert [h["status"] for h in p["hosts"]] == ["ipv6", "ipv4_only", "unknown"]
    assert (result["unknown"], result["total"]) == (1, 3)


def test_too_many_unknown_lookups_fail():
    with pytest.raises(ValueError, match="lookups failed"):
        ce.measure(SMALL, lambda n: None, lambda n: None)


def test_endpoint_list_shape():
    assert len(ce.ENDPOINTS) == 23
    for key, entry in ce.ENDPOINTS.items():
        assert set(entry["hosts"]) <= set(ce.ROLES), key
        assert entry["name"]


def test_fetch_uses_context_dns():
    hosts = {h for e in ce.ENDPOINTS.values() for h in e["hosts"].values()}
    result = SOURCES["cloud_endpoints"].fetch(make_ctx(aaaa=hosts))
    assert all(p["with_ipv6"] == p["checked"] for p in result["providers"])
