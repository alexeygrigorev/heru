import pytest

from tests_integration.helpers import (
    assert_continue_latest_smoke,
    prepare_smoke_session,
    smoke_token,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def gemini_smoke_session(module_integration_root):
    return prepare_smoke_session("gemini", cwd=module_integration_root)


def test_gemini_smoke_prompt_succeeds(gemini_smoke_session) -> None:
    assert smoke_token("gemini") in gemini_smoke_session.engine.render_transcript(gemini_smoke_session.execution)


def test_gemini_continue_latest_succeeds(gemini_smoke_session) -> None:
    assert_continue_latest_smoke(gemini_smoke_session)
