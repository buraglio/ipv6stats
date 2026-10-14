from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out


def page(out, slug):
    return (out / "country" / slug / "index.html").read_text()


def test_a_page_per_economy(tmp_path):
    out = render(tmp_path)
    assert sorted(p.name for p in (out / "country").iterdir()) == ["bl", "de", "fr", "us"]


def test_us_page(tmp_path):
    html = page(render(tmp_path), "us")
    assert "<title>United States of America · IPv6 Global Statistics</title>" in html
    for text in ("61.9%", "59.9%", "57.2%", "50.0%", "52.0%", "92.0%", "60,000", "ARIN", "COMCAST-7922"):
        assert text in html, text
    assert html.count("Plotly.newPlot") == 1                  # history chart
    assert 'aria-current="page">Country Analysis' in html
    assert 'href="../../static/site.css"' in html


def test_us_page_has_nist_and_dated_reference(tmp_path):
    html = page(render(tmp_path), "us")
    assert "Department of Justice" in html
    assert "OMB memorandum M-21-07" in html
    assert "Reference — last reviewed 2026-10-14" in html
    assert "Department of Justice" not in page(render(tmp_path / "b"), "fr")


def test_country_in_missing_list_says_unavailable(tmp_path):
    html = page(render(tmp_path), "de")
    assert "History for this economy could not be fetched" in html
    assert "Plotly.newPlot" not in html


def test_country_without_other_sources_renders(tmp_path):
    html = page(render(tmp_path), "bl")
    assert "97.1%" in html
    assert "collected for the 50 economies with the most APNIC samples" in html
    assert html.count("—") >= 1

