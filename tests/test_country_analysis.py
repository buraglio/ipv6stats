from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "country-analysis" / "index.html").read_text()


def test_map_and_geography_file(tmp_path):
    out, html = render(tmp_path)
    assert "ISO-3" in html
    assert "../static/topojson/" in html
    assert (out / "static" / "topojson" / "world_110m.json").is_file()


def test_index_links_every_economy(tmp_path):
    _, html = render(tmp_path)
    index = html[html.index("All economies"):]
    for slug in ("bl", "de", "fr", "us"):
        assert f'href="../country/{slug}/"' in index


def test_leaders_regions_and_nist(tmp_path):
    _, html = render(tmp_path)
    leaders = html[html.index("<h3>Leaders</h3>"):html.index("<h3>By region</h3>")]
    assert leaders.index("France") < leaders.index("Germany")   # the map's data lists codes in another order
    assert "Americas" in html
    assert "2 of 4" in html                      # NIST web-operational domains
    assert 'href="../country/us/"' in html


def test_without_apnic(tmp_path):
    _, html = render(tmp_path, omit=("apnic",))
    assert "— source unavailable" in html
    assert "Plotly.newPlot" not in html
