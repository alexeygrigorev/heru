import pytest

from tests_integration.helpers import (
    assert_continue_latest_smoke,
    prepare_smoke_session,
    smoke_token,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def codex_smoke_session(module_integration_root):
    return prepare_smoke_session("codex", cwd=module_integration_root)


def test_codex_smoke_prompt_succeeds(codex_smoke_session) -> None:
    assert smoke_token("codex") in codex_smoke_session.engine.render_transcript(codex_smoke_session.execution)


def test_codex_continue_latest_succeeds(integration_root) -> None:
    assert_continue_latest_smoke("codex", cwd=integration_root)
