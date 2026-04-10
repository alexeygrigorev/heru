import pytest

from tests_integration.helpers import (
    assert_continue_latest_smoke,
    prepare_smoke_session,
    smoke_token,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def opencode_smoke_session(module_integration_root):
    return prepare_smoke_session("opencode", cwd=module_integration_root)


def test_opencode_smoke_prompt_succeeds(opencode_smoke_session) -> None:
    assert smoke_token("opencode") in opencode_smoke_session.engine.render_transcript(opencode_smoke_session.execution)


def test_opencode_continue_latest_succeeds(integration_root) -> None:
    assert_continue_latest_smoke("opencode", cwd=integration_root)
