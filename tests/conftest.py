from pathlib import Path

import pytest

from heru.base import CLIExecutionResult


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def execution_for(
    *,
    adapter: str,
    cwd: Path,
    stdout: str,
    stderr: str = "",
    exit_code: int = 0,
    argv: tuple[str, ...] | None = None,
) -> CLIExecutionResult:
    return CLIExecutionResult(
        adapter=adapter,
        argv=argv or (adapter, "run"),
        cwd=cwd,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


@pytest.fixture
def fixture_loader():
    return fixture_text
