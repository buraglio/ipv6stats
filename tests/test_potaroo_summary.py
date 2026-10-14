from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import potaroo_summary as ps
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "bgp" / "v6-index.html").read_text(encoding="utf-8", errors="ignore")


def stat(stem, value, label="x"):
    return f'<a href="/cgi-bin/plota">{label}</a></td><td><b><a href="{stem}.txt" target="text">{value}</a></b></td>'


ALL = "".join(stat(stem, i + 1) for i, stem in enumerate(ps.WANTED)) + "".join(
    stat(f"bgp-prefix-{n}", n * 10) + stat(f"bgp-p-prefix-{n}", n / 10) for n in range(32, 49))


def test_parse_sample():
    parsed = ps.parse(ALL)
    assert parsed["stats"]["fib_entries"] == 1 and isinstance(parsed["stats"]["fib_entries"], int)
    assert parsed["prefix_lengths"][-1] == {"length": 48, "prefixes": 480, "share": 4.8}


def test_parse_recorded_page():
    parsed = ps.parse(FIXTURE)
    assert parsed["stats"]["unique_ases"] > 10_000
    assert 30 < parsed["stats"]["average_prefix_length"] < 64
    assert any(r["length"] == 48 and r["prefixes"] > 0 for r in parsed["prefix_lengths"])


def test_summary_rejects_missing_statistics():
    with pytest.raises(ValueError, match="Potaroo report format changed"):
        ps.parse(ALL.replace("bgp-as-count.txt", "bgp-ases.txt"))


def test_fetch():
    assert SOURCES["bgp_v6_summary"].fetch(make_ctx(routes={ps.URL: FakeResponse(text=FIXTURE)}))["stats"]
