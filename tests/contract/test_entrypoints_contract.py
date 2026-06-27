import pytest
from typer.testing import CliRunner

from heru import ENGINE_CHOICES, get_engine
from heru.adapters.claude import ClaudeCLIAdapter
from heru.adapters.codex import CodexCLIAdapter
from heru.adapters.copilot import CopilotCLIAdapter
from heru.adapters.gemini import GeminiCLIAdapter
from heru.adapters.goz import GozCLIAdapter
from heru.adapters.opencode import OpenCodeAdapter
from heru.main import app


def test_engine_choices_lists_all_supported_public_engines() -> None:
    assert ENGINE_CHOICES == ["claude", "codex", "copilot", "gemini", "goz", "opencode"]


@pytest.mark.parametrize(
    ("engine_name", "adapter_type"),
    [
        ("claude", ClaudeCLIAdapter),
        ("codex", CodexCLIAdapter),
        ("copilot", CopilotCLIAdapter),
        ("gemini", GeminiCLIAdapter),
        ("goz", GozCLIAdapter),
        ("opencode", OpenCodeAdapter),
    ],
)
def test_get_engine_resolves_stable_public_adapter_instances(engine_name: str, adapter_type) -> None:
    assert isinstance(get_engine(engine_name), adapter_type)


@pytest.mark.parametrize("engine_name", ENGINE_CHOICES)
def test_engine_commands_expose_public_profile_option(engine_name: str) -> None:
    result = CliRunner().invoke(app, [engine_name, "--help"])

    assert result.exit_code == 0
    assert "--profile" in result.stdout
