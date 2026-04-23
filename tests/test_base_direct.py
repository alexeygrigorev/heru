from pathlib import Path
import subprocess
import sys

from heru.base import (
    AdapterCapabilities,
    CLIExecutionResult,
    CLIInvocation,
    ExternalCLIAdapter,
    StreamEventAdapter,
    build_invocation_env,
)
from heru.types import EngineUsageWindow, LiveEvent, RuntimeEngineContinuation


def _write_script(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


class _LiveAdapter(ExternalCLIAdapter):
    LIVE_UPDATE_INTERVAL_SECONDS = 0.05

    def __init__(self, script: Path, *, stripped_env_vars: tuple[str, ...] = ()) -> None:
        super().__init__(
            name="stub",
            binary=sys.executable,
            capabilities=AdapterCapabilities(available=True, transcript_format="jsonl"),
            stripped_env_vars=stripped_env_vars,
        )
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
            stdin_data=prompt,
        )

    def stream_event_adapter(self):
        return StreamEventAdapter(
            live_events=lambda payload: [
                LiveEvent(kind="message", engine="stub", role="assistant", content=payload["text"])
            ]
            if payload.get("type") == "message"
            else [],
            continuation_id=lambda payload: payload.get("session_id")
            if payload.get("type") == "init"
            else None,
        )

    def extract_continuation(self, execution):
        return self.extract_continuation_from_payloads(
            execution,
            lambda payload: RuntimeEngineContinuation(session_id=payload["session_id"])
            if payload.get("type") == "init" and isinstance(payload.get("session_id"), str)
            else None,
        )


class _NoStdinLiveAdapter(_LiveAdapter):
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


class _HookAdapter(ExternalCLIAdapter):
    TRANSCRIPT_EMPTY_ON_PARSED_PAYLOADS = True
    USAGE_PROVIDER = "stub"

    def build_command(self, prompt, cwd, model=None, *, max_turns=None, resume_session_id=None):
        return [sys.executable, "-c", "print('unused')"]

    def transcript_assistant_text(self, execution):
        return ""

    def usage_window_from_payload(self, payload, metadata):
        if payload.get("type") != "usage":
            return None
        total_tokens = payload.get("total_tokens")
        if not isinstance(total_tokens, int):
            return None
        metadata["total_tokens"] = total_tokens
        return EngineUsageWindow(used=total_tokens, unit="tokens")

    def error_details_from_payload(self, payload):
        if payload.get("type") != "error":
            return None, {}, None
        message = payload.get("message")
        metadata = {"error_code": payload.get("code")} if payload.get("code") is not None else {}
        return message if isinstance(message, str) else None, metadata, None

    def update_usage_metadata_from_payload(self, payload, metadata) -> None:
        if payload.get("type") != "init":
            return
        session_id = payload.get("session_id")
        if isinstance(session_id, str) and session_id:
            metadata["session_id"] = session_id

    def continuation_from_payload(self, payload):
        if payload.get("type") != "init":
            return None
        session_id = payload.get("session_id")
        return RuntimeEngineContinuation(session_id=session_id) if isinstance(session_id, str) else None


