from pathlib import Path

import pytest
from typer.testing import CliRunner

from heru import ENGINE_CHOICES, get_engine
from heru.base import CLIExecutionResult
from heru.main import app, main


def test_heru_registry_exposes_all_engines() -> None:
    expected = {"codex", "claude", "copilot", "gemini", "opencode", "goz"}
    assert expected.issubset(set(ENGINE_CHOICES))
    for engine_name in expected:
        engine = get_engine(engine_name)
        assert engine.name == engine_name


@pytest.mark.parametrize("engine_name", ENGINE_CHOICES)
def test_engine_subcommands_forward_common_options(
    monkeypatch,
    capsys,
    tmp_path: Path,
    engine_name: str,
) -> None:
    engine = get_engine(engine_name)
    calls: dict[str, object] = {}

    def fake_run(
        prompt: str,
        cwd: Path,
        model: str | None = None,
        *,
        max_turns: int | None = None,
        resume_session_id: str | None = None,
        emit_unified: bool = False,
    ) -> CLIExecutionResult:
        calls.update(
            prompt=prompt,
            cwd=cwd,
            model=model,
            max_turns=max_turns,
            resume_session_id=resume_session_id,
            emit_unified=emit_unified,
        )
        return CLIExecutionResult(
            adapter=engine_name,
            argv=(engine_name, prompt),
            cwd=cwd,
            exit_code=7,
            stdout=f"{engine_name}:done\n",
            stderr=f"{engine_name}:stderr\n",
        )

    monkeypatch.setattr(engine, "run", fake_run)

    exit_code = main(
        [
            engine_name,
            "ship it",
            "--cwd",
            str(tmp_path),
            "--model",
            f"{engine_name}-model",
            "--max-turns",
            "3",
            "--resume",
            "session-123",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 7
    assert captured.out == f"{engine_name}:done\n"
    assert captured.err == f"{engine_name}:stderr\n"
    assert calls == {
        "prompt": "ship it",
        "cwd": tmp_path.resolve(),
        "model": f"{engine_name}-model",
        "max_turns": 3,
        "resume_session_id": "session-123",
        "emit_unified": True,
    }


@pytest.mark.parametrize("engine_name", ENGINE_CHOICES)
def test_engine_subcommands_raw_flag_disables_unified_output(
    monkeypatch,
    capsys,
    tmp_path: Path,
    engine_name: str,
) -> None:
    engine = get_engine(engine_name)
    calls: dict[str, object] = {}

    def fake_run(
        prompt: str,
        cwd: Path,
        model: str | None = None,
        *,
        max_turns: int | None = None,
        resume_session_id: str | None = None,
        emit_unified: bool = False,
    ) -> CLIExecutionResult:
        calls["emit_unified"] = emit_unified
        return CLIExecutionResult(
            adapter=engine_name,
            argv=(engine_name, prompt),
            cwd=cwd,
            exit_code=0,
            stdout='{"native":true}\n',
            stderr="",
        )

    monkeypatch.setattr(engine, "run", fake_run)

    exit_code = main([engine_name, "ship it", "--cwd", str(tmp_path), "--raw"])

    assert exit_code == 0
    assert capsys.readouterr().out == '{"native":true}\n'
    assert calls == {"emit_unified": False}


def test_root_help_lists_registered_engines() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for engine_name in ENGINE_CHOICES:
        assert engine_name in result.stdout


@pytest.mark.parametrize("engine_name", ENGINE_CHOICES)
def test_engine_help_shows_shared_options(engine_name: str) -> None:
    runner = CliRunner()

    result = runner.invoke(app, [engine_name, "--help"])

    assert result.exit_code == 0
    for option in ("--cwd", "--model", "--max-turns", "--resume", "--raw"):
        assert option in result.stdout


def test_legacy_engine_flag_still_runs_with_deprecation_warning(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    engine = get_engine("claude")
    calls: dict[str, object] = {}

    def fake_run(
        prompt: str,
        cwd: Path,
        model: str | None = None,
        *,
        max_turns: int | None = None,
        resume_session_id: str | None = None,
        emit_unified: bool = False,
    ) -> CLIExecutionResult:
        calls.update(
            prompt=prompt,
            cwd=cwd,
            model=model,
            max_turns=max_turns,
            resume_session_id=resume_session_id,
            emit_unified=emit_unified,
        )
        return CLIExecutionResult(
            adapter="claude",
            argv=("claude", prompt),
            cwd=cwd,
            exit_code=0,
            stdout="done\n",
            stderr="engine stderr\n",
        )

    monkeypatch.setattr(engine, "run", fake_run)

    exit_code = main(
        [
            "ship it",
            "--engine",
            "claude",
            "--cwd",
            str(tmp_path),
            "--model",
            "claude-sonnet-4-20250514",
            "--max-turns",
            "3",
            "--resume-session-id",
            "session-123",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "done\n"
    assert "Deprecation warning:" in captured.err
    assert "engine stderr\n" in captured.err
    assert calls == {
        "prompt": "ship it",
        "cwd": tmp_path.resolve(),
        "model": "claude-sonnet-4-20250514",
        "max_turns": 3,
        "resume_session_id": "session-123",
        "emit_unified": True,
    }
