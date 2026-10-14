import json
from datetime import datetime, timedelta, timezone

from collect.manifest import load
from collect.registry import DAY, Source
from collect.run import RunResult, exceeds_threshold, run
from tests.fakes import make_ctx

NOW = datetime(2026, 10, 14, 0, 5, tzinfo=timezone.utc)


def stub(key, fn, ttl=DAY, requires_env=()):
    return Source(key, ttl, fn, "Stub", "https://example.net/", requires_env)


def never_called(ctx):
    raise AssertionError("fetch should not have been called")


def test_successful_fetch_writes_payload_and_manifest(tmp_path):
    result = run({"a": stub("a", lambda c: {"x": 1})}, tmp_path, make_ctx(now=NOW))

    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 1}
    entry = load(tmp_path)["a"]
    assert entry["status"] == "ok"
    assert entry["error"] is None
    assert entry["last_success"] == NOW.isoformat(timespec="seconds")
    assert entry["ttl_seconds"] == DAY
    assert result.attempted == ["a"] and result.failed == []


def test_failed_fetch_keeps_previous_payload(tmp_path):
    earlier = NOW - timedelta(days=2)
    run({"a": stub("a", lambda c: {"x": 1})}, tmp_path, make_ctx(now=earlier))

    def boom(ctx):
        raise RuntimeError("boom")

    result = run({"a": stub("a", boom)}, tmp_path, make_ctx(now=NOW))

    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 1}
    entry = load(tmp_path)["a"]
    assert entry["status"] == "error"
    assert "boom" in entry["error"]
    assert entry["last_success"] == earlier.isoformat(timespec="seconds")
    assert entry["last_attempt"] == NOW.isoformat(timespec="seconds")
    assert result.failed == ["a"]


def test_empty_payload_is_a_failure(tmp_path):
    result = run({"a": stub("a", lambda c: {})}, tmp_path, make_ctx(now=NOW))
    assert result.failed == ["a"]
    assert not (tmp_path / "a.json").exists()


def test_unserializable_payload_is_a_failure_and_writes_nothing(tmp_path):
    result = run({"a": stub("a", lambda c: {"x": object()})}, tmp_path, make_ctx(now=NOW))
    assert result.failed == ["a"]
    assert not (tmp_path / "a.json").exists()


def test_missing_env_is_not_configured(tmp_path):
    sources = {"a": stub("a", never_called, requires_env=("TOKEN",))}
    result = run(sources, tmp_path, make_ctx(env={}, now=NOW))
    assert result.not_configured == ["a"]
    assert result.attempted == []
    entry = load(tmp_path)["a"]
    assert entry["status"] == "not_configured"
    assert "TOKEN" in entry["error"]


def test_blank_env_value_counts_as_missing(tmp_path):
    sources = {"a": stub("a", never_called, requires_env=("TOKEN",))}
    result = run(sources, tmp_path, make_ctx(env={"TOKEN": "  "}, now=NOW))
    assert result.not_configured == ["a"]


def test_source_not_due_is_skipped_unless_forced(tmp_path):
    run({"a": stub("a", lambda c: {"x": 1}, ttl=30 * DAY)}, tmp_path, make_ctx(now=NOW))
    later = make_ctx(now=NOW + timedelta(days=1))

    skipped = run({"a": stub("a", never_called, ttl=30 * DAY)}, tmp_path, later)
    assert skipped.skipped == ["a"]

    forced = run({"a": stub("a", lambda c: {"x": 2}, ttl=30 * DAY)}, tmp_path, later, force=True)
    assert forced.attempted == ["a"]
    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 2}


def test_daily_source_runs_again_the_next_night(tmp_path):
    # Yesterday's run finished at 00:07; tonight's starts at 00:05 (23h58m later).
    yesterday = make_ctx(now=NOW - timedelta(days=1) + timedelta(minutes=2))
    run({"a": stub("a", lambda c: {"x": 1})}, tmp_path, yesterday)
    result = run({"a": stub("a", lambda c: {"x": 2})}, tmp_path, make_ctx(now=NOW))
    assert result.attempted == ["a"]


def test_only_limits_sources(tmp_path):
    sources = {"a": stub("a", lambda c: {"x": 1}), "b": stub("b", never_called)}
    result = run(sources, tmp_path, make_ctx(now=NOW), only={"a"})
    assert result.attempted == ["a"]
    assert "b" not in load(tmp_path)


def test_failure_threshold():
    assert not exceeds_threshold(RunResult(attempted=["a", "b", "c", "d"], failed=["a"]))
    assert exceeds_threshold(RunResult(attempted=["a", "b", "c", "d"], failed=["a", "b"]))
    assert not exceeds_threshold(RunResult())
