import pytest

from collect.registry import SOURCES
from collect.sources import ipv6matrix as m
from tests.fakes import FakeResponse, make_ctx

BODY = {
    "Sat Aug 21 2010 00:00:00 GMT+0000 (Coordinated Universal Time)": {"US": {"hosts": 100, "hosts6": 1}},
    "Sun Oct 04 2026 00:00:00 GMT+0000 (Coordinated Universal Time)": {
        "US": {"hosts": 1000, "hosts6": 600}, "DE": {"hosts": 500, "hosts6": 200}, "A1": {"hosts": 50, "hosts6": 0}},
}


def test_parse_latest_crawl_and_series():
    p = m.parse(BODY)
    assert p["latest"] == {"date": "2026-10-04", "hosts": 1550, "hosts_ipv6": 800, "share": 51.6}
    assert [s["date"] for s in p["series"]] == ["2010-08-21", "2026-10-04"]
    assert [c["code"] for c in p["countries"]] == ["US", "DE"]          # A1 (anonymous proxy) left out
    assert p["countries"][0]["share"] == 60.0


def test_matrix_rejects_changed_format():
    with pytest.raises(ValueError, match="IPv6 Matrix format changed"):
        m.parse({"results": []})


def test_fetch():
    assert SOURCES["ipv6matrix_hosts"].fetch(make_ctx(routes={m.URL: FakeResponse(json_data=BODY)}))["latest"]
