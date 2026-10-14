import pytest

from collect.registry import DAY, SOURCES, source


def test_source_registers_and_returns_function():
    @source("test_registry_example", DAY, title="Example", url="https://example.net/")
    def fetch(ctx):
        return {"ok": True}

    try:
        src = SOURCES["test_registry_example"]
        assert src.fetch is fetch
        assert src.ttl_seconds == DAY
        assert src.title == "Example"
        assert src.url == "https://example.net/"
        assert src.requires_env == ()
    finally:
        del SOURCES["test_registry_example"]


def test_duplicate_key_rejected():
    @source("test_registry_dup", DAY, title="Dup", url="https://example.net/")
    def first(ctx):
        return {}

    try:
        with pytest.raises(ValueError, match="duplicate source key"):
            @source("test_registry_dup", DAY, title="Dup", url="https://example.net/")
            def second(ctx):
                return {}
    finally:
        del SOURCES["test_registry_dup"]
