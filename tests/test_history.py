import json
from datetime import datetime, timezone

from collect import history
from collect.manifest import load as load_manifest
from collect.registry import SOURCES
from tests.sample_data import write_sample_data

DAY1 = datetime(2026, 10, 14, 0, 30, tzinfo=timezone.utc)
DAY2 = datetime(2026, 10, 15, 0, 30, tzinfo=timezone.utc)


def test_snapshot_records_tracked_values(tmp_path):
    d = write_sample_data(tmp_path)
    entry = history.record(d, load_manifest(d), SOURCES, DAY1)
    assert entry == {"date": "2026-10-14", "values": {"apnic_world_capable": 43.6, "cloudflare_ipv6": 38.4,
                                                       "tranco_aaaa": 61.2, "isoc_top_sites": 51.7}}
    assert history.load(d) == [entry]


def test_snapshot_replaces_same_day(tmp_path):
    d = write_sample_data(tmp_path)
    history.record(d, load_manifest(d), SOURCES, DAY1)
    history.record(d, load_manifest(d), SOURCES, DAY1)
    history.record(d, load_manifest(d), SOURCES, DAY2)
    assert [h["date"] for h in history.load(d)] == ["2026-10-14", "2026-10-15"]


def test_snapshot_skips_failed_and_outdated_sources(tmp_path):
    d = write_sample_data(tmp_path, omit=("tranco_aaaa",))
    manifest = load_manifest(d)
    manifest["apnic"]["schema"] = 1  # written by an older parser
    values = history.record(d, manifest, SOURCES, DAY1)["values"]
    assert "tranco_aaaa" not in values and "apnic_world_capable" not in values
    assert values["cloudflare_ipv6"] == 38.4


def test_no_tracked_data_records_nothing(tmp_path):
    assert history.record(tmp_path, {}, SOURCES, DAY1) is None
    assert history.load(tmp_path) == []


def test_run_records_a_snapshot(tmp_path):
    from collect.registry import Source
    from collect.run import run
    from tests.fakes import make_ctx
    sources = {"tranco_aaaa": Source("tranco_aaaa", 1, lambda c: {"percentage": 50.0}, "T", "https://e.example/")}
    run(sources, tmp_path, make_ctx(now=DAY1))
    assert history.load(tmp_path)[0]["values"] == {"tranco_aaaa": 50.0}
