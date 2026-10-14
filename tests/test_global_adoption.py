from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "global-adoption" / "index.html").read_text()


def test_headline_numbers(tmp_path):
    _, html = render(tmp_path)
    assert '<div class="metric-value">47.7%</div>' in html          # consensus
    assert '<div class="metric-value">85.6%</div>' in html          # highest capability
    assert "France" in html
    assert '<div class="metric-value">171,550</div>' in html        # five RIRs
    assert "5 of 5 registries" in html


def test_top_table_joins_sources(tmp_path):
    _, html = render(tmp_path)
    table = html[html.index("Top economies"):html.index("Address allocations")]
    assert table.index("France") < table.index("United States of America") < table.index("Germany")
    assert "39.0%" in table and "44.0%" in table and "57.2%" in table
    assert 'href="../country/fr/"' in table
    assert "Saint Barthelemy" not in table


def test_missing_optional_source_shows_dash(tmp_path):
    _, html = render(tmp_path, omit=("cisco_6lab",))
    table = html[html.index("Top economies"):html.index("Address allocations")]
    assert "—" in table and "57.2%" not in table


def test_rir_and_website_sections(tmp_path):
    _, html = render(tmp_path)
    assert "RIPE NCC" in html and "52,000" in html
    assert html.count("Plotly.newPlot") >= 2   # regions bar + RIR growth
    sites = html[html.index("Websites on IPv6"):]
    assert sites.index("United States of America") < sites.index("France")


def test_nav_and_legacy_redirect(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">Global Adoption' in html
    assert '"Global Adoption": "global-adoption/"' in (out / "index.html").read_text()


def test_global_adoption_without_any_data(tmp_path):
    out = tmp_path / "dist"
    build(tmp_path / "no-data", out, NOW)
    assert "— source unavailable" in (out / "global-adoption" / "index.html").read_text()
