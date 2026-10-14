from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import cidr_report as cr
from tests.fakes import FakeResponse, make_ctx

FIXTURE = (Path(__file__).parent / "fixtures" / "bgp" / "cidr-aggregation.html").read_text()


def test_parse_recorded_table():
    parsed = cr.parse(FIXTURE)
    assert len(parsed["ases"]) == 30
    assert parsed["date"].count("-") == 2
    first = parsed["ases"][0]
    assert first["now"] - first["aggregated"] == first["gain"]
    assert parsed["table"]["now"] > first["now"]


def test_parse_date():
    assert cr.parse_date("14Oct26") == "2026-10-14"


def test_cidr_rejects_changed_format():
    with pytest.raises(ValueError, match="CIDR Report format changed"):
        cr.parse("<html>maintenance</html>")


def name_routes(asns, body):
    return {f"{cr.NAMES_URL}?resource=AS{a}": body for a in asns}


def test_fetch_adds_names():
    asns = [a["asn"] for a in cr.parse(FIXTURE)["ases"]]
    routes = {cr.URL: FakeResponse(text=FIXTURE)}
    routes.update(name_routes(asns, FakeResponse(json_data={"status": "ok", "data": {"holder": "EXAMPLE - Example Ltd"}})))
    payload = SOURCES["cidr_report_aggregation"].fetch(make_ctx(routes=routes))
    assert payload["ases"][0]["name"] == "EXAMPLE - Example Ltd"


def test_names_are_optional():
    routes = {cr.URL: FakeResponse(text=FIXTURE)}  # RIPEstat unreachable
    payload = SOURCES["cidr_report_aggregation"].fetch(make_ctx(routes=routes))
    assert all(a["name"] is None for a in payload["ases"])
