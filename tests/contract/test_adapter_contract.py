from pathlib import Path

import pytest

from heru.adapters.claude import ClaudeCLIAdapter
from heru.adapters.codex import CodexCLIAdapter
from heru.adapters.copilot import CopilotCLIAdapter
from heru.adapters.gemini import GeminiCLIAdapter
from heru.adapters.goz import GozCLIAdapter
from heru.adapters.opencode import OpenCodeAdapter
from heru.base import CLIExecutionResult
from heru.base import LATEST_CONTINUATION_SENTINEL


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


@pytest.mark.parametrize(
    ("adapter", "cwd", "kwargs", "expected_argv"),
    [
        (
            CodexCLIAdapter(),
            Path("/tmp/workspace"),
            {"prompt": "ship it"},
            [
                "codex",
                "exec",
                "--json",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "--cd",
                "/tmp/workspace",
                "ship it",
            ],
        ),
        (
            ClaudeCLIAdapter(),
            Path("/tmp/workspace"),
            {"prompt": "ship it", "model": "sonnet", "max_turns": 3},
            [
                "claude",
                "-p",
                "ship it",
                "--output-format",
                "stream-json",
                "--include-partial-messages",
                "--verbose",
                "--dangerously-skip-permissions",
                "--model",
                "sonnet",
                "--max-turns",
                "3",
            ],
        ),
        (
            CopilotCLIAdapter(),
            Path("/tmp/workspace"),
            {"prompt": "ship it", "model": "gpt-5"},
            [
                "copilot",
                "-p",
                "ship it",
                "--output-format",
                "json",
                "--allow-all-tools",
                "--autopilot",
                "--no-auto-update",
                "--add-dir",
                "/tmp/workspace",
                "--model",
                "gpt-5",
            ],
        ),
        (
            GeminiCLIAdapter(),
            Path("/tmp/workspace"),
            {"prompt": "ship it", "model": "gemini-2.5-pro"},
            [
                "gemini",
                "-p",
                "ship it",
                "--output-format",
                "stream-json",
                "--yolo",
                "-m",
                "gemini-2.5-pro",
            ],
        ),
        (
            OpenCodeAdapter(),
            Path("/tmp/workspace"),
            {"prompt": "ship it", "model": "gpt-5"},
            [
                "opencode",
                "run",
                "--format",
                "json",
                "--dir",
                "/tmp/workspace",
                "--model",
                "gpt-5",
                "ship it",
            ],
        ),
        (
            GozCLIAdapter(),
            Path("/tmp/workspace"),
            {"prompt": "ship it", "model": "glm-4.5"},
            ["goz", "run", "--format", "json", "--model", "glm-4.5", "ship it"],
        ),
    ],
)
def test_build_invocation_preserves_public_argv_shape(adapter, cwd, kwargs, expected_argv) -> None:
    invocation = adapter.build_invocation(kwargs.pop("prompt"), cwd, **kwargs)

    assert list(invocation.argv) == expected_argv


@pytest.mark.parametrize(
    ("adapter", "resume_session_id", "expected_argv"),
    [
        (
            CodexCLIAdapter(),
            "thread-123",
            [
                "codex",
                "exec",
                "resume",
                "--json",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "thread-123",
                "ship it",
            ],
        ),
        (
            ClaudeCLIAdapter(),
            "session-123",
            [
                "claude",
                "--resume",
                "session-123",
                "-p",
                "ship it",
                "--output-format",
                "stream-json",
                "--include-partial-messages",
                "--verbose",
                "--dangerously-skip-permissions",
            ],
        ),
        (
            CopilotCLIAdapter(),
            "session-123",
            [
                "copilot",
                "-p",
                "ship it",
                "--output-format",
                "json",
                "--allow-all-tools",
                "--autopilot",
                "--no-auto-update",
                "--add-dir",
                "/tmp/workspace",
                "--resume=session-123",
            ],
        ),
        (
            GeminiCLIAdapter(),
            "session-123",
            [
                "gemini",
                "-p",
                "ship it",
                "--output-format",
                "stream-json",
                "--yolo",
                "--resume",
                "session-123",
            ],
        ),
        (
            OpenCodeAdapter(),
            "session-123",
            [
                "opencode",
                "run",
                "--format",
                "json",
                "--dir",
                "/tmp/workspace",
                "--session",
                "session-123",
                "ship it",
            ],
        ),
        (
            GozCLIAdapter(),
            "session-123",
            [
                "goz",
                "run",
                "--format",
                "json",
                "--resume-session",
                "session-123",
                "ship it",
            ],
        ),
    ],
)
def test_build_invocation_preserves_public_resume_shape(adapter, resume_session_id, expected_argv) -> None:
    invocation = adapter.build_invocation("ship it", Path("/tmp/workspace"), resume_session_id=resume_session_id)

    assert list(invocation.argv) == expected_argv


