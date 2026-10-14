from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return (out / "overview" / "index.html").read_text()


def test_headline_numbers_come_from_data(tmp_path):
    html = render(tmp_path)
    assert '<div class="metric-value">47.7%</div>' in html      # consensus
    assert '<div class="metric-value">38.4%</div>' in html      # Cloudflare
    assert '<div class="metric-value">258,009</div>' in html    # BGP prefixes
    assert "+27,009 in the past year" in html
    assert '<div class="metric-value">61.2%</div>' in html      # Tranco sites
    assert "Economies ≥ 50% IPv6-capable" in html
    assert '<div class="metric-value">2</div>' in html
    assert "3 of 3 sources" in html


def test_removed_static_claims_are_gone(tmp_path):
    html = render(tmp_path)
    for text in ["228,789", "49%", "12%", "IPv6-only Support", "Facebook", "Mobile Leadership",
                 "US Milestone", "25+", "France (80%)", "13.2%"]:
        assert text not in html, text


def test_trends_use_ranked_economies_and_regions(tmp_path):
    html = render(tmp_path)
    assert "France" in html and "85.6%" in html
    assert "United States of America" in html and "61.9%" in html
    assert "Saint Barthelemy" not in html
    assert "Unclassified" not in html
    assert html.index("Americas") < html.index("Europe")


def test_updates_and_insights_are_generated(tmp_path):
    html = render(tmp_path)
    assert "+3,009" in html                      # BGP change in the last 30 days
    assert "31,250" in html and "2026-10-13" in html   # LACNIC total and file date
    assert "11,300" in html and "54 economies" in html  # AFRINIC
    assert "+17.6 points" in html                # Tranco 61.2 minus APNIC 43.6


def test_missing_source_shows_unavailable(tmp_path):
    html = render(tmp_path, omit=("cloudflare_ip_version",))
    assert "— source unavailable" in html
    assert '<div class="metric-value">52.4%</div>' in html
    assert "2 of 3 sources" in html


def test_empty_data_dir_still_builds(tmp_path):
    out = tmp_path / "dist"
    build(tmp_path / "no-data-yet", out, NOW)
    html = (out / "overview" / "index.html").read_text()
    assert html.count("— source unavailable") >= 5


def test_stale_source_is_marked(tmp_path):
    html = render(tmp_path, last_success={"bgp_v6_table": "2026-10-10T00:05:00+00:00"})
    assert "stale since 2026-10-10" in html


def test_freshness_table_lists_opt_in_source(tmp_path):
    html = render(tmp_path)
    assert "Internet Society Pulse API" in html
    assert "not configured" in html
    assert "ISOC_PULSE_API_KEY" in html


def test_charts_render(tmp_path):
    html = render(tmp_path)
    assert html.count("Plotly.newPlot") == 2
