from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "extended-data-sources" / "index.html").read_text()


def test_domains_and_dns(tmp_path):
    _, html = render(tmp_path)
    assert "1,421 of 1,437" in html and "51,978,468" in html and "315,029,019" in html


def test_old_zone_data_is_flagged(tmp_path):
    _, html = render(tmp_path)
    row = html[html.index("<td>de</td>"):html.index("</tr>", html.index("<td>de</td>"))]
    assert "zone data from 2010-01-20" in row


def test_routing_security_and_measurement(tmp_path):
    _, html = render(tmp_path)
    for text in ("73.2%", "64.8%", "94.2%", "34.9%", "157,946", "7,075 of 15,265", "21,723 of 35,630", "54.7%"):
        assert text in html, text


def test_access_networks_join_apnic(tmp_path):
    _, html = render(tmp_path)
    nets = html[html.index("Access networks"):]
    assert "Comcast" in nets and "85.3%" in nets                   # AS7922 is in the US network table
    assert "not among APNIC" in nets                               # e.g. T-Mobile isn't in the sample


def test_government_and_registries(tmp_path):
    _, html = render(tmp_path)
    assert "1 of 2" in html and "nasa.gov" in html
    assert "RIPE NCC" in html and "DE" in html


def test_routing_security_unavailable_without_key(tmp_path):
    _, html = render(tmp_path, not_configured=("isoc_routing",))
    sec = html[html.index("Routing security"):html.index("Measurement networks")]
    assert "— source unavailable" in sec


def test_nav_and_legacy(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">Extended Data Sources' in html
    assert '"Extended Data Sources": "extended-data-sources/"' in (out / "index.html").read_text()