@pytest.mark.parametrize(
    ("adapter", "fixture_name", "expected_text"),
    [
        (CodexCLIAdapter(), "codex_stream.jsonl", "Codex says hello again."),
        (ClaudeCLIAdapter(), "claude_stream.jsonl", "Final Claude answer"),
        (CopilotCLIAdapter(), "copilot_stream.jsonl", "Copilot final answer"),
        (GeminiCLIAdapter(), "gemini_stream.jsonl", "Gemini text"),
        (OpenCodeAdapter(), "opencode_stream.jsonl", "OpenCode line 2"),
        (GozCLIAdapter(), "goz_stream.jsonl", "Hello Goz"),
    ],
)
def test_render_transcript_extracts_assistant_text_from_fixture(
    adapter,
    fixture_name: str,
    expected_text: str,
    fixture_loader,
    tmp_path: Path,
) -> None:
    transcript = adapter.render_transcript(
        execution_for(adapter=adapter.name, cwd=tmp_path, stdout=fixture_loader(fixture_name))
    )

    assert expected_text in transcript
    assert not transcript.startswith('{"type"')


@pytest.mark.parametrize(
    ("adapter", "fixture_name", "provider", "usage_used", "continuation_attr", "continuation_id"),
    [
        (CodexCLIAdapter(), "codex_stream.jsonl", "openai", 20, "thread_id", "codex-thread-123"),
        (ClaudeCLIAdapter(), "claude_stream.jsonl", "anthropic", 18, "session_id", "claude-session-123"),
        (CopilotCLIAdapter(), "copilot_stream.jsonl", "github", 70, "session_id", "copilot-session-123"),
        (GeminiCLIAdapter(), "gemini_stream.jsonl", "google", 18, "session_id", "gemini-session-123"),
        (OpenCodeAdapter(), "opencode_stream.jsonl", "z.ai", 11, "session_id", "opencode-session-123"),
        (GozCLIAdapter(), "goz_stream.jsonl", "z.ai", 9, "session_id", "goz-session-123"),
    ],
)
def test_extract_usage_observation_and_continuation_match_fixture_contract(
    adapter,
    fixture_name: str,
    provider: str,
    usage_used: int,
    continuation_attr: str,
    continuation_id: str,
    fixture_loader,
    tmp_path: Path,
) -> None:
    execution = execution_for(adapter=adapter.name, cwd=tmp_path, stdout=fixture_loader(fixture_name))

    observation = adapter.extract_usage_observation(execution)
    continuation = adapter.extract_continuation(execution)

    assert observation is not None
    assert observation.provider == provider
    assert observation.usage is not None
    assert observation.usage.used == usage_used
    assert continuation is not None
    assert getattr(continuation, continuation_attr) == continuation_id


@pytest.mark.parametrize(
    ("engine_name", "expected_argv"),
    [
        (
            "codex",
            [
                "codex",
                "exec",
                "resume",
                "--json",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "--last",
                "continue please",
            ],
        ),
        (
            "claude",
            [
                "claude",
                "--continue",
                "-p",
                "continue please",
                "--output-format",
                "stream-json",
                "--include-partial-messages",
                "--verbose",
                "--dangerously-skip-permissions",
            ],
        ),
        (
            "copilot",
            [
                "copilot",
                "-p",
                "continue please",
                "--output-format",
                "json",
                "--allow-all-tools",
                "--autopilot",
                "--no-auto-update",
                "--add-dir",
                "/tmp/workspace",
                "--continue",
            ],
        ),
        (
            "gemini",
            [
                "gemini",
                "-p",
                "continue please",
                "--output-format",
                "stream-json",
                "--yolo",
                "--resume",
            ],
        ),
        (
            "opencode",
            [
                "opencode",
                "run",
                "--format",
                "json",
                "--dir",
                "/tmp/workspace",
                "--continue",
                "continue please",
            ],
        ),
    ],
)
def test_continue_latest_maps_to_engine_native_resume_shape(engine_name: str, expected_argv) -> None:
    from heru import get_engine

    invocation = get_engine(engine_name).build_invocation(
        "continue please",
        Path("/tmp/workspace"),
        resume_session_id=LATEST_CONTINUATION_SENTINEL,
    )

    assert list(invocation.argv) == expected_argv


def test_goz_rejects_continue_latest_without_explicit_session_id() -> None:
    from heru import get_engine

    with pytest.raises(ValueError, match="goz does not support resuming the latest session"):
        get_engine("goz").build_invocation(
            "continue please",
            Path("/tmp/workspace"),
            resume_session_id=LATEST_CONTINUATION_SENTINEL,
        )


def test_claude_large_prompt_switches_from_arg_to_stdin(tmp_path: Path) -> None:
    prompt = "x" * (ClaudeCLIAdapter._MAX_ARG_PROMPT_BYTES + 1)

    invocation = ClaudeCLIAdapter().build_invocation(prompt, tmp_path)

    assert "-p" not in invocation.argv
    assert invocation.stdin_data == prompt
