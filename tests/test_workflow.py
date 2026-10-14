from pathlib import Path

import pytest

import collect.sources  # noqa: F401  (registers sources)
from collect.registry import SOURCES
from tests.fakes import make_ctx

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "publish.yml"


def isoc_has_client() -> bool:
    try:
        SOURCES["isoc_pulse"].fetch(make_ctx(env={"ISOC_PULSE_API_KEY": "k"}))
    except NotImplementedError:
        return False
    except Exception:  # a real client fails here only because the fake session has no routes
        return True
    return True


def test_workflow_does_not_enable_isoc_before_its_client_exists():
    # Setting the secret would make the source due (and failing) every night.
    if isoc_has_client():
        pytest.skip("ISOC client exists; the secret may be passed")
    assert "secrets.ISOC_PULSE_API_KEY" not in WORKFLOW.read_text()


TESTS_WORKFLOW = WORKFLOW.parent / "test.yml"


def test_publish_runs_only_from_main():
    # Pages has one site per repo and schedule/dispatch only run from the default branch.
    text = WORKFLOW.read_text()
    assert 'cron: "0 0 * * *"' in text
    assert "workflow_dispatch:" in text
    assert "branches: [main]" in text
    assert "static-site" not in text


def test_other_branches_run_tests_without_secrets_or_deploys():
    text = TESTS_WORKFLOW.read_text()
    assert "branches: [staging]" in text
    assert "pull_request:" in text
    assert "uv run pytest" in text
    assert "secrets." not in text
    assert "deploy-pages" not in text
