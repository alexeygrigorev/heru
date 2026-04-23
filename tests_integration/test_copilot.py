import pytest

from tests_integration.helpers import (
    assert_continue_latest_smoke,
    prepare_smoke_session,
    smoke_token,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def copilot_smoke_session(module_integration_root):
    return prepare_smoke_session("copilot", cwd=module_integration_root)


def test_copilot_smoke_prompt_succeeds(copilot_smoke_session) -> None:
    assert smoke_token("copilot") in copilot_smoke_session.engine.render_transcript(copilot_smoke_session.execution)


def test_copilot_continue_latest_succeeds(copilot_smoke_session) -> None:
    assert_continue_latest_smoke(copilot_smoke_session)
