from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import apnic, apnic_regions as ar
from tests.fakes import FakeResponse, make_ctx

PAGE = (Path(__file__).parent / "fixtures" / "apnic" / "economy-US.html").read_text(encoding="utf-8")


def routes(failing=None):
    table = {f"{apnic.URL}{code}": FakeResponse(text=PAGE) for code in ar.REGIONS}
    if failing:
        table[f"{apnic.URL}{failing}"] = FakeResponse(status_code=503)
    return table


def test_fetches_every_region():
    payload = SOURCES["apnic_region_history"].fetch(make_ctx(routes=routes()))
    assert set(payload["regions"]) == set(ar.REGIONS)
    assert payload["regions"]["XE"]["name"] == "Europe"
    assert len(payload["regions"]["XA"]["history"]) >= 52


def test_region_history_fails_if_any_region_fails():
    with pytest.raises(Exception, match="503"):
        SOURCES["apnic_region_history"].fetch(make_ctx(routes=routes(failing="XD")))
