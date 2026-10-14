from tests.sample_data import NOW, write_sample_data
from web.build import build
from web.format import format_value


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "bgp-statistics" / "index.html").read_text()


def test_decimal_format():
    assert format_value(4.9156, "decimal") == "4.92"


def test_headline_numbers(tmp_path):
    _, html = render(tmp_path)
    for text in ("258,009", "+27,009 in the past year", "37,751", "+2,751 in the past year", "42.99", "4.92"):
        assert text in html, text


def test_prefix_lengths_and_aggregation(tmp_path):
    _, html = render(tmp_path)
    assert "/48" in html and "121,568" in html and "47.0%" in html
    agg = html[html.index("could shrink the table most"):]
    assert "AS9808" in agg and "CHINAMOBILE-CN" in agg and "AS7552" in agg and "2026-10-14" in agg


def test_routeviews_and_charts(tmp_path):
    _, html = render(tmp_path)
    assert "route-views.wide" in html and "255,106" in html
    assert html.count("Plotly.newPlot") == 3   # table size, AS count, prefix lengths


def test_without_new_sources(tmp_path):
    _, html = render(tmp_path, omit=("bgp_v6_summary", "cidr_report_aggregation", "routeviews_collectors", "bgp_v6_ases"))
    assert html.count("— source unavailable") >= 4


def test_nav_and_legacy(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">BGP Statistics' in html
    assert '"BGP Statistics": "bgp-statistics/"' in (out / "index.html").read_text()
