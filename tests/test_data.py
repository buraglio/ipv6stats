from datetime import datetime, timezone

import pytest

from tests.sample_data import NOW, write_sample_data
from web.data import Data, Datum, combine


def test_datum_carries_provenance(tmp_path):
    data = Data(write_sample_data(tmp_path), NOW)
    d = data.datum("apnic", lambda p: p["world"]["capable"])
    assert d == Datum(43.6, ("apnic",), datetime(2026, 10, 14, 0, 5, tzinfo=timezone.utc), False)


def test_failed_source_gives_none(tmp_path):
    data = Data(write_sample_data(tmp_path, omit=("apnic",)), NOW)
    assert data.datum("apnic", lambda p: p["world"]["capable"]) is None


def test_pick_returning_none_gives_none(tmp_path):
    data = Data(write_sample_data(tmp_path), NOW)
    assert data.datum("apnic", lambda p: None) is None


def test_unknown_source_raises(tmp_path):
    data = Data(write_sample_data(tmp_path), NOW)
    with pytest.raises(KeyError, match="unknown source"):
        data.datum("apnicc", lambda p: p)


def test_shape_mismatch_raises(tmp_path):
    data = Data(write_sample_data(tmp_path), NOW)
    with pytest.raises(ValueError, match="apnic.json"):
        data.datum("apnic", lambda p: p["no_such_field"])


def test_stale_after_twice_the_interval(tmp_path):
    data = Data(write_sample_data(tmp_path, last_success={"bgp_v6_table": "2026-10-11T00:05:00+00:00"}), NOW)
    assert data.datum("bgp_v6_table", lambda p: p["current"]).stale
    assert not data.datum("apnic", lambda p: p["world"]).stale


def test_combine_merges_provenance():
    old = datetime(2026, 10, 1, tzinfo=timezone.utc)
    new = datetime(2026, 10, 14, tzinfo=timezone.utc)
    merged = combine(5, [Datum(1, ("b",), new, False), Datum(2, ("a",), old, True)])
    assert merged == Datum(5, ("a", "b"), old, True)


def test_status_rows(tmp_path):
    rows = {r["key"]: r for r in Data(write_sample_data(tmp_path), NOW).status_rows()}
    assert rows["isoc_pulse"]["status"] == "not_configured"
    assert "ISOC_PULSE_API_KEY" in rows["isoc_pulse"]["error"]
    assert rows["bgp_v6_table"]["ttl_days"] == 1
    assert rows["apnic"]["ttl_days"] == 30
    assert rows["apnic"]["status"] == "ok"


def test_missing_data_dir_has_no_data(tmp_path):
    data = Data(tmp_path / "does-not-exist", NOW)
    assert data.datum("apnic", lambda p: p) is None
    assert all(r["status"] == "never run" for r in data.status_rows())
