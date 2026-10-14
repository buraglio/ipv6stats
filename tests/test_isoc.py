import json
from pathlib import Path

import pytest

from collect.registry import SOURCES
from collect.sources import isoc
from tests.fakes import FakeResponse, make_ctx

FIXTURES = Path(__file__).parent / "fixtures" / "isoc"
KEY = {"ISOC_PULSE_API_KEY": " secret "}


def body(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def routes(overrides=None):
    # Longer paths first: FakeSession matches by prefix, and "/ipv6" prefixes "/ipv6?topsites=true".
    table = {f"{isoc.API}{path}": FakeResponse(json_data=body(name)) for name, path in isoc.SERIES}
    table.update(overrides or {})
    return dict(sorted(table.items(), key=lambda kv: -len(kv[0])))


def test_parse_series_converts_to_percent_and_sorts_by_date():
    parsed = isoc.parse_series({"data": [{"date": "2026-07-16", "value": 0.517}, {"date": "2026-07-01", "value": 0.51}]})
    assert parsed["series"] == [{"date": "2026-07-01", "value": 51.0}, {"date": "2026-07-16", "value": 51.7}]
    assert parsed["latest"] == {"date": "2026-07-16", "value": 51.7}


def test_rejects_empty_series():
    with pytest.raises(ValueError, match="ISOC Pulse series is empty"):
        isoc.parse_series({"data": []})


def test_rejects_changed_format():
    with pytest.raises(ValueError, match="ISOC Pulse response format changed"):
        isoc.parse_series({"results": []})
    with pytest.raises(ValueError, match="ISOC Pulse response format changed"):
        isoc.parse_series({"data": [{"date": "2026-07-16", "value": 51.7}]})  # a percent, not a fraction


def test_fetch_all_series_with_bearer_key():
    ctx = make_ctx(routes=routes(), env=KEY)
    payload = SOURCES["isoc_pulse"].fetch(ctx)
    assert payload["websites_ipv6"]["latest"] == {"date": "2026-07-16", "value": 51.7}
    assert payload["websites_https"]["latest"]["value"] == 95.9
    assert payload["websites_tls13"]["latest"]["value"] == 87.8
    assert payload["users_ipv6"]["latest"] == {"date": "2026-10-01", "value": 44.09}
    assert all(kwargs["headers"] == {"Authorization": "Bearer secret"} for _, kwargs in ctx.session.calls)


def test_fetch_reports_rejected_key():
    bad = {f"{isoc.API}/ipv6?topsites=true": FakeResponse(status_code=401, text='{"detail": "Unauthorized"}')}
    with pytest.raises(ValueError, match="401.*Unauthorized"):
        SOURCES["isoc_pulse"].fetch(make_ctx(routes=routes(bad), env=KEY))
