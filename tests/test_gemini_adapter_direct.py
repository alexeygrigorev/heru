from pathlib import Path

from heru.adapters._gemini_impl import (
    duration_to_millis,
    gemini_error_details,
    gemini_usage_window,
    live_events,
)
from heru.adapters.gemini import GeminiCLIAdapter
from heru.base import LATEST_CONTINUATION_SENTINEL


def _execution(tmp_path: Path, stdout: str, *, stderr: str = "", exit_code: int = 0):
    from heru.base import CLIExecutionResult

    return CLIExecutionResult(
        adapter="gemini",
        argv=("gemini", "-p", "prompt"),
        cwd=tmp_path,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_gemini_build_invocation_fresh_shape(tmp_path: Path) -> None:
    invocation = GeminiCLIAdapter().build_invocation("ship it", tmp_path, model="gemini-2.5-pro")

    assert list(invocation.argv) == [
        "gemini",
        "-p",
        "ship it",
        "--output-format",
        "stream-json",
        "--yolo",
        "-m",
        "gemini-2.5-pro",
    ]


def test_gemini_build_invocation_resume_shape(tmp_path: Path) -> None:
    invocation = GeminiCLIAdapter().build_invocation("ship it", tmp_path, resume_session_id="session-123")

    assert list(invocation.argv)[-2:] == ["--resume", "session-123"]


def test_gemini_build_invocation_continue_latest_shape(tmp_path: Path) -> None:
    invocation = GeminiCLIAdapter().build_invocation(
        "ship it",
        tmp_path,
        resume_session_id=LATEST_CONTINUATION_SENTINEL,
    )

    assert invocation.argv[-1] == "--resume"


def test_gemini_render_transcript_uses_fixture_jsonl(tmp_path: Path, fixture_loader) -> None:
    transcript = GeminiCLIAdapter().render_transcript(
        _execution(tmp_path, fixture_loader("gemini_stream.jsonl"))
    )

    assert transcript == "Gemini text"


def test_gemini_extract_usage_and_continuation_from_fixture(tmp_path: Path, fixture_loader) -> None:
    execution = _execution(tmp_path, fixture_loader("gemini_stream.jsonl"))
    adapter = GeminiCLIAdapter()

    observation = adapter.extract_usage_observation(execution)
    continuation = adapter.extract_continuation(execution)

    assert observation is not None
    assert observation.provider == "google"
    assert observation.usage is not None
    assert observation.usage.used == 18
    assert observation.metadata["finish_reason"] == "STOP"
    assert observation.metadata["model"] == "gemini-2.5-pro"
    assert continuation is not None
    assert continuation.session_id == "gemini-session-123"


def test_gemini_usage_window_supports_result_stats_shape() -> None:
    metadata: dict[str, str | int | bool | None] = {}

    usage = gemini_usage_window(
        {"type": "result", "stats": {"input_tokens": 2, "output_tokens": 3, "duration_ms": 50}},
        metadata,
    )

    assert usage is not None
    assert usage.used == 5
    assert metadata["duration_ms"] == 50


def test_gemini_error_details_extract_quota_usage_metadata() -> None:
    payload = {
        "type": "error",
        "value": {
            "message": "quota exhausted",
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaValue": "1000", "quotaMetric": "tokens_per_day"}],
                },
                {
                    "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                    "reason": "QUOTA_EXHAUSTED",
                    "metadata": {"quotaResetTimeStamp": "2026-04-11T00:00:00Z"},
                },
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "1.5s"},
            ],
        },
    }

    message, metadata, usage = gemini_error_details(payload)

    assert message == "quota exhausted"
    assert usage is not None
    assert usage.limit == 1000
    assert usage.reset_at == "2026-04-11T00:00:00Z"
    assert metadata["retry_delay_ms"] == 1500
    assert metadata["error_status"] == "RESOURCE_EXHAUSTED"


def test_gemini_duration_to_millis_supports_seconds_and_ms() -> None:
    assert duration_to_millis("1.25s") == 1250
    assert duration_to_millis("50ms") == 50


def test_gemini_live_events_include_tool_result_and_usage() -> None:
    tool_event = live_events({"type": "tool_result", "result": {"answer": "world"}})[0]
    usage_event = live_events(
        {"type": "finished", "value": {"usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 2, "totalTokenCount": 3}}}
    )[0]

    assert tool_event.kind == "tool_result"
    assert tool_event.tool_output == '{"answer": "world"}'
    assert usage_event.kind == "usage"
    assert usage_event.metadata == {"promptTokenCount": 1, "candidatesTokenCount": 2, "totalTokenCount": 3}


def test_gemini_extract_usage_observation_uses_stderr_limit_fallback(tmp_path: Path) -> None:
    observation = GeminiCLIAdapter().extract_usage_observation(
        _execution(tmp_path, "", stderr="rate limit exceeded", exit_code=1)
    )

    assert observation is not None
    assert observation.limit_reason == "rate limit reached"
