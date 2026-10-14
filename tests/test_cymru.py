from datetime import datetime, timezone
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import cymru
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "cymru" / "fullbogons-ipv6.txt").read_text()
SAMPLE = "# last updated 1791996901 (Wed Oct 14 16:55:01 2026 GMT)\n# Know your network!\n::/10\n100::/8\n"


def test_parse_sample():
    assert cymru.parse(SAMPLE, min_prefixes=1) == {"prefixes": 2, "updated": "2026-10-14", "url": cymru.HOME}


def test_parse_recorded_file():
    assert cymru.parse(FIXTURE)["prefixes"] > 1000


def test_bogons_reject_non_prefix_lines():
    with pytest.raises(ValueError, match="not a prefix"):
        cymru.parse(SAMPLE + "<html>error</html>\n", min_prefixes=1)


def test_rejects_stale_list():
    with pytest.raises(ValueError, match="stopped updating"):
        cymru.parse(SAMPLE, now=datetime(2026, 10, 20, tzinfo=timezone.utc), min_prefixes=1)


def test_fetch():
    assert SOURCES["cymru_bogons"].fetch(make_ctx(routes={cymru.URL: FakeResponse(text=FIXTURE)}))["prefixes"]
