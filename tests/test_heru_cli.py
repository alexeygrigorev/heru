from pathlib import Path

from heru import ENGINE_CHOICES, get_engine
from heru.base import CLIExecutionResult
from heru.main import main


def test_heru_registry_exposes_all_engines() -> None:
    expected = {"codex", "claude", "copilot", "gemini", "opencode", "goz"}
    assert expected.issubset(set(ENGINE_CHOICES))
    for engine_name in expected:
        engine = get_engine(engine_name)
        assert engine.name == engine_name


def test_heru_cli_runs_selected_engine(monkeypatch, capsys, tmp_path: Path) -> None:
    engine = get_engine("claude")
    calls: dict[str, object] = {}

    def fake_run(
        prompt: str,
        cwd: Path,
        model: str | None = None,
        *,
        max_turns: int | None = None,
        resume_session_id: str | None = None,
    ):
        calls.update(
            prompt=prompt,
            cwd=cwd,
            model=model,
            max_turns=max_turns,
            resume_session_id=resume_session_id,
        )
        return CLIExecutionResult(
            adapter="claude",
            argv=("claude", "-p", prompt),
            cwd=cwd,
            exit_code=0,
            stdout="done\n",
            stderr="",
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

    assert exit_code == 0
    assert capsys.readouterr().out == "done\n"
    assert calls == {
        "prompt": "ship it",
        "cwd": tmp_path.resolve(),
        "model": "claude-sonnet-4-20250514",
        "max_turns": 3,
        "resume_session_id": "session-123",
    }
