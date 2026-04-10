from pathlib import Path

from heru.adapters._opencode_impl import (
    extract_opencode_errors,
    opencode_error_details,
    opencode_usage_window,
    live_events,
)
from heru.adapters.opencode import OpenCodeAdapter
from heru.base import LATEST_CONTINUATION_SENTINEL


def _execution(tmp_path: Path, stdout: str, *, stderr: str = "", exit_code: int = 0):
    from heru.base import CLIExecutionResult

    return CLIExecutionResult(
        adapter="opencode",
        argv=("opencode", "run"),
        cwd=tmp_path,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_opencode_build_invocation_fresh_shape(tmp_path: Path) -> None:
    invocation = OpenCodeAdapter().build_invocation("ship it", tmp_path, model="gpt-5")

    assert list(invocation.argv) == [
        "opencode",
        "run",
        "--format",
        "json",
        "--dir",
        str(tmp_path),
        "--model",
        "gpt-5",
        "ship it",
    ]


def test_opencode_build_invocation_resume_shape(tmp_path: Path) -> None:
    invocation = OpenCodeAdapter().build_invocation("ship it", tmp_path, resume_session_id="session-123")

    assert list(invocation.argv) == [
        "opencode",
        "run",
        "--format",
        "json",
        "--dir",
        str(tmp_path),
        "--session",
        "session-123",
        "ship it",
    ]


def test_opencode_build_invocation_continue_latest_shape(tmp_path: Path) -> None:
    invocation = OpenCodeAdapter().build_invocation(
        "ship it",
        tmp_path,
        resume_session_id=LATEST_CONTINUATION_SENTINEL,
    )

    assert list(invocation.argv) == [
        "opencode",
        "run",
        "--format",
        "json",
        "--dir",
        str(tmp_path),
        "--continue",
        "ship it",
    ]


def test_opencode_render_transcript_uses_fixture_jsonl(tmp_path: Path, fixture_loader) -> None:
    transcript = OpenCodeAdapter().render_transcript(
        _execution(tmp_path, fixture_loader("opencode_stream.jsonl"))
    )

    assert transcript == "OpenCode line 1\nOpenCode line 2"


def test_opencode_extract_usage_and_continuation_from_fixture(tmp_path: Path, fixture_loader) -> None:
    execution = _execution(tmp_path, fixture_loader("opencode_stream.jsonl"))
    adapter = OpenCodeAdapter()

    observation = adapter.extract_usage_observation(execution)
    continuation = adapter.extract_continuation(execution)

    assert observation is not None
    assert observation.provider == "z.ai"
    assert observation.usage is not None
    assert observation.usage.used == 11
    assert observation.metadata["cache_read_tokens"] == 1
    assert continuation is not None
    assert continuation.session_id == "opencode-session-123"


def test_opencode_usage_window_sums_input_and_output_without_total() -> None:
    metadata: dict[str, str | int | bool | None] = {}
    usage = opencode_usage_window(
        {"type": "step_finish", "part": {"tokens": {"input": 2, "output": 3}}},
        metadata,
    )

    assert usage is not None
    assert usage.used == 5


def test_opencode_error_details_reads_error_payload() -> None:
    message, metadata = opencode_error_details(
        {
            "type": "error",
            "error": {"name": "APIError", "data": {"message": "request failed", "status": 429, "code": "quota"}},
        }
    )

    assert message == "request failed"
    assert metadata["error_name"] == "APIError"
    assert metadata["error_status"] == 429
    assert metadata["error_code"] == "quota"


def test_opencode_extract_errors_joins_multiple_messages() -> None:
    stdout = "\n".join(
        [
            '{"type":"error","error":{"name":"APIError","data":{"message":"first"}}}',
            '{"type":"error","error":{"name":"APIError","data":{"message":"second"}}}',
        ]
    )

    assert extract_opencode_errors(stdout) == "first\nsecond"


def test_opencode_live_events_include_usage_and_error() -> None:
    usage_event = live_events(
        {"type": "step_finish", "part": {"tokens": {"total": 3, "input": 1, "output": 2}, "cost": 0.5}}
    )[0]
    error_event = live_events(
        {"type": "error", "error": {"name": "APIError", "data": {"message": "broken"}}}
    )[0]

    assert usage_event.kind == "usage"
    assert usage_event.metadata["total_tokens"] == 3
    assert error_event.kind == "error"
    assert error_event.error == "broken"


def test_opencode_extract_usage_observation_uses_stderr_limit_fallback(tmp_path: Path) -> None:
    observation = OpenCodeAdapter().extract_usage_observation(
        _execution(
            tmp_path,
            '{"type":"text","sessionID":"sess-1","part":{"text":"hello"}}\n',
            stderr="usage limit reached",
            exit_code=1,
        )
    )

    assert observation is not None
    assert observation.limit_reason == "usage limit reached"
