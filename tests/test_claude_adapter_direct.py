from pathlib import Path

from heru.adapters._claude_impl import (
    claude_error_details,
    claude_usage_window,
    extract_claude_text_delta_fallback,
    live_events,
)
from heru.adapters.claude import ClaudeCLIAdapter
from heru.base import LATEST_CONTINUATION_SENTINEL


def _execution(tmp_path: Path, stdout: str, *, stderr: str = "", exit_code: int = 0):
    from heru.base import CLIExecutionResult

    return CLIExecutionResult(
        adapter="claude",
        argv=("claude", "-p", "prompt"),
        cwd=tmp_path,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_claude_build_invocation_fresh_shape(tmp_path: Path) -> None:
    invocation = ClaudeCLIAdapter().build_invocation("ship it", tmp_path, model="sonnet", max_turns=3)

    assert list(invocation.argv) == [
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
    ]
    assert invocation.stdin_data is None


def test_claude_build_invocation_resume_shape(tmp_path: Path) -> None:
    invocation = ClaudeCLIAdapter().build_invocation("ship it", tmp_path, resume_session_id="session-123")

    assert list(invocation.argv) == [
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
    ]


def test_claude_build_invocation_continue_latest_shape(tmp_path: Path) -> None:
    invocation = ClaudeCLIAdapter().build_invocation(
        "ship it",
        tmp_path,
        resume_session_id=LATEST_CONTINUATION_SENTINEL,
    )

    assert list(invocation.argv) == [
        "claude",
        "--resume",
        "-p",
        "ship it",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--dangerously-skip-permissions",
    ]


def test_claude_build_invocation_uses_stdin_for_large_prompt(tmp_path: Path) -> None:
    prompt = "x" * (ClaudeCLIAdapter._MAX_ARG_PROMPT_BYTES + 1)

    invocation = ClaudeCLIAdapter().build_invocation(prompt, tmp_path)

    assert "-p" not in invocation.argv
    assert invocation.stdin_data == prompt


def test_claude_render_transcript_uses_fixture_jsonl(tmp_path: Path, fixture_loader) -> None:
    transcript = ClaudeCLIAdapter().render_transcript(
        _execution(tmp_path, fixture_loader("claude_stream.jsonl"))
    )

    assert transcript == "Hello Claude\nFinal Claude answer"


def test_claude_extract_usage_and_continuation_from_fixture(tmp_path: Path, fixture_loader) -> None:
    execution = _execution(tmp_path, fixture_loader("claude_stream.jsonl"))
    adapter = ClaudeCLIAdapter()

    observation = adapter.extract_usage_observation(execution)
    continuation = adapter.extract_continuation(execution)

    assert observation is not None
    assert observation.provider == "anthropic"
    assert observation.usage is not None
    assert observation.usage.used == 18
    assert observation.metadata["service_tier"] == "pro"
    assert observation.metadata["web_search_requests"] == 1
    assert continuation is not None
    assert continuation.session_id == "claude-session-123"


def test_claude_extract_usage_observation_reads_error_metadata(tmp_path: Path) -> None:
    stdout = '{"type":"error","error":{"type":"rate_limit","code":"quota","message":"rate limit exceeded"}}\n'

    observation = ClaudeCLIAdapter().extract_usage_observation(_execution(tmp_path, stdout, exit_code=1))

    assert observation is not None
    assert observation.limit_reason == "rate limit reached"
    assert observation.metadata["error_type"] == "rate_limit"
    assert observation.metadata["error_code"] == "quota"


def test_claude_text_delta_fallback_stitches_fragments() -> None:
    stdout = "\n".join(
        [
            '{"type":"content_block_delta","index":1,"delta":{"type":"text_delta","text":"world"}}',
            '{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"hello "}}',
        ]
    )

    assert extract_claude_text_delta_fallback(stdout) == ["hello ", "world"]


def test_claude_usage_window_collects_nested_metadata() -> None:
    metadata: dict[str, str | int | bool | None] = {}
    payload = {
        "usage": {
            "input_tokens": 3,
            "output_tokens": 4,
            "cache_creation_input_tokens": 5,
            "cache_read_input_tokens": 6,
            "server_tool_use": {"web_fetch_requests": 2},
            "cache_creation": {"ephemeral_5m_input_tokens": 9},
            "service_tier": "priority",
        },
        "duration_ms": 20,
        "total_cost_usd": 0.5,
    }

    usage = claude_usage_window(payload, metadata)

    assert usage is not None
    assert usage.used == 18
    assert metadata["web_fetch_requests"] == 2
    assert metadata["ephemeral_5m_input_tokens"] == 9
    assert metadata["total_cost_usd"] == "0.500000"


def test_claude_error_details_reads_result_error_shape() -> None:
    message, metadata = claude_error_details(
        {"type": "result", "is_error": True, "error": {"type": "invalid", "code": "bad", "message": "broken"}}
    )

    assert message == "broken"
    assert metadata["error_type"] == "invalid"
    assert metadata["error_code"] == "bad"
    assert metadata["error_message"] == "broken"


def test_claude_live_events_include_tool_and_usage() -> None:
    tool_event = live_events(
        {
            "type": "content_block_start",
            "content_block": {"type": "tool_use", "name": "bash", "input": {"cmd": "pwd"}},
        }
    )[0]
    usage_event = live_events(
        {"type": "result", "result": "done", "usage": {"input_tokens": 1, "output_tokens": 2}}
    )[-1]

    assert tool_event.kind == "tool_call"
    assert tool_event.tool_name == "bash"
    assert usage_event.kind == "usage"
    assert usage_event.metadata == {"input_tokens": 1, "output_tokens": 2}
