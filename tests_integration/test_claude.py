import pytest

from tests_integration.helpers import (
    assert_continue_latest_smoke,
    prepare_smoke_session,
    smoke_token,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def claude_smoke_session(module_integration_root):
    return prepare_smoke_session("claude", cwd=module_integration_root)


def test_claude_smoke_prompt_succeeds(claude_smoke_session) -> None:
    assert smoke_token("claude") in claude_smoke_session.engine.render_transcript(claude_smoke_session.execution)


def test_claude_continue_latest_succeeds(integration_root) -> None:
    assert_continue_latest_smoke("claude", cwd=integration_root)
