from pathlib import Path

import pytest

from collect.registry import DAY, SOURCES
from collect.sources import bgp
from tests.fakes import FakeResponse, make_ctx

FIXTURE = Path(__file__).parent / "fixtures" / "bgp" / "bgp-active.txt"

# 1791936000 = 2026-10-14T00:00Z, 1791979200 = 2026-10-14T12:00Z, 1792022400 = 2026-10-15T00:00Z
SAMPLE = """1791979200 258100
1791936000 258000
not a data line
1792022400 258600
"""


def test_parse_keeps_last_sample_per_day_even_out_of_order():
    parsed = bgp.parse(SAMPLE, min_days=1)
    assert parsed["daily"] == [{"date": "2026-10-14", "prefixes": 258100},
                               {"date": "2026-10-15", "prefixes": 258600}]
    assert parsed["current"] == 258600
    assert parsed["current_at"] == "2026-10-15T00:00:00+00:00"
    assert parsed["url"] == bgp.PAGE


def test_parse_recorded_file():
    lines = [line.split() for line in FIXTURE.read_text().splitlines() if line.strip()]
    newest = max(lines, key=lambda parts: int(parts[0]))
    parsed = bgp.parse(FIXTURE.read_text())
    assert len(parsed["daily"]) >= 365
    assert parsed["current"] == int(newest[1])


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="Potaroo"):
        bgp.parse("<html>moved</html>")


def test_registered_daily():
    assert SOURCES["bgp_v6_table"].ttl_seconds == DAY


def test_fetch():
    ctx = make_ctx(routes={bgp.URL: FakeResponse(text=FIXTURE.read_text())})
    assert SOURCES["bgp_v6_table"].fetch(ctx)["current"] > 0
