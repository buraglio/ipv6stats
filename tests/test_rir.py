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


RIPE_SAMPLE = """2|ripencc|1791928799|167536|19700101|20261013|+0200
ripencc|*|ipv6|*|26850|summary
ripencc|NL|ipv6|2001:600::|29|19990826|allocated
ripencc|DE|ipv6|2001:608::|32|20030812|allocated
ripencc|DE|ipv6|2001:609::|48||assigned
"""


def test_file_date_comes_from_end_date_not_serial():
    # RIPE's serial is a Unix timestamp; reading it as YYYYMMDD gave "1791-92-87".
    assert rir.parse_delegations(RIPE_SAMPLE, "ripencc", rir.URLS["ripencc"])["file_date"] == "2026-10-13"


def test_by_country_and_history():
    parsed = rir.parse_delegations(RIPE_SAMPLE, "ripencc", rir.URLS["ripencc"])
    assert parsed["by_country"] == {"DE": 1.0, "NL": 8.0}  # DE: /32 + /48 rounds to 1.0
    # The undated /48 counts in the totals but not in the dated history.
    assert parsed["history"] == [{"year": 1999, "blocks_32": 8.0}, {"year": 2003, "blocks_32": 9.0}]


def test_arin_extended_format():
    text = ("2.3|arin|1791982821510|204020|19700101|20261014|-0400\n"
            "arin|US|ipv6|2001:400::|32|19990803|allocated|04f048163e37eef48d891498545eefc0\n"
            "arin||ipv6|2001:4:113::|48||available|\n")
    parsed = rir.parse_delegations(text, "arin", rir.URLS["arin"])
    assert parsed["file_date"] == "2026-10-14"
    assert parsed["by_country"] == {"US": 1.0}


def test_rejects_bad_end_date():
    text = "2|ripencc|1|1|19700101|garbage|+0200\nripencc|DE|ipv6|2001:608::|32|20030812|allocated\n"
    with pytest.raises(ValueError, match="format changed"):
        rir.parse_delegations(text, "ripencc", rir.URLS["ripencc"])


def test_all_five_registered():
    for key in ("afrinic_delegations", "apnic_delegations", "arin_delegations",
                "lacnic_delegations", "ripe_delegations"):
        assert key in SOURCES
