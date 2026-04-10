import logging
from pathlib import Path
import sys

from heru.adapters._codex_impl import (
    classify_codex_usage_limit,
    codex_error_details,
    codex_live_events,
    codex_retry_at_hint,
    codex_usage_window,
    extract_codex_errors,
    iter_codex_payloads,
)
from heru.adapters.codex import CodexCLIAdapter
from heru.base import CLIInvocation, LATEST_CONTINUATION_SENTINEL


def _execution(tmp_path: Path, stdout: str, *, stderr: str = "", exit_code: int = 0):
    from heru.base import CLIExecutionResult

    return CLIExecutionResult(
        adapter="codex",
        argv=("codex", "exec"),
        cwd=tmp_path,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


class _LiveCodexAdapter(CodexCLIAdapter):
    def __init__(self, script: Path) -> None:
        super().__init__(binary=sys.executable)
        self._script = script

    def build_command(self, prompt, cwd, model=None, *, max_turns=None, resume_session_id=None):
        return [sys.executable, str(self._script)]

    def build_invocation(self, prompt, cwd, model=None, *, max_turns=None, resume_session_id=None, extra_env=None):
        invocation = super().build_invocation(
            prompt,
            cwd,
            model=model,
            max_turns=max_turns,
            resume_session_id=resume_session_id,
            extra_env=extra_env,
        )
        return CLIInvocation(
            argv=invocation.argv,
            cwd=invocation.cwd,
            env=invocation.env,
            stdin_data=None,
        )


def test_codex_build_invocation_fresh_shape(tmp_path: Path) -> None:
    invocation = CodexCLIAdapter().build_invocation("ship it", tmp_path)

    assert list(invocation.argv) == [
        "codex",
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "--cd",
        str(tmp_path),
        "ship it",
    ]


def test_codex_build_invocation_resume_shape(tmp_path: Path) -> None:
    invocation = CodexCLIAdapter().build_invocation(
        "ship it",
        tmp_path,
        resume_session_id="thread-123",
    )

    assert list(invocation.argv) == [
        "codex",
        "exec",
        "resume",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "thread-123",
        "ship it",
    ]


def test_codex_build_invocation_continue_latest_shape(tmp_path: Path) -> None:
    invocation = CodexCLIAdapter().build_invocation(
        "ship it",
        tmp_path,
        resume_session_id=LATEST_CONTINUATION_SENTINEL,
    )

    assert list(invocation.argv) == [
        "codex",
        "exec",
        "resume",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "ship it",
    ]


def test_codex_render_transcript_uses_fixture_jsonl(tmp_path: Path, fixture_loader) -> None:
    stdout = fixture_loader("codex_stream.jsonl")

    transcript = CodexCLIAdapter().render_transcript(_execution(tmp_path, stdout))

    assert transcript == "Codex says hello again."


def test_codex_render_transcript_falls_back_to_stderr_when_payloads_have_no_messages(tmp_path: Path) -> None:
    stdout = '{"type":"thread.started","thread_id":"thread-123"}\n'

    transcript = CodexCLIAdapter().render_transcript(
        _execution(tmp_path, stdout, stderr="stderr only")
    )

    assert transcript == "[stderr]\nstderr only"


def test_codex_extract_usage_observation_reads_usage_and_continuation_fixture(
    tmp_path: Path, fixture_loader
) -> None:
    stdout = fixture_loader("codex_stream.jsonl")
    adapter = CodexCLIAdapter()

    observation = adapter.extract_usage_observation(_execution(tmp_path, stdout))
    continuation = adapter.extract_continuation(_execution(tmp_path, stdout))

    assert observation is not None
    assert observation.provider == "openai"
    assert observation.usage is not None
    assert observation.usage.used == 20
    assert observation.metadata["input_tokens"] == 12
    assert continuation is not None
    assert continuation.thread_id == "codex-thread-123"


def test_codex_extract_usage_observation_uses_stderr_limit_hint(tmp_path: Path) -> None:
    stderr = "You've hit your usage limit. Try again at 9am UTC. Purchase more credits."

    observation = CodexCLIAdapter().extract_usage_observation(
        _execution(tmp_path, "", stderr=stderr, exit_code=1)
    )

    assert observation is not None
    assert observation.limit_reason == "usage limit reached"
    assert observation.metadata["retry_at_hint"] == "9am UTC"
    assert observation.metadata["purchase_more_credits"] is True


def test_codex_iter_payloads_supports_multiline_objects() -> None:
    stdout = '{\n  "type": "thread.started",\n  "thread_id": "thread-123"\n}\n'

    payloads = iter_codex_payloads(stdout)

    assert payloads == [{"type": "thread.started", "thread_id": "thread-123"}]


def test_codex_extract_codex_errors_keeps_failed_command_output() -> None:
    stdout = "\n".join(
        [
            '{"type":"item.completed","item":{"id":"cmd-1","type":"command_execution","aggregated_output":"bad things happened","status":"failed","exit_code":1}}',
            '{"type":"turn.failed","message":"turn failed"}',
        ]
    )

    assert extract_codex_errors(stdout) == ["turn failed", "bad things happened"]


def test_codex_usage_window_sums_parts_when_total_missing() -> None:
    metadata: dict[str, str | int | bool | None] = {}

    usage = codex_usage_window(
        {"type": "turn.completed", "usage": {"input_tokens": 2, "output_tokens": 3}},
        metadata,
    )

    assert usage is not None
    assert usage.used == 5
    assert metadata["input_tokens"] == 2
    assert metadata["output_tokens"] == 3


def test_codex_error_details_reads_nested_json_error() -> None:
    payload = {
        "type": "error",
        "message": '{"status":429,"error":{"type":"rate_limit","code":"quota","message":"Too many requests"}}',
    }

    message, metadata = codex_error_details(payload)

    assert message == "Too many requests"
    assert metadata["error_status"] == 429
    assert metadata["error_type"] == "rate_limit"
    assert metadata["error_code"] == "quota"


def test_codex_helper_extracts_retry_hint_and_limit_metadata() -> None:
    result = classify_codex_usage_limit("You've hit your usage limit. Try again at tomorrow 9am.")

    assert result is not None
    assert result.retry_at == "tomorrow 9am"
    assert codex_retry_at_hint("Try again at 5pm UTC.") == "5pm UTC"


def test_codex_live_events_exposes_message_tool_and_usage() -> None:
    message_events = codex_live_events(
        {"type": "item.completed", "item": {"type": "agent_message", "text": "hello"}}
    )
    tool_events = codex_live_events(
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": ["bash", "-lc", "pwd"],
                "aggregated_output": "/tmp",
                "exit_code": 0,
            },
        }
    )
    usage_events = codex_live_events(
        {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}}
    )

    assert message_events[0].content == "hello"
    assert tool_events[0].tool_name == "bash"
    assert tool_events[0].tool_output == "/tmp"
    assert usage_events[0].metadata == {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}


