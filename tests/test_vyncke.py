from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import vyncke
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "vyncke" / "ipv6status.html").read_text(encoding="utf-8")


def table(title, rows):
    body = "".join(
        f'<tr><td>{i}<td><a href=detailed.php?country={cc}><img class="flag-{cc}" src="/flags/flags-sprite.png" border=0> {name}</a>\n'
        f"\t<td align=right>50\n\t<td align=right>{weighted}%\n\t<td align=right>{green}% (17)\n\t<td align=right>0.0% (0)\n"
        for i, (cc, name, weighted, green) in enumerate(rows, 1))
    return f'<h3>{title} (Umbrella)</h3>\n<table class="table"><tbody>\n{body}</tbody>\n  </table>'


SAMPLE = (table("Web", [("no", "Norway", "55.54", "68.0"), ("uk", "United-Kingdom", "66.14", "34.0"),
                        ("eu", "European Union", "42.24", "40.0")])
          + table("Email", [("no", "Norway", "56.72", "70.0")])
          + table("DNS", [("de", "Germany", "91.75", "98.0")]))


def test_parse_sample():
    parsed = vyncke.parse(SAMPLE, min_rows=1)
    assert parsed["web"][0] == {"code": "NO", "name": "Norway", "sites": 50, "weighted_pct": 55.54, "green_pct": 68.0}
    assert parsed["dns"][0]["code"] == "DE"


def test_uk_maps_to_gb_and_eu_is_dropped():
    codes = [r["code"] for r in vyncke.parse(SAMPLE, min_rows=1)["web"]]
    assert codes == ["NO", "GB"]


def test_parse_recorded_page():
    parsed = vyncke.parse(FIXTURE)
    for service in vyncke.SERVICES:
        assert len(parsed[service]) >= vyncke.MIN_ROWS
    assert "US" in {r["code"] for r in parsed["web"]}


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="Vyncke page format changed"):
        vyncke.parse("<html>redesigned</html>")


def test_fetch():
    ctx = make_ctx(routes={vyncke.URL: FakeResponse(text=FIXTURE)})
    assert SOURCES["vyncke"].fetch(ctx)["web"]


def test_row_without_flag_keeps_its_own_country():
    # A row missing its flag image must not swallow the next row's name and numbers.
    page = SAMPLE.replace('<img class="flag-no" src="/flags/flags-sprite.png" border=0> ', "", 1)
    web = vyncke.parse(page, min_rows=1)["web"]
    assert web[0]["code"] == "NO" and web[0]["name"] == "Norway" and web[0]["green_pct"] == 68.0
    assert [r["code"] for r in web] == ["NO", "GB"]
