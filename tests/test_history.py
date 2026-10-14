import json
from datetime import datetime, timezone

import pytest

from collect import history
from collect.manifest import load as load_manifest, save as save_manifest
from collect.registry import SOURCES
from tests.sample_data import write_sample_data

DAY1 = datetime(2026, 10, 14, 0, 30, tzinfo=timezone.utc)   # sample data's FETCHED is 2026-10-14T00:05
DAY2 = datetime(2026, 10, 15, 0, 30, tzinfo=timezone.utc)


def test_records_own_measurements_fetched_today(tmp_path):
    d = write_sample_data(tmp_path)
    entry = history.record(d, load_manifest(d), SOURCES, DAY1)
    # Tranco 61.2; cloud hostnames 3 of 7 with IPv6; NIST 2 of 4 domains with IPv6 web
    assert entry == {"date": "2026-10-14", "values": {"tranco_aaaa": 61.2, "cloud_hostnames": 42.9, "nist_web": 50.0}}
    assert history.load(d) == [entry]


def test_skips_sources_not_fetched_today(tmp_path):
    # A monthly source that is merely not due keeps status "ok"; its old value must not be re-dated.
    d = write_sample_data(tmp_path, last_success={"tranco_aaaa": "2026-09-20T00:05:00+00:00"})
    values = history.record(d, load_manifest(d), SOURCES, DAY1)["values"]
    assert "tranco_aaaa" not in values


def test_replaces_same_day_and_records_nothing_on_quiet_days(tmp_path):
    d = write_sample_data(tmp_path)
    history.record(d, load_manifest(d), SOURCES, DAY1)
    history.record(d, load_manifest(d), SOURCES, DAY1)
    assert history.record(d, load_manifest(d), SOURCES, DAY2) is None   # nothing fetched on DAY2
    assert [h["date"] for h in history.load(d)] == ["2026-10-14"]


def test_skips_failed_and_outdated_sources(tmp_path):
    d = write_sample_data(tmp_path, omit=("tranco_aaaa",))
    manifest = load_manifest(d)
    manifest["nist_usgv6"]["schema"] = 99
    values = history.record(d, manifest, SOURCES, DAY1)["values"]
    assert set(values) == {"cloud_hostnames"}


def test_corrupt_history_is_reported_and_left_alone(tmp_path):
    d = write_sample_data(tmp_path)
    (d / history.HISTORY).write_text('{"not": "a list"')
    with pytest.raises(ValueError, match="history.json"):
        history.load(d)
    with pytest.raises(ValueError):
        history.record(d, load_manifest(d), SOURCES, DAY1)
    assert (d / history.HISTORY).read_text() == '{"not": "a list"'   # not overwritten


def test_run_survives_corrupt_history(tmp_path):
    from collect.registry import Source
    from collect.run import run
    from tests.fakes import make_ctx
    (tmp_path / history.HISTORY).write_text("[{]")
    sources = {"tranco_aaaa": Source("tranco_aaaa", 1, lambda c: {"percentage": 50.0}, "T", "https://e.example/")}
    result = run(sources, tmp_path, make_ctx(now=DAY1))
    assert result.failed == [] and (tmp_path / "tranco_aaaa.json").exists()
