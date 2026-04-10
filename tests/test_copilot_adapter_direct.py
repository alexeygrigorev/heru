from pathlib import Path

from heru.adapters._copilot_impl import (
    copilot_quota_usage_window,
    copilot_usage_observation,
    errors,
    live_events,
    select_copilot_quota_snapshot,
)
from heru.adapters.copilot import CopilotCLIAdapter
from heru.base import LATEST_CONTINUATION_SENTINEL


def _execution(tmp_path: Path, stdout: str, *, stderr: str = "", exit_code: int = 0):
    from heru.base import CLIExecutionResult

    return CLIExecutionResult(
        adapter="copilot",
        argv=("copilot", "-p", "prompt"),
        cwd=tmp_path,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_copilot_build_invocation_fresh_shape(tmp_path: Path) -> None:
    invocation = CopilotCLIAdapter().build_invocation("ship it", tmp_path, model="gpt-5")

    assert list(invocation.argv) == [
        "copilot",
        "-p",
        "ship it",
        "--output-format",
        "json",
        "--allow-all-tools",
        "--autopilot",
        "--no-auto-update",
        "--add-dir",
        str(tmp_path),
        "--model",
        "gpt-5",
    ]


def test_copilot_build_invocation_resume_shape(tmp_path: Path) -> None:
    invocation = CopilotCLIAdapter().build_invocation("ship it", tmp_path, resume_session_id="session-123")

    assert invocation.argv[-1] == "--resume=session-123"


def test_copilot_build_invocation_continue_latest_shape(tmp_path: Path) -> None:
    invocation = CopilotCLIAdapter().build_invocation(
        "ship it",
        tmp_path,
        resume_session_id=LATEST_CONTINUATION_SENTINEL,
    )

    assert invocation.argv[-1] == "--continue"


def test_copilot_render_transcript_uses_fixture_jsonl(tmp_path: Path, fixture_loader) -> None:
    transcript = CopilotCLIAdapter().render_transcript(
        _execution(tmp_path, fixture_loader("copilot_stream.jsonl"))
    )

    assert transcript == "Copilot final answer"


def test_copilot_extract_usage_and_continuation_from_fixture(tmp_path: Path, fixture_loader) -> None:
    execution = _execution(tmp_path, fixture_loader("copilot_stream.jsonl"))
    adapter = CopilotCLIAdapter()

    observation = adapter.extract_usage_observation(execution)
    continuation = adapter.extract_continuation(execution)

    assert observation is not None
    assert observation.provider == "github"
    assert observation.usage is not None
    assert observation.usage.unit == "requests"
    assert observation.usage.used == 70
    assert observation.metadata["quota_snapshot"] == "chat"
    assert continuation is not None
    assert continuation.session_id == "copilot-session-123"


def test_copilot_usage_observation_uses_token_totals_without_quota_snapshot() -> None:
    usage, metadata = copilot_usage_observation(
        {"type": "assistant.usage", "data": {"inputTokens": 3, "outputTokens": 4, "cacheReadTokens": 2}}
    ) or (None, {})

    assert usage is not None
    assert usage.used == 9
    assert metadata["cacheReadTokens"] == 2


def test_copilot_quota_usage_window_computes_remaining() -> None:
    usage = copilot_quota_usage_window(
        {"entitlementRequests": 100, "usedRequests": 40, "resetDate": "2026-04-11T00:00:00Z"}
    )

    assert usage is not None
    assert usage.limit == 100
    assert usage.remaining == 60


def test_copilot_selects_preferred_quota_snapshot() -> None:
    name, snapshot = select_copilot_quota_snapshot({"premium": {"usedRequests": 1}, "chat": {"usedRequests": 2}})

    assert name == "chat"
    assert snapshot == {"usedRequests": 2}


def test_copilot_error_helper_reads_failed_tool_result() -> None:
    result = errors(
        {
            "type": "tool.execution_complete",
            "data": {"success": False, "result": {"content": "tool failed"}},
        }
    )

    assert result == ["tool failed"]


def test_copilot_live_events_cover_tool_and_usage() -> None:
    tool_event = live_events({"type": "tool.execution_start", "data": {"toolName": "search"}})[0]
    usage_event = live_events(
        {"type": "assistant.usage", "data": {"inputTokens": 1, "outputTokens": 2, "model": "gpt-5"}}
    )[0]

    assert tool_event.kind == "tool_call"
    assert tool_event.tool_name == "search"
    assert usage_event.kind == "usage"
    assert usage_event.metadata == {"inputTokens": 1, "outputTokens": 2, "model": "gpt-5"}
