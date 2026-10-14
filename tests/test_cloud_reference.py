from datetime import datetime, timezone

import pytest

from collect.sources.cloud_endpoints import ENDPOINTS
from web import reference


def test_reference_loads_with_defaults():
    providers = reference.load_cloud_providers()
    assert len(providers) == 23
    aws = next(p for p in providers if p["key"] == "aws")
    assert aws["name"] == "AWS" and aws["service"] and isinstance(aws["limitations"], list)
    assert "grade" not in aws


def test_reference_keys_match_endpoint_providers():
    assert {p["key"] for p in reference.load_cloud_providers()} == set(ENDPOINTS)


def test_reference_has_no_statistics():
    assert "%" not in reference.CLOUD_FILE.read_text()


def test_reference_requires_fields(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text('[[provider]]\nkey = "x"\nname = "X"\n')
    with pytest.raises(ValueError, match="last_reviewed"):
        reference.load_cloud_providers(bad)
    bad.write_text('[[provider]]\nkey = "x"\nname = "X"\nlast_reviewed = "soon"\n')
    with pytest.raises(ValueError, match="last_reviewed"):
        reference.load_cloud_providers(bad)
    bad.write_text('[[provider]]\nkey = "x"\nname = "X"\nlast_reviewed = "2026-01-01"\n' * 2)
    with pytest.raises(ValueError, match="duplicate"):
        reference.load_cloud_providers(bad)


def test_stale_reviews_warn():
    providers = [{"name": "Old", "last_reviewed": "2025-10-04"}, {"name": "New", "last_reviewed": "2026-10-01"}]
    warnings = reference.stale_reviews(providers, datetime(2026, 10, 14, tzinfo=timezone.utc))
    assert len(warnings) == 1 and "Old" in warnings[0]


def test_reference_has_no_missing_values_written_as_text():
    # Fields the old data never stated must be absent, not "None" or an invented "No".
    text = reference.CLOUD_FILE.read_text()
    assert '"None"' not in text
    s3 = next(s for p in reference.load_cloud_providers() if p["key"] == "aws" for s in p["service"] if s["name"] == "S3")
    assert "prefix_delegation" not in s3 and "nat_free_egress" not in s3


def test_list_reference_files_load_and_have_no_statistics():
    carriers, gov = reference.load_carriers(), reference.load_government()
    assert carriers["carrier"][0]["asn"] == 21928 and gov["group"][0]["domains"]
    for path in (reference.CARRIERS_FILE, reference.GOVERNMENT_FILE):
        assert "%" not in path.read_text()


def test_list_reviews_warn_when_old():
    old = datetime(2027, 6, 1, tzinfo=timezone.utc)
    assert len(reference.list_reviews(old)) == 2
    assert reference.list_reviews(datetime(2026, 10, 15, tzinfo=timezone.utc)) == []
