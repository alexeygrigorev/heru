from pathlib import Path
import selectors
import subprocess
from itertools import chain, repeat

import pytest

from heru.base import (
    AdapterCapabilities,
    CLIExecutionResult,
    CLIInvocation,
    ExternalCLIAdapter,
    StreamEventAdapter,
    build_invocation_env,
)
from heru.types import LiveEvent, RuntimeEngineContinuation


class ContractAdapter(ExternalCLIAdapter):
    LIVE_UPDATE_INTERVAL_SECONDS = 0.05

    def __init__(self) -> None:
        super().__init__(
            name="stub",
            binary="stub-bin",
            capabilities=AdapterCapabilities(available=True, transcript_format="jsonl"),
            stripped_env_vars=("SECRET_TOKEN",),
        )

    def build_command(self, prompt, cwd, model=None, *, max_turns=None, resume_session_id=None):
        command = [self.binary, "--cwd", str(cwd), prompt]
        if model:
            command.extend(["--model", model])
        if resume_session_id:
            command.extend(["--resume", resume_session_id])
        return command

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


class FakeCompletedProcess:
    def __init__(self, *, stdout: str, stderr: str, returncode: int, pid: int = 4321) -> None:
        self.pid = pid
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    def communicate(self, input=None):
        self.input = input
        return self._stdout, self._stderr


class FakeStream:
    def __init__(self, fileno_value: int, chunks: list[bytes]) -> None:
        self._fileno = fileno_value
        self.chunks = chunks
        self.closed = False

    def fileno(self) -> int:
        return self._fileno

    def read(self):
        data = b"".join(self.chunks)
        self.chunks.clear()
        return data

    def close(self) -> None:
        self.closed = True


class FakeLiveProcess:
    def __init__(self, stdout_chunks: list[bytes], stderr_chunks: list[bytes]) -> None:
        self.pid = 9876
        self.returncode = -15
        self.stdout = FakeStream(11, stdout_chunks)
        self.stderr = FakeStream(12, stderr_chunks)
        self.stdin = None
        self._terminated = False

    def poll(self):
        return self.returncode if self._terminated else None

    def terminate(self) -> None:
        self._terminated = True

    def wait(self, timeout=None):
        return self.returncode

    def kill(self) -> None:
        self._terminated = True


class FakeSelector:
    def __init__(self) -> None:
        self._registered: dict[int, tuple[FakeStream, str]] = {}

    def register(self, fileobj, _events, data=None):
        self._registered[fileobj.fileno()] = (fileobj, data)

    def unregister(self, fileobj):
        self._registered.pop(fileobj.fileno(), None)

    def get_map(self):
        return self._registered

    def select(self, timeout=None):
        del timeout
        for fileobj, data in self._registered.values():
            if fileobj.chunks:
                key = selectors.SelectorKey(
                    fileobj=fileobj,
                    fd=fileobj.fileno(),
                    events=selectors.EVENT_READ,
                    data=data,
                )
                return [(key, selectors.EVENT_READ)]
        return []

    def close(self) -> None:
        self._registered.clear()


def test_build_invocation_returns_public_cliinvocation(tmp_path: Path) -> None:
    invocation = ContractAdapter().build_invocation(
        "ship it",
        tmp_path,
        model="gpt-test",
        resume_session_id="sess-1",
        extra_env={"EXTRA_FLAG": "yes"},
    )

    assert isinstance(invocation, CLIInvocation)
    assert list(invocation.argv) == [
        "stub-bin",
        "--cwd",
        str(tmp_path),
        "ship it",
        "--model",
        "gpt-test",
        "--resume",
        "sess-1",
    ]
    assert invocation.stdin_data == "ship it"
    assert invocation.env["EXTRA_FLAG"] == "yes"


def test_build_invocation_env_strips_workspace_external_python_env(monkeypatch, tmp_path: Path) -> None:
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


def test_build_invocation_env_keeps_workspace_python_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/venv")

    env = build_invocation_env(
        cwd=tmp_path,
        extra_env={"LITEHIVE_WORKSPACE_ROOT": str(tmp_path.parent)},
    )

    assert env["VIRTUAL_ENV"] == "/tmp/venv"


def test_run_emits_unified_output_from_public_stream_adapter(monkeypatch, tmp_path: Path) -> None:
    process = FakeCompletedProcess(
        stdout='{"type":"init","session_id":"sess-1"}\n{"type":"message","text":"hello"}\n',
        stderr="",
        returncode=0,
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)

    result = ContractAdapter().run("ship it", tmp_path, emit_unified=True)

    assert result.exit_code == 0
    assert '"kind":"message"' in result.stdout
    assert '"continuation_id":"sess-1"' in result.stdout
    assert process.input == "ship it"


def test_run_live_enforces_stdout_inactivity_timeout(monkeypatch, tmp_path: Path) -> None:
    process = FakeLiveProcess([b'{"type":"message","text":"hello"}\n'], [])
    streams = {
        process.stdout.fileno(): process.stdout,
        process.stderr.fileno(): process.stderr,
    }
    monotonic_values = chain([0.0, 0.0, 0.0, 0.2, 0.2, 0.2, 0.4, 0.4], repeat(0.4))

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(selectors, "DefaultSelector", FakeSelector)
    monkeypatch.setattr(
        "heru.base.os.read",
        lambda fileno, _size: streams[fileno].chunks.pop(0) if streams[fileno].chunks else b"",
    )
    monkeypatch.setattr("heru.base.time.monotonic", lambda: next(monotonic_values))

    result = ContractAdapter().run_live(
        "ship it",
        tmp_path,
        inactivity_timeout_seconds=0.1,
    )

    assert "hello" in result.stdout
    assert "Process killed after 0s of inactivity." in result.stderr
    assert result.exit_code == -15


def test_extract_continuation_reads_public_runtime_handle(tmp_path: Path) -> None:
    result = ContractAdapter().extract_continuation(
        CLIExecutionResult(
            adapter="stub",
            argv=("stub-bin",),
            cwd=tmp_path,
            exit_code=0,
            stdout='{"type":"init","session_id":"sess-123"}\n',
            stderr="",
        )
    )

    assert result == RuntimeEngineContinuation(session_id="sess-123")
