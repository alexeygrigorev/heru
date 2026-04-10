import pytest

from tests_integration.helpers import (
    assert_resume_by_id_smoke,
    prepare_smoke_session,
    smoke_token,
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def goz_smoke_session(module_integration_root):
    return prepare_smoke_session("goz", cwd=module_integration_root)


def test_goz_smoke_prompt_succeeds(goz_smoke_session) -> None:
    assert smoke_token("goz") in goz_smoke_session.engine.render_transcript(goz_smoke_session.execution)


def test_goz_resume_by_id_succeeds(integration_root) -> None:
    assert_resume_by_id_smoke("goz", cwd=integration_root)
