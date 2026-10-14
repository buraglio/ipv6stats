import pytest

from collect.registry import SOURCES
from collect.sources import nist
from tests.fakes import FakeResponse, make_ctx

# Three rows copied from the live page's markup: a normal row, a row whose agency is a
# link with ANTD-7 grey cells, and an italic (greyed-out) domain.
ROWS = (
    '<TR align=center><TD align=left><ANTD-0><a href="https://www.abmc.gov">gov.abmc.</a></TD>'
    '<TD><ANTD-9>American Battle Monuments Commission</TD>'
    '<TD BGCOLOR=#00A000><ANTD-8>[3] 9/9/8 [O]</TD><TD BGCOLOR=#00A000><ANTD-8>[1] 4/4/4 [O]</TD>'
    '<TD BGCOLOR=#00A000><ANTD-8>[1] 1/1/1 [O]</TD><TD BGCOLOR=#DDDDDD></TD>'
    '<TR align=center><TD align=left><ANTD-0><a href="https://www.18f.gov">gov.18f.</a></TD>'
    '<TD><ANTD-9><a href=../cgi-bin/cfo?gsa>General Services Administration</a></TD>'
    '<TD BGCOLOR=#00A000><ANTD-8>[4] 4/0/4 [O]</TD><TD BGCOLOR=#999999><ANTD-7>[0] 0/0/0 [-]</TD>'
    '<TD BGCOLOR=#999999><ANTD-7>[0] 0/0/0 [-]</TD><TD BGCOLOR=#DDDDDD></TD>'
    '<TR align=center><TD BGCOLOR=#DDDDDD align=left><ANTD-0><i>gov.budgetlob.</i></TD>'
    '<TD><ANTD-9><a href=../cgi-bin/cfo?education>Department of Education</a></TD>'
    '<TD BGCOLOR=#D00000><ANTD-8>[S] 0/0/0 [L]</TD><TD BGCOLOR=#999999><ANTD-7>[0] 0/0/0 [-]</TD>'
    '<TD BGCOLOR=#FFFF00><ANTD-8>[1] 1/0/0 [P]</TD><TD BGCOLOR=#DDDDDD></TD>'
)


def test_parse_counts_by_service_and_agency():
    parsed = nist.parse(ROWS, min_domains=1)
    assert parsed["domains"] == 3
    assert parsed["totals"]["web"] == {"operational": 1, "not_applicable": 1, "in_progress": 1}
    assert parsed["totals"]["dns"] == {"operational": 2, "none": 1}
    assert [a["name"] for a in parsed["agencies"]] == [
        "American Battle Monuments Commission", "Department of Education", "General Services Administration"]
    assert parsed["agencies"][0]["web"] == {"operational": 1}


def test_rejects_unknown_color():
    with pytest.raises(ValueError, match="NIST page format changed"):
        nist.parse(ROWS.replace("#FFFF00", "#123456"), min_domains=1)


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="NIST page format changed"):
        nist.parse("<html>maintenance</html>")


def test_fetch():
    ctx = make_ctx(routes={nist.URL: FakeResponse(text=ROWS)})
    with pytest.raises(ValueError):  # three rows are below MIN_DOMAINS
        SOURCES["nist_usgv6"].fetch(ctx)
