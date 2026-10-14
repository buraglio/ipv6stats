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
    assert len(parsed["countries"]) == 2  # Anguilla's row has no data


def test_parse_recorded_file():
    codes = {c["code"] for c in sixlab.parse(FIXTURE)["countries"]}
    assert {"US", "FR", "IN"} <= codes


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="6lab users.js format changed"):
        sixlab.parse("<html>404</html>")


def test_fetch():
    ctx = make_ctx(routes={sixlab.URL: FakeResponse(text=FIXTURE)})
    assert SOURCES["cisco_6lab"].fetch(ctx)["countries"]


def test_rows_without_data_are_left_out():
    # 6lab lists some territories as 0.0,0.0,0.0: no data, not zero IPv6 users.
    codes = [c["code"] for c in sixlab.parse(SAMPLE, min_countries=1)["countries"]]
    assert codes == ["US", "AE"]