def test_codex_run_live_emit_unified_handles_large_item_completed_fixture(
    tmp_path: Path, fixture_loader, caplog
) -> None:
    stdout = fixture_loader("codex_large_item_completed.jsonl")
    payload_file = tmp_path / "payload.jsonl"
    payload_file.write_text(stdout, encoding="utf-8")
    script = tmp_path / "live_codex.py"
    script.write_text(
        "from pathlib import Path\n"
        "import sys, time\n"
        f"payload = Path({str(payload_file)!r}).read_text(encoding='utf-8')\n"
        "sys.stdout.write(payload[:4096])\n"
        "sys.stdout.flush()\n"
        "time.sleep(0.1)\n"
        "sys.stdout.write(payload[4096:])\n"
        "sys.stdout.flush()\n",
        encoding="utf-8",
    )
    caplog.set_level(logging.WARNING, logger="litehive.agents.adapters.codex")

    result = _LiveCodexAdapter(script).run_live(prompt="ignored", cwd=tmp_path, emit_unified=True)

    assert '"kind":"tool_result"' in result.stdout
    assert '"tool_name":"bash"' in result.stdout
    assert '"tool_output":"' + ("A" * 8192) in result.stdout
    assert not [record for record in caplog.records if "skipping" in record.message]


def test_codex_run_live_emit_unified_logs_truncated_payload_once(tmp_path: Path, caplog) -> None:
    script = tmp_path / "truncated_codex.py"
    script.write_text(
        "import sys, time\n"
        "sys.stdout.write('{\"type\":\"item.completed\",\"item\":{\"type\":\"command_execution\",\"aggregated_output\":\"')\n"
        "sys.stdout.flush()\n"
        "time.sleep(0.1)\n",
        encoding="utf-8",
    )
    caplog.set_level(logging.WARNING, logger="litehive.agents.adapters.codex")

    _LiveCodexAdapter(script).run_live(prompt="ignored", cwd=tmp_path, emit_unified=True)

    messages = [record.message for record in caplog.records if "unterminated JSON object" in record.message]
    assert messages == [
        'codex: skipping unterminated JSON object at line 1 (content: {"type":"item.completed","item":{"type":"command_execution","aggregated_output":")'
    ]
