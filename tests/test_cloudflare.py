import pytest

from collect.registry import SOURCES
from collect.sources import cloudflare
from tests.fakes import FakeResponse, make_ctx

BODY = {
    "success": True,
    "result": {
        "serie_0": {
            "timestamps": ["2026-10-06T00:00:00Z", "2026-10-13T00:00:00Z"],
            "IPv4": ["62.1", "61.6"],
            "IPv6": ["37.9", "38.4"],
        }
    },
}


def test_parse_serie_0():
    assert cloudflare.parse(BODY) == {
        "series": [{"t": "2026-10-06T00:00:00Z", "ipv6": 37.9}, {"t": "2026-10-13T00:00:00Z", "ipv6": 38.4}],
        "latest_ipv6": 38.4,
        "latest_ipv4": 61.6,
        "url": cloudflare.PAGE,
    }


def test_parse_legacy_main_shape():
    body = {"success": True, "result": {"main": BODY["result"]["serie_0"]}}
    assert cloudflare.parse(body)["latest_ipv6"] == 38.4


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="unexpected Cloudflare response"):
        cloudflare.parse({"success": True, "result": {"something_else": {}}})


def test_rejects_api_error():
    with pytest.raises(ValueError, match="Cloudflare API error"):
        cloudflare.parse({"success": False, "errors": [{"message": "bad token"}]})


def test_requires_api_key():
    assert SOURCES["cloudflare_ip_version"].requires_env == ("CLOUDFLARE_API_KEY",)


def test_fetch_sends_bearer_token():
    ctx = make_ctx(routes={cloudflare.API: FakeResponse(json_data=BODY)}, env={"CLOUDFLARE_API_KEY": " tok "})
    assert SOURCES["cloudflare_ip_version"].fetch(ctx)["latest_ipv6"] == 38.4
    url, kwargs = ctx.session.calls[0]
    assert kwargs["headers"] == {"Authorization": "Bearer tok"}


def test_fetch_http_error_includes_body():
    ctx = make_ctx(routes={cloudflare.API: FakeResponse(status_code=400, text="dateRange invalid")},
                   env={"CLOUDFLARE_API_KEY": "tok"})
    with pytest.raises(ValueError, match="400.*dateRange invalid"):
        SOURCES["cloudflare_ip_version"].fetch(ctx)
