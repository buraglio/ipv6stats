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
    return True


def test_workflow_does_not_enable_isoc_before_its_client_exists():
    # Setting the secret would make the source due (and failing) every night.
    if isoc_has_client():
        pytest.skip("ISOC client exists; the secret may be passed")
    assert "secrets.ISOC_PULSE_API_KEY" not in WORKFLOW.read_text()
