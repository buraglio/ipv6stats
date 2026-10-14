from tests.sample_data import NOW, write_sample_data
from web.build import build


def render(tmp_path, **kwargs):
    out = tmp_path / "dist"
    build(write_sample_data(tmp_path / "data", **kwargs), out, NOW)
    return out, (out / "cloud-services" / "index.html").read_text()


def test_comparison_table_joins_measured_and_reference(tmp_path):
    _, html = render(tmp_path)
    table = html[html.index("Provider comparison"):html.index("AWS services")]
    assert "Mythic Beasts" in table and "Fly.io" in table        # every reference provider listed
    assert "2 of 6" in table                                      # AWS hostnames with IPv6
    assert "6,944 IPv6 / 10,628 IPv4" in table                    # AWS published prefixes
    assert "0 IPv6 / 900 IPv4" in table                           # Oracle


def test_aws_service_summary(tmp_path):
    _, html = render(tmp_path)
    aws = html[html.index("AWS services"):]
    assert "2 of 2 services" in aws and "Amazon EC2" in aws


def test_provider_reference_shows_review_date(tmp_path):
    _, html = render(tmp_path)
    assert html.count("Reference — last reviewed 2025-10-04") == 23


def test_no_grades(tmp_path):
    _, html = render(tmp_path)
    assert "Grade" not in html   # lowercase "grade" can appear legitimately, e.g. in "upgrade"


def test_hostname_statuses_listed(tmp_path):
    _, html = render(tmp_path)
    assert "console.aws.amazon.com" in html and "IPv4 only" in html


def test_without_measured_sources(tmp_path):
    _, html = render(tmp_path, omit=("cloud_endpoints", "aws_ipv6_services", "ip_ranges_aws", "ip_ranges_oracle"))
    assert "— source unavailable" in html
    assert "Mythic Beasts" in html                                # reference still shown


def test_nav_and_legacy(tmp_path):
    out, html = render(tmp_path)
    assert 'aria-current="page">Cloud Services' in html
    assert '"Cloud Services": "cloud-services/"' in (out / "index.html").read_text()


def test_missing_service_fields_render_as_dash(tmp_path):
    _, html = render(tmp_path)
    assert "<td>None</td>" not in html
