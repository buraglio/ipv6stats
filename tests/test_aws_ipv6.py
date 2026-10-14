from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import aws_ipv6
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "aws" / "aws-ipv6-support.html").read_text(encoding="utf-8")


def row(*cells):
    return "<tr>" + "".join(f'<td tabindex="-1">{c}</td>' for c in cells) + "</tr>"


SAMPLE = ("<table><thead><tr><th>Service name</th></tr></thead>"
          + row("AWS Amplify", "Yes", "No", "Yes", "")
          + row("Amazon EC2", "Yes", "Partial", "Yes", "Yes") + "</table>")


def test_parse_sample():
    parsed = aws_ipv6.parse(SAMPLE, min_services=1)
    assert parsed["services"][0] == {"name": "AWS Amplify", "dual_stack": "yes", "ipv6_only": "no",
                                     "public_endpoints": "yes", "private_endpoints": None}
    assert parsed["counts"]["ipv6_only"] == {"yes": 0, "partial": 1, "no": 1}
    assert parsed["total"] == 2


def test_parse_recorded_page():
    parsed = aws_ipv6.parse(FIXTURE)
    assert parsed["total"] >= aws_ipv6.MIN_SERVICES
    assert parsed["counts"]["dual_stack"]["yes"] > 0


def test_rejects_unexpected_value():
    with pytest.raises(ValueError, match="AWS IPv6 table format changed"):
        aws_ipv6.parse(SAMPLE.replace(">Partial<", ">Coming soon<"), min_services=1)


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="AWS IPv6 table format changed"):
        aws_ipv6.parse("<html>moved</html>")


def test_fetch():
    assert SOURCES["aws_ipv6_services"].fetch(make_ctx(routes={aws_ipv6.URL: FakeResponse(text=FIXTURE)}))["total"]
