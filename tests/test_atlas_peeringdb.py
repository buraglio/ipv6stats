import pytest

from collect.registry import SOURCES
from collect.sources import atlas, peeringdb
from tests.fakes import FakeResponse, make_ctx


def atlas_routes(connected=15265, v6=7075, v4=14000):
    return {f"{atlas.API}&tags=system-ipv6-works": FakeResponse(json_data={"count": v6, "results": []}),
            f"{atlas.API}&tags=system-ipv4-works": FakeResponse(json_data={"count": v4, "results": []}),
            atlas.API: FakeResponse(json_data={"count": connected, "results": []})}


def test_atlas_counts():
    assert SOURCES["ripe_atlas_probes"].fetch(make_ctx(routes=atlas_routes())) == {
        "connected": 15265, "ipv6_works": 7075, "ipv4_works": 14000, "url": atlas.HOME}


def test_atlas_rejects_impossible_counts():
    with pytest.raises(ValueError, match="RIPE Atlas"):
        SOURCES["ripe_atlas_probes"].fetch(make_ctx(routes=atlas_routes(connected=10, v6=20)))


def test_peeringdb_counts(monkeypatch):
    monkeypatch.setattr(peeringdb, "MIN_NETWORKS", 1)
    body = {"data": [{"info_ipv6": True}, {"info_ipv6": False}, {"info_ipv6": True}]}
    payload = SOURCES["peeringdb_networks"].fetch(make_ctx(routes={peeringdb.API: FakeResponse(json_data=body)}))
    assert (payload["networks"], payload["ipv6_networks"]) == (3, 2)


def test_peeringdb_rejects_changed_format():
    with pytest.raises(ValueError, match="PeeringDB"):
        SOURCES["peeringdb_networks"].fetch(make_ctx(routes={peeringdb.API: FakeResponse(json_data={"data": []})}))