def _execution(adapter: str, tmp_path: Path, stdout: str, *, stderr: str = "", exit_code: int = 0) -> CLIExecutionResult:
    return CLIExecutionResult(
        adapter=adapter,
        argv=(adapter, "run"),
        cwd=tmp_path,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_run_live_happy_path_streams_updates(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path / "live.py",
        "import sys, time\n"
        "sys.stdout.write('{\"type\":\"message\",\"text\":\"hello\"}\\n'); sys.stdout.flush(); time.sleep(0.1)\n"
        "sys.stdout.write('{\"type\":\"message\",\"text\":\" world\"}\\n'); sys.stdout.flush()\n",
    )
    adapter = _NoStdinLiveAdapter(script)
    updates: list[str] = []

    result = adapter.run_live(
        prompt="ignored",
        cwd=tmp_path,
        on_update=lambda execution: updates.append(execution.stdout),
    )

    assert result.exit_code == 0
    assert '{"type":"message","text":"hello"}' in result.stdout
    assert any("hello" in update for update in updates)


def test_run_live_emit_unified_renders_stream_events(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path / "unified.py",
        "import sys\n"
        "sys.stdout.write('{\"type\":\"init\",\"session_id\":\"sess-1\"}\\n')\n"
        "sys.stdout.write('{\"type\":\"message\",\"text\":\"hello\"}\\n')\n"
        "sys.stdout.flush()\n",
    )

    result = _LiveAdapter(script).run_live(prompt="ignored", cwd=tmp_path, emit_unified=True)

    assert '"kind":"message"' in result.stdout
    assert '"continuation_id":"sess-1"' in result.stdout


def test_run_live_times_out_on_stderr_only_noise(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path / "noise.py",
        "import sys, time\n"
        "while True:\n"
        "    sys.stderr.write('noise\\n'); sys.stderr.flush(); time.sleep(0.05)\n",
    )

    result = _LiveAdapter(script).run_live(
        prompt="ignored",
        cwd=tmp_path,
        inactivity_timeout_seconds=0.2,
    )

    assert "noise" in result.stderr
    assert "Process killed after 0s of inactivity." in result.stderr


def test_run_live_terminates_process_when_callback_raises(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path / "loop.py",
        "import sys, time\n"
        "sys.stdout.write('{\"type\":\"message\",\"text\":\"hello\"}\\n'); sys.stdout.flush()\n"
        "time.sleep(30)\n",
    )
    adapter = _NoStdinLiveAdapter(script)
    started: list[int] = []

    def on_update(_execution) -> None:
        raise RuntimeError("stop now")

    try:
        adapter.run_live(prompt="ignored", cwd=tmp_path, on_started=started.append, on_update=on_update)
    except RuntimeError as exc:
        assert str(exc) == "stop now"
    else:
        raise AssertionError("expected run_live to re-raise callback error")

    assert started
    assert subprocess.run(["bash", "-lc", f"kill -0 {started[0]}"], capture_output=True).returncode != 0


def test_build_invocation_env_strips_python_env_outside_workspace(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/venv")
    monkeypatch.setenv("CONDA_PREFIX", "/tmp/conda")
    monkeypatch.setenv("SECRET_TOKEN", "present")

    env = build_invocation_env(
        cwd=tmp_path,
        stripped_env_vars=("SECRET_TOKEN",),
        extra_env={"LITEHIVE_WORKSPACE_ROOT": str(tmp_path.parent / "other")},
    )

    assert "VIRTUAL_ENV" not in env
    assert "CONDA_PREFIX" not in env
    assert "SECRET_TOKEN" not in env


def test_build_invocation_env_keeps_python_env_inside_workspace(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/venv")

    env = build_invocation_env(
        cwd=tmp_path,
        extra_env={"LITEHIVE_WORKSPACE_ROOT": str(tmp_path.parent)},
    )

    assert env["VIRTUAL_ENV"] == "/tmp/venv"


def test_extract_continuation_from_run_live_output(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path / "continuation.py",
        "import sys\n"
        "sys.stdout.write('{\"type\":\"init\",\"session_id\":\"sess-123\"}\\n')\n"
        "sys.stdout.write('{\"type\":\"message\",\"text\":\"hello\"}\\n')\n"
        "sys.stdout.flush()\n",
    )
    adapter = _LiveAdapter(script)

    result = adapter.run_live(prompt="ignored", cwd=tmp_path)
    continuation = adapter.extract_continuation(result)

    assert continuation == RuntimeEngineContinuation(session_id="sess-123")


def test_render_transcript_uses_shared_payload_fallback(tmp_path: Path) -> None:
    adapter = _HookAdapter(name="hook", binary=sys.executable)

    transcript = adapter.render_transcript(
        _execution(
            "hook",
            tmp_path,
            '{"type":"init","session_id":"sess-123"}\n',
            stderr="stderr only",
        )
    )

    assert transcript == "[stderr]\nstderr only"


def test_usage_and_continuation_hooks_flow_through_base_adapter(tmp_path: Path) -> None:
    adapter = _HookAdapter(name="hook", binary=sys.executable)
    execution = _execution(
        "hook",
        tmp_path,
        "\n".join(
            [
                '{"type":"init","session_id":"sess-123"}',
                '{"type":"usage","total_tokens":7}',
                '{"type":"error","message":"rate limit exceeded","code":429}',
            ]
        ),
        exit_code=1,
    )

    observation = adapter.extract_usage_observation(execution)
    continuation = adapter.extract_continuation(execution)

    assert observation is not None
    assert observation.provider == "stub"
    assert observation.limit_reason == "rate limit reached"
    assert observation.usage is not None
    assert observation.usage.used == 7
    assert observation.metadata["error_code"] == 429
    assert observation.metadata["session_id"] == "sess-123"
    assert continuation == RuntimeEngineContinuation(session_id="sess-123")
