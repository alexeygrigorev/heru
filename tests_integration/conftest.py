from pathlib import Path

import pytest


@pytest.fixture
def integration_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture(scope="module")
def module_integration_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("heru-integration")

