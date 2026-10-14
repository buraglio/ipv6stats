from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import sixlab
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "sixlab" / "users.js").read_text(encoding="utf-8")

SAMPLE = """var UsersData = {
  data: [
["US", "United States of America",0.546,1.36532176E8,57.2],
["AE", "United Arab Emirates",0.41799998,4121796.5,30.7],
["AI", "Anguilla",0.0,0.0,0.0],
"""


def test_parse_sample_uses_last_column():
    parsed = sixlab.parse(SAMPLE, min_countries=1)
    assert parsed["countries"][0] == {"code": "US", "name": "United States of America", "ipv6_users_pct": 57.2}
    assert len(parsed["countries"]) == 3


def test_parse_recorded_file():
    codes = {c["code"] for c in sixlab.parse(FIXTURE)["countries"]}
    assert {"US", "FR", "IN"} <= codes


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="6lab users.js format changed"):
        sixlab.parse("<html>404</html>")


def test_fetch():
    ctx = make_ctx(routes={sixlab.URL: FakeResponse(text=FIXTURE)})
    assert SOURCES["cisco_6lab"].fetch(ctx)["countries"]
