import os
from pathlib import Path

import pytest

from tests_integration.helpers import INTEGRATION_ENV


@pytest.fixture(autouse=True, scope="session")
def _enable_all_integration_engines():
    previous = os.environ.get(INTEGRATION_ENV)
    os.environ[INTEGRATION_ENV] = "all"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(INTEGRATION_ENV, None)
        else:
            os.environ[INTEGRATION_ENV] = previous


@pytest.fixture
def integration_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture(scope="module")
def module_integration_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("heru-integration")

