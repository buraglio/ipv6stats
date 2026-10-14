import pytest

from collect.registry import SOURCES
from collect.sources import rir
from tests.fakes import FakeResponse, make_ctx

SAMPLE = """# comment line
2|lacnic|20261013|50084|19870101|20261013|-0300
lacnic|*|ipv6|*|13570|summary
lacnic|MX|ipv6|2001:1200::|32|20030110|allocated
lacnic|MX|ipv6|2001:1201::|44|20190404|assigned
lacnic|BR|ipv6|2804::|29|20100101|allocated
lacnic|BR|ipv6|2804:8::|32|20100101|reserved
lacnic|GT|ipv4|2.152.0.0|1024|20260714|allocated
"""


def test_parse_counts_32_equivalents():
    parsed = rir.parse_delegations(SAMPLE, "lacnic", rir.LACNIC_URL)
    assert parsed["file_date"] == "2026-10-13"
    assert parsed["total_blocks_32"] == 9.0  # 8 (/29) + 1 (/32) + 1/4096 (/44)
    assert parsed["countries"] == 2
    assert parsed["top_countries"][0] == {"code": "BR", "blocks_32": 8.0, "share": 88.89}
    assert parsed["top_countries"][1]["code"] == "MX"
    assert parsed["url"] == rir.LACNIC_URL


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="lacnic delegation file format changed"):
        rir.parse_delegations("<html>not found</html>", "lacnic", rir.LACNIC_URL)


def test_fetch_afrinic():
    text = "2|afrinic|20261014|10025|00000000|20261014|00000\nafrinic|ZA|ipv6|2c0f::|32|20100101|allocated\n"
    ctx = make_ctx(routes={rir.AFRINIC_URL: FakeResponse(text=text)})
    parsed = SOURCES["afrinic_delegations"].fetch(ctx)
    assert parsed["file_date"] == "2026-10-14"
    assert parsed["countries"] == 1


def test_isoc_is_opt_in():
    assert SOURCES["isoc_pulse"].requires_env == ("ISOC_PULSE_API_KEY",)


def test_isoc_with_key_reports_missing_client():
    with pytest.raises(NotImplementedError, match="ISOC Pulse API client"):
        SOURCES["isoc_pulse"].fetch(make_ctx(env={"ISOC_PULSE_API_KEY": "k"}))
