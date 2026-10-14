import pytest

from collect.registry import SOURCES
from collect.sources import routeviews as rv
from tests.fakes import FakeResponse, make_ctx

COLLECTORS = {"count": 3, "results": [
    {"name": "route-views2", "country": "US", "rir_region": "ARIN", "removed": False},
    {"name": "route-views.wide", "country": "JP", "rir_region": "APNIC", "removed": False},
    {"name": "route-views.old", "country": "US", "rir_region": "ARIN", "removed": True}]}


def snap(name, date, v6):
    return {"collector": name, "date": f"{date}T00:00:00Z", "ipv6_prefix_count": v6, "ipv6_peer_count": 5,
            "ipv4_prefix_count": 1000000}


FIRST = {"count": 150, "results": [snap("route-views2", "2001-10-27", 0)] * 100}
PAGE1 = {"results": [snap("route-views2", "2026-10-13", 250000)] * 50}       # second-to-last page
PAGE2 = {"results": [snap("route-views.wide", "2026-10-14", 255106)]}        # last page


def routes():
    return {f"{rv.BASE}/collector/": FakeResponse(json_data=COLLECTORS),
            f"{rv.BASE}/timeseries/?page=2": FakeResponse(json_data=PAGE2),
            f"{rv.BASE}/timeseries/?page=1": FakeResponse(json_data=PAGE1),
            f"{rv.BASE}/timeseries/": FakeResponse(json_data=FIRST)}


def test_routeviews_reads_last_two_pages():
    payload = rv.collect(make_ctx(routes=routes()), min_collectors=1)
    names = [c["name"] for c in payload["collectors"]]
    assert names == ["route-views.wide", "route-views2"]     # by IPv6 prefixes, removed collector skipped
    assert payload["collectors"][1]["date"] == "2026-10-13"
    assert payload["active"] == 2 and payload["snapshot_date"] == "2026-10-14"


def test_rejects_changed_format():
    bad = routes(); bad[f"{rv.BASE}/collector/"] = FakeResponse(json_data={"detail": "Not found"})
    with pytest.raises(ValueError, match="RouteViews API format changed"):
        rv.collect(make_ctx(routes=bad), min_collectors=1)


def test_registered_daily():
    assert SOURCES["routeviews_collectors"].ttl_seconds == 86_400
