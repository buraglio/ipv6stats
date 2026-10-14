import pytest

from collect.registry import SOURCES
from collect.sources import isoc, isoc_routing as ir
from tests.fakes import FakeResponse, make_ctx

KEY = {"ISOC_PULSE_API_KEY": "k"}
ROA6 = {"data": [{"date": "2026-10-12", "value": 0.7324}, {"date": "2026-10-11", "value": 0.73}]}
ROA4 = {"data": [{"date": "2026-10-12", "value": 0.648}]}
ROV = {"data": [{"date": "2026-10-10", "partial": 0.9424, "full": 0.3487}, {"date": "2021-12-24", "partial": 0.3006, "full": 0.0625}]}


def routes(rov=ROV):
    return {f"{isoc.API}/roa?ip_version=6": FakeResponse(json_data=ROA6),
            f"{isoc.API}/roa?ip_version=4": FakeResponse(json_data=ROA4),
            f"{isoc.API}/rov": FakeResponse(json_data=rov)}


def test_fetch_routing_security():
    p = SOURCES["isoc_routing"].fetch(make_ctx(routes=routes(), env=KEY))
    assert p["roa_ipv6"]["latest"] == {"date": "2026-10-12", "value": 73.24}
    assert p["roa_ipv4"]["latest"]["value"] == 64.8
    assert p["rov"]["latest"] == {"date": "2026-10-10", "partial": 94.24, "full": 34.87}
    assert p["rov"]["series"][0]["date"] == "2021-12-24"


def test_routing_security_requires_key():
    assert SOURCES["isoc_routing"].requires_env == ("ISOC_PULSE_API_KEY",)


def test_rov_rejects_changed_format():
    with pytest.raises(ValueError, match="ISOC Pulse response format changed"):
        SOURCES["isoc_routing"].fetch(make_ctx(routes=routes(rov={"data": [{"date": "2026-10-10", "value": 0.5}]}), env=KEY))


def test_roa_zero_points_are_gaps_not_measurements():
    with_gaps = {"data": [{"date": "2019-01-09", "value": 0.0}, {"date": "2019-10-08", "value": 0.29},
                          {"date": "2019-10-09", "value": 0.0}, {"date": "2019-10-28", "value": 0.30}]}
    r = routes(); r[f"{isoc.API}/roa?ip_version=6"] = FakeResponse(json_data=with_gaps)
    p = SOURCES["isoc_routing"].fetch(make_ctx(routes=r, env=KEY))
    assert [x["date"] for x in p["roa_ipv6"]["series"]] == ["2019-10-08", "2019-10-28"]
    assert p["roa_ipv6"]["latest"]["value"] == 30.0
