from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from heru import extract_engine_continuation, get_engine
from heru.base import CLIExecutionResult, ExternalCLIAdapter, LATEST_CONTINUATION_SENTINEL
from heru.quota import (
    claude_quota_block_reason,
    codex_quota_block_reason,
    copilot_quota_block_reason,
    zai_quota_block_reason,
)
from heru.types import RuntimeEngineContinuation


INTEGRATION_ENV = "HERU_INTEGRATION_ENGINES"
TIMEOUT_ENV = "HERU_INTEGRATION_TIMEOUT_SECONDS"
DEFAULT_TIMEOUT_SECONDS = 60
ENGINE_NAMES = ("claude", "codex", "copilot", "gemini", "goz", "opencode")


@dataclass(frozen=True, slots=True)
class SmokeSession:
    engine_name: str
    cwd: Path
    engine: ExternalCLIAdapter
    execution: CLIExecutionResult
    continuation: RuntimeEngineContinuation | None


def enabled_integration_engines() -> set[str]:
    raw = os.environ.get(INTEGRATION_ENV, "")
    if not raw.strip():
        return set()
    enabled = {item.strip() for item in raw.split(",") if item.strip()}
    return set(ENGINE_NAMES) if enabled & {"all", "*"} else enabled


def require_enabled_engine(engine_name: str) -> None:
    enabled = enabled_integration_engines()
    if not enabled:
        pytest.skip(f"{INTEGRATION_ENV} is unset; real engine integration tests are opt-in")
    if engine_name not in enabled:
        pytest.skip(f"{engine_name} is not enabled in {INTEGRATION_ENV}={','.join(sorted(enabled))}")


def _engine_quota_block_reason(engine_name: str) -> str | None:
    try:
        if engine_name == "codex":
            return codex_quota_block_reason()
        if engine_name == "claude":
            return claude_quota_block_reason()
        if engine_name == "copilot":
            return copilot_quota_block_reason()
        if engine_name in {"goz", "opencode"}:
            return zai_quota_block_reason()
    except Exception:
        return None
    return None


def require_real_engine(engine_name: str) -> None:
    require_enabled_engine(engine_name)
    engine = get_engine(engine_name)
    if not engine.is_available():
        pytest.skip(f"{engine_name} binary not available on PATH")
    quota_reason = _engine_quota_block_reason(engine_name)
    if quota_reason:
        pytest.skip(f"{engine_name} quota too high: {quota_reason}")


def integration_timeout_seconds() -> int:
    raw = os.environ.get(TIMEOUT_ENV, str(DEFAULT_TIMEOUT_SECONDS)).strip()
    try:
        value = int(raw)
    except ValueError:
        pytest.fail(f"{TIMEOUT_ENV} must be an integer, got {raw!r}")
    if value <= 0:
        pytest.fail(f"{TIMEOUT_ENV} must be positive, got {value}")
    return value


def smoke_token(engine_name: str) -> str:
    return f"HERU_INTEGRATION_SMOKE_{engine_name.upper()}"


def resume_token(engine_name: str) -> str:
    return f"HERU_INTEGRATION_RESUME_{engine_name.upper()}"


def smoke_prompt(engine_name: str) -> str:
    token = smoke_token(engine_name)
    return (
        "Reply with exactly this text and nothing else: "
        f"{token}"
    )


def resume_prompt(engine_name: str) -> str:
    token = resume_token(engine_name)
    return (
        "Resume the conversation and reply with exactly this text and nothing else: "
        f"{token}"
    )


