import io
import zipfile

import pytest

from collect.registry import SOURCES
from collect.sources import tranco
from tests.fakes import FakeResponse, make_ctx


def make_zip(rows):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("top-1m.csv", "".join(f"{rank},{domain}\n" for rank, domain in rows))
    return buffer.getvalue()


def test_top_domains_reads_first_n():
    data = make_zip([(1, "google.com"), (2, "example.org"), (3, "www.foo.net")])
    assert tranco.top_domains(data, 2) == ["google.com", "example.org"]


def test_has_ipv6_checks_apex_then_www():
    names = {"google.com", "www.example.org"}
    has = names.__contains__
    assert tranco.has_ipv6("google.com", has)
    assert tranco.has_ipv6("example.org", has)
    assert not tranco.has_ipv6("www.foo.net", has)  # no "www.www.foo.net" lookup


def test_measure_counts_and_rounds():
    result = tranco.measure(["google.com", "example.org", "www.foo.net"],
                            {"google.com", "www.example.org"}.__contains__)
    assert result["checked"] == 3
    assert result["with_aaaa"] == 2
    assert result["percentage"] == 66.7
    assert result["top"][2] == {"rank": 3, "domain": "www.foo.net", "aaaa": False}


def test_measure_rejects_zero_as_broken_dns():
    with pytest.raises(ValueError, match="DNS"):
        tranco.measure(["a.com", "b.com"], lambda name: False)


def test_rejects_changed_format():
    # A list shorter than TOP_N means the download is not the real list.
    ctx = make_ctx(routes={tranco.LIST_URL: FakeResponse(content=make_zip([(1, "a.com")]))}, aaaa={"a.com"})
    with pytest.raises(ValueError, match="only 1 domains"):
        SOURCES["tranco_aaaa"].fetch(ctx)


def test_fetch_full_list(monkeypatch):
    monkeypatch.setattr(tranco, "TOP_N", 3)
    rows = [(1, "google.com"), (2, "example.org"), (3, "www.foo.net"), (4, "ignored.com")]
    ctx = make_ctx(routes={tranco.LIST_URL: FakeResponse(content=make_zip(rows))},
                   aaaa={"google.com", "www.example.org", "ignored.com"})
    assert SOURCES["tranco_aaaa"].fetch(ctx)["with_aaaa"] == 2
