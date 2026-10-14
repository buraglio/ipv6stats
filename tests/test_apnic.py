from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import apnic
from tests.fakes import FakeResponse, make_ctx

FIXTURE = Path(__file__).parent / "fixtures" / "apnic" / "ipv6.html"

# Three rows in the page's real format: world, a region, an economy.
SAMPLE = r"""
["<a href=\"/ipv6/XA\">XA</a>","<a href=\"/ipv6/XA\">World</a>",{v: 43.65, f:'x'}, {v: 41.02, f: 'x'},972331706]
["<a href=\"/ipv6/XE\">XE</a>","<a href=\"/ipv6/XE\">Europe</a>",{v: 36.87, f:'x'}, {v: 35.72, f: 'x'},134455991]
["<a href=\"/ipv6/CI\">CI</a>","<a href=\"/ipv6/CI\">C&ocirc;te d&#39;Ivoire</a>, <a href=\"/ipv6/XB\">Africa</a>",{v: 1.50, f:'x'}, {v: 1.25, f: 'x'},123456]
["<a href=\"/ipv6/XA\">XA</a>","<a href=\"/ipv6/XA\">World</a>",{v: 99.99, f:'x'}, {v: 99.99, f: 'x'},1]
"""


def test_parse_sample_rows():
    parsed = apnic.parse(SAMPLE, min_economies=1)
    assert parsed["world"] == {"code": "XA", "name": "World", "capable": 43.65,
                               "preferred": 41.02, "samples": 972331706}
    assert [r["name"] for r in parsed["regions"]] == ["Europe"]
    assert parsed["economies"] == [{"code": "CI", "name": "Côte d'Ivoire", "capable": 1.5,
                                    "preferred": 1.25, "samples": 123456}]
    assert parsed["url"] == apnic.URL


def test_parse_recorded_page():
    parsed = apnic.parse(FIXTURE.read_text(encoding="utf-8"))
    assert parsed["world"]["name"] == "World"
    assert 0 < parsed["world"]["capable"] < 100
    assert len(parsed["economies"]) >= 100
    assert "US" in {r["code"] for r in parsed["economies"]}
    assert "Europe" in {r["name"] for r in parsed["regions"]}


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="APNIC page format changed"):
        apnic.parse("<html><body>redesigned</body></html>")


def test_fetch_uses_page():
    ctx = make_ctx(routes={apnic.URL: FakeResponse(text=FIXTURE.read_text(encoding="utf-8"))})
    assert SOURCES["apnic"].fetch(ctx)["world"]["code"] == "XA"


def test_fetch_http_error_raises():
    ctx = make_ctx(routes={apnic.URL: FakeResponse(status_code=503)})
    with pytest.raises(Exception, match="503"):
        SOURCES["apnic"].fetch(ctx)