def execute_engine_prompt(
    engine_name: str,
    *,
    prompt: str,
    cwd: Path,
    max_turns: int | None = None,
    resume_session_id: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> tuple[ExternalCLIAdapter, CLIExecutionResult]:
    engine = get_engine(engine_name)
    invocation = engine.finalize_invocation(
        engine.build_invocation(
            prompt,
            cwd,
            model=getattr(engine, "DEFAULT_MODEL", None),
            max_turns=max_turns,
            resume_session_id=resume_session_id,
            extra_env=extra_env,
        )
    )
    timeout_seconds = integration_timeout_seconds()
    run_kwargs = {
        "args": invocation.argv,
        "cwd": invocation.cwd,
        "env": invocation.env,
        "capture_output": True,
        "text": True,
        "timeout": timeout_seconds,
        "check": False,
    }
    if invocation.stdin_data is None:
        run_kwargs["stdin"] = subprocess.DEVNULL
    else:
        run_kwargs["input"] = invocation.stdin_data
    try:
        completed = subprocess.run(**run_kwargs)
    except subprocess.TimeoutExpired as exc:
        stdout_tail = (exc.stdout or "")[-800:]
        stderr_tail = (exc.stderr or "")[-800:]
        pytest.fail(
            f"{engine_name} timed out after {timeout_seconds}s\n"
            f"argv: {list(invocation.argv)!r}\n"
            f"stdout_tail:\n{stdout_tail}\n"
            f"stderr_tail:\n{stderr_tail}"
        )
    sandboxed, sandbox_summary = engine.sandbox_details()
    return engine, CLIExecutionResult(
        adapter=engine.name,
        argv=invocation.argv,
        cwd=invocation.cwd,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        sandboxed=sandboxed,
        sandbox_summary=sandbox_summary,
    )


def assistant_transcript(engine_name: str, execution: CLIExecutionResult) -> str:
    engine = get_engine(engine_name)
    return engine.render_transcript(execution).partition("\n\n[stderr]\n")[0].strip()


def _skip_on_empty_upstream(engine_name: str, execution: CLIExecutionResult) -> None:
    if execution.exit_code != 0:
        return
    if assistant_transcript(engine_name, execution).strip():
        return
    pytest.skip(
        f"{engine_name} returned no assistant output after retries (upstream provider flake)"
    )


def assert_successful_reply(engine_name: str, execution: CLIExecutionResult, expected_text: str) -> None:
    transcript = assistant_transcript(engine_name, execution)
    assert execution.exit_code == 0, execution.transcript
    assert transcript, f"Expected assistant transcript from {engine_name}"
    assert expected_text in transcript, transcript


def prepare_smoke_session(engine_name: str, *, cwd: Path, attempts: int = 4) -> SmokeSession:
    require_real_engine(engine_name)
    max_turns = 1 if engine_name == "claude" else None
    expected = smoke_token(engine_name)
    last_execution: CLIExecutionResult | None = None
    engine: ExternalCLIAdapter | None = None
    for attempt in range(attempts):
        if attempt > 0:
            time.sleep(5 * attempt)
        engine, last_execution = execute_engine_prompt(
            engine_name,
            prompt=smoke_prompt(engine_name),
            cwd=cwd,
            max_turns=max_turns,
        )
        if last_execution.exit_code == 0 and expected in assistant_transcript(engine_name, last_execution):
            break
    assert last_execution is not None and engine is not None
    _skip_on_empty_upstream(engine_name, last_execution)
    assert_successful_reply(engine_name, last_execution, expected)
    return SmokeSession(
        engine_name=engine_name,
        cwd=cwd,
        engine=engine,
        execution=last_execution,
        continuation=extract_engine_continuation(engine_name, last_execution),
    )


def assert_continue_latest_smoke(session: SmokeSession, *, attempts: int = 4) -> None:
    engine_name = session.engine_name
    max_turns = 1 if engine_name == "claude" else None
    expected = resume_token(engine_name)
    resumed: CLIExecutionResult | None = None
    for attempt in range(attempts):
        if attempt > 0:
            time.sleep(5 * attempt)
        _, resumed = execute_engine_prompt(
            engine_name,
            prompt=resume_prompt(engine_name),
            cwd=session.cwd,
            max_turns=max_turns,
            resume_session_id=LATEST_CONTINUATION_SENTINEL,
        )
        if resumed.exit_code == 0 and expected in assistant_transcript(engine_name, resumed):
            break
    assert resumed is not None
    _skip_on_empty_upstream(engine_name, resumed)
    assert_successful_reply(engine_name, resumed, expected)
    assert session.continuation is None or session.continuation.resume_id


def assert_resume_by_id_smoke(session: SmokeSession, *, attempts: int = 4) -> None:
    engine_name = session.engine_name
    continuation = session.continuation
    assert continuation is not None and continuation.resume_id, (
        f"Expected {engine_name} continuation id from first run, got {continuation!r}"
    )
    max_turns = 1 if engine_name == "claude" else None
    expected = resume_token(engine_name)
    resumed: CLIExecutionResult | None = None
    for attempt in range(attempts):
        if attempt > 0:
            time.sleep(5 * attempt)
        _, resumed = execute_engine_prompt(
            engine_name,
            prompt=resume_prompt(engine_name),
            cwd=session.cwd,
            max_turns=max_turns,
            resume_session_id=continuation.resume_id,
        )
        if resumed.exit_code == 0 and expected in assistant_transcript(engine_name, resumed):
            break
    assert resumed is not None
    _skip_on_empty_upstream(engine_name, resumed)
    assert_successful_reply(engine_name, resumed, expected)
