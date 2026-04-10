from pathlib import Path

from heru.adapters._goz_impl import (
    format_goz_tool_block,
    goz_cost_value,
    goz_error_details,
    goz_extract_text,
    goz_usage_window,
    live_events,
)
from heru.adapters.goz import GozCLIAdapter


def _execution(tmp_path: Path, stdout: str, *, stderr: str = "", exit_code: int = 0):
    from heru.base import CLIExecutionResult

    return CLIExecutionResult(
        adapter="goz",
        argv=("goz", "run"),
        cwd=tmp_path,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_goz_build_invocation_fresh_shape(tmp_path: Path) -> None:
    invocation = GozCLIAdapter().build_invocation("ship it", tmp_path, model="glm-4.5")

    assert list(invocation.argv) == ["goz", "run", "--format", "json", "--model", "glm-4.5", "ship it"]


def test_goz_build_invocation_resume_shape(tmp_path: Path) -> None:
    invocation = GozCLIAdapter().build_invocation("ship it", tmp_path, resume_session_id="session-123")

    assert list(invocation.argv) == [
        "goz",
        "run",
        "--format",
        "json",
        "--resume-session",
        "session-123",
        "ship it",
    ]


def test_goz_render_transcript_uses_fixture_jsonl(tmp_path: Path, fixture_loader) -> None:
    transcript = GozCLIAdapter().render_transcript(_execution(tmp_path, fixture_loader("goz_stream.jsonl")))

    assert "Hello Goz" in transcript
    assert "```tool" in transcript


def test_goz_extract_usage_and_continuation_from_fixture(tmp_path: Path, fixture_loader) -> None:
    execution = _execution(tmp_path, fixture_loader("goz_stream.jsonl"))
    adapter = GozCLIAdapter()

    observation = adapter.extract_usage_observation(execution)
    continuation = adapter.extract_continuation(execution)

    assert observation is not None
    assert observation.provider == "z.ai"
    assert observation.usage is not None
    assert observation.usage.used == 9
    assert observation.metadata["model"] == "glm-4.5"
    assert continuation is not None
    assert continuation.session_id == "goz-session-123"


def test_goz_usage_window_reads_cost_and_model() -> None:
    metadata: dict[str, str | int | bool | None] = {}
    usage = goz_usage_window(
        {"type": "usage", "input_tokens": 2, "output_tokens": 3, "model": "glm", "cost": 0.1},
        metadata,
    )

    assert usage is not None
    assert usage.used == 5
    assert metadata["model"] == "glm"
    assert metadata["cost"] == "0.100000"


def test_goz_error_details_reads_nested_error_dict() -> None:
    message, metadata = goz_error_details(
        {"type": "error", "error": {"type": "rate_limit", "code": 429, "error": {"message": "too many"}}}
    )

    assert message == "too many"
    assert metadata["error_type"] == "rate_limit"
    assert metadata["error_code"] == 429


def test_goz_extract_text_supports_nested_lists() -> None:
    value = [{"text": "hello "}, {"content": {"text": "world"}}]

    assert goz_extract_text(value) == "hello world"


def test_goz_format_tool_block_renders_input_and_output() -> None:
    block = format_goz_tool_block({"id": "tool-1", "name": "grep", "input": {"pattern": "x"}, "output": "done"})

    assert "name: grep" in block
    assert '"pattern": "x"' in block
    assert "output:" in block


def test_goz_cost_value_supports_nested_totals() -> None:
    cost = goz_cost_value({"data": {"total_cost": {"usd": 0.25}}}, {})

    assert cost == 0.25


def test_goz_live_events_include_tool_result_and_usage() -> None:
    tool_event = live_events({"type": "tool_result", "tool": "grep", "result": {"matches": 2}})[0]
    usage_event = live_events({"type": "usage", "input_tokens": 1, "output_tokens": 2, "total_tokens": 3})[0]

    assert tool_event.kind == "tool_result"
    assert tool_event.tool_name == "grep"
    assert tool_event.tool_output == '{"matches": 2}'
    assert usage_event.kind == "usage"
    assert usage_event.metadata["total_tokens"] == 3
