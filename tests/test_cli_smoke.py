import json
import os
from pathlib import Path
import subprocess
import sys


def _write_engine(path: Path, payloads: list[str], *, stderr: str = "", exit_code: int = 0) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        "capture = pathlib.Path(os.environ['HERU_CAPTURE_PATH'])\n"
        "capture.write_text(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd()}), encoding='utf-8')\n"
        + "".join(f"sys.stdout.write({payload!r} + '\\n')\n" for payload in payloads)
        + (f"sys.stderr.write({stderr!r})\n" if stderr else "")
        + "sys.stdout.flush()\n"
        + f"raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_cli(tmp_path: Path, engine_name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    capture = tmp_path / f"{engine_name}-capture.json"
    env = dict(**os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", HERU_CAPTURE_PATH=str(capture))
    return subprocess.run(
        [sys.executable, "-m", "heru.main", engine_name, *args],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
    )


def test_cli_smoke_emits_unified_output_from_fake_codex_binary(tmp_path: Path) -> None:
    _write_engine(
        tmp_path / "codex",
        [
            '{"type":"thread.started","thread_id":"thread-123"}',
            '{"type":"item.completed","item":{"id":"msg-1","type":"agent_message","text":"hello from codex"}}',
        ],
        stderr="codex stderr\n",
    )
    capture = tmp_path / "codex-capture.json"
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", HERU_CAPTURE_PATH=str(capture))

    result = subprocess.run(
        [sys.executable, "-m", "heru.main", "codex", "ship it", "--cwd", str(tmp_path)],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
    )

    lines = [json.loads(line) for line in result.stdout.splitlines()]
    recorded = json.loads(capture.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert [line["kind"] for line in lines] == ["message", "continuation"]
    assert recorded["cwd"] == str(tmp_path.resolve())
    assert "--cd" in recorded["argv"]
    assert result.stderr == "codex stderr\n"


def test_cli_smoke_raw_output_preserves_fake_gemini_jsonl(tmp_path: Path) -> None:
    _write_engine(
        tmp_path / "gemini",
        [
            '{"type":"init","session_id":"gemini-session"}',
            '{"type":"content","text":"hello raw"}',
        ],
    )
    capture = tmp_path / "gemini-capture.json"
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", HERU_CAPTURE_PATH=str(capture))

    result = subprocess.run(
        [sys.executable, "-m", "heru.main", "gemini", "ship it", "--cwd", str(tmp_path), "--raw"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines()[0] == '{"type":"init","session_id":"gemini-session"}'
    assert "--yolo" in json.loads(capture.read_text(encoding="utf-8"))["argv"]


def test_cli_smoke_continue_flag_reaches_fake_opencode_binary(tmp_path: Path) -> None:
    _write_engine(tmp_path / "opencode", ['{"type":"text","sessionID":"sess-1","part":{"text":"hello"}}'])
    capture = tmp_path / "opencode-capture.json"
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", HERU_CAPTURE_PATH=str(capture))

    result = subprocess.run(
        [sys.executable, "-m", "heru.main", "opencode", "ship it", "--cwd", str(tmp_path), "--continue"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
    )

    argv = json.loads(capture.read_text(encoding="utf-8"))["argv"]

    assert result.returncode == 0
    assert "--continue" in argv
