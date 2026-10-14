from datetime import datetime, timezone
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import he_report as he
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "he" / "ipv6-progress-report.html").read_text(encoding="utf-8", errors="ignore")
SAMPLE = """Root Zone Processed: Wed Oct 14 10:14:04 2026
<br>Top Level Domains (TLDs): 1437
<br>TLDs with IPv6 nameservers: 1421
<br>TLDs with nameservers with IPv6 glue in the root zone: 1419
<pre>
                     TLD   domains         A      AAAA    A-glue AAAA-glue                downloaded                   processed
                     com 167590972 147699636  30785986   1555630     32630  (Wed Oct 14 03:48:52 2026)  (Wed Oct 14 10:13:27 2026)
                      de  13155766   6375832   2330359    398186       114  (Wed Jan 20 01:22:39 2010)  (Wed Oct 14 10:13:40 2026)
                   total 180746738 154075468  33116345   1953816     32744
</pre>"""


def test_parse_sample():
    p = he.parse(SAMPLE, min_rows=1)
    assert (p["tlds"], p["tlds_ipv6_ns"], p["tlds_ipv6_glue"]) == (1437, 1421, 1419)
    assert p["root_zone_processed"] == "2026-10-14"
    assert p["domains"] == {"domains": 180746738, "a": 154075468, "aaaa": 33116345, "a_glue": 1953816, "aaaa_glue": 32744}
    assert p["top_tlds"][1] == {"tld": "de", "domains": 13155766, "aaaa": 2330359, "downloaded": "2010-01-20"}


def test_parse_recorded_page():
    p = he.parse(FIXTURE)
    assert p["domains"]["aaaa"] > 1_000_000 and len(p["top_tlds"]) == he.TOP


def test_rejects_stale_or_changed_report():
    with pytest.raises(ValueError, match="stopped updating"):
        he.parse(SAMPLE, now=datetime(2026, 10, 20, tzinfo=timezone.utc), min_rows=1)
    with pytest.raises(ValueError, match="HE report format changed"):
        he.parse("<html>maintenance</html>")


def test_fetch():
    assert SOURCES["he_progress"].fetch(make_ctx(routes={he.URL: FakeResponse(text=FIXTURE)}))["tlds"]
