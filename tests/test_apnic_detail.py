from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import apnic, apnic_detail
from tests.fakes import FakeResponse, make_ctx

FIXTURES = Path(__file__).parent / "fixtures" / "apnic"
MAIN = (FIXTURES / "ipv6.html").read_text(encoding="utf-8")
US = (FIXTURES / "economy-US.html").read_text(encoding="utf-8")

SAMPLE = r"""
      [new Date('2026-10-05'),60.1,58.0],
      [new Date('2026-10-06'),60.2,58.1],
      [new Date('2026-10-12'),61.0,59.0],
      [new Date('2026-10-03'),3498874],
["<a href=\"//stats.labs.apnic.net/ipv6/AS7922?c=US&p=1&v=1&w=30&x=1\">AS7922</a>","COMCAST-7922 - Comcast Cable Communications, LLC",{v: 85.28, f:'x'},{v: 83.59, f: 'x'},16629912],
["<a href=\"//stats.labs.apnic.net/ipv6/AS7018?c=US&p=1&v=1&w=30&x=1\">AS7018</a>","ATT-INTERNET4 - AT&amp;T \"Enterprises\", LLC",{v: 85.95, f:'x'},{v: 84.0, f: 'x'},20000000],
["<a href=\"//stats.labs.apnic.net/ipv6/AS7922?c=US&p=1&v=1&w=30&x=1\">AS7922</a>","dup",{v: 1.0, f:'x'},{v: 1.0, f: 'x'},1],
"""


def test_parse_economy_sample():
    parsed = apnic_detail.parse_economy(SAMPLE)
    # 2026-10-05 and -06 are the same ISO week (keep the later); -12 is the next week
    assert parsed["history"] == [{"date": "2026-10-06", "capable": 60.2, "preferred": 58.1},
                                 {"date": "2026-10-12", "capable": 61.0, "preferred": 59.0}]
    assert [n["asn"] for n in parsed["networks"]] == [7018, 7922]  # by samples, first copy kept
    assert parsed["networks"][0]["name"] == 'ATT-INTERNET4 - AT&T "Enterprises", LLC'


def test_parse_recorded_page():
    parsed = apnic_detail.parse_economy(US)
    assert len(parsed["history"]) >= 52
    assert parsed["networks"] and isinstance(parsed["networks"][0]["asn"], int)
    assert len(parsed["networks"]) <= apnic_detail.TOP_NETWORKS


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="APNIC economy page format changed"):
        apnic_detail.parse_economy("<html>redesigned</html>")


def top_codes(n):
    ranked = sorted(apnic.parse(MAIN)["economies"], key=lambda e: e["samples"], reverse=True)
    return [e["code"] for e in ranked[:n]]


def test_fetch_top_economies(monkeypatch):
    monkeypatch.setattr(apnic_detail, "TOP_ECONOMIES", 2)
    codes = top_codes(2)
    routes = {f"{apnic.URL}{c}": FakeResponse(text=US) for c in codes}
    routes[apnic.URL] = FakeResponse(text=MAIN)  # last: it is a prefix of every economy URL
    result = SOURCES["apnic_economy_detail"].fetch(make_ctx(routes=routes))
    assert sorted(result["economies"]) == sorted(codes)
    assert result["missing"] == []


def test_fetch_tolerates_a_few_failed_pages(monkeypatch):
    monkeypatch.setattr(apnic_detail, "TOP_ECONOMIES", 2)
    first, second = top_codes(2)
    routes = {f"{apnic.URL}{first}": FakeResponse(text=US), f"{apnic.URL}{second}": FakeResponse(status_code=503),
              apnic.URL: FakeResponse(text=MAIN)}
    monkeypatch.setattr(apnic_detail, "MAX_MISSING", 1)
    assert SOURCES["apnic_economy_detail"].fetch(make_ctx(routes=routes))["missing"] == [second]
    monkeypatch.setattr(apnic_detail, "MAX_MISSING", 0)
    with pytest.raises(ValueError, match="economy pages failed"):
        SOURCES["apnic_economy_detail"].fetch(make_ctx(routes=routes))
