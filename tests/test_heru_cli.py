import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import heru.quota as heru_quota
from heru import ENGINE_CHOICES, get_engine
from heru.base import CLIExecutionResult
from heru.main import app, main
from heru.quota.claude_quota import ClaudeQuotaStatus, ClaudeQuotaWindow
from heru.quota.codex_quota import CodexQuotaStatus, CodexQuotaWindow
from heru.quota.copilot_quota import CopilotQuotaStatus
from heru.quota.zai_quota import ZaiQuotaStatus, ZaiQuotaWindow


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
def test_engine_subcommands_forward_continue_flag(
    monkeypatch,
    tmp_path: Path,
    engine_name: str,
) -> None:
    engine = get_engine(engine_name)
    if not engine.supports_continue_latest():
        assert main([engine_name, "ship it", "--continue"]) == 1
        return

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
        calls["resume_session_id"] = resume_session_id
        return CLIExecutionResult(
            adapter=engine_name,
            argv=(engine_name, prompt),
            cwd=cwd,
            exit_code=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(engine, "run", fake_run)

    exit_code = main([engine_name, "ship it", "--cwd", str(tmp_path), "--continue"])

    assert exit_code == 0
    assert calls == {"resume_session_id": "__heru_continue_latest__"}


@pytest.mark.parametrize("engine_name", ENGINE_CHOICES)
def test_engine_subcommands_reject_resume_and_continue_together(engine_name: str) -> None:
    exit_code = main([engine_name, "ship it", "--resume", "session-123", "--continue"])

    assert exit_code == 1


@pytest.mark.parametrize("engine_name", [name for name in ENGINE_CHOICES if not get_engine(name).supports_continue_latest()])
def test_engine_subcommands_reject_continue_when_engine_requires_explicit_id(engine_name: str) -> None:
    exit_code = main([engine_name, "ship it", "--continue"])

    assert exit_code == 1


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
    for option in ("--cwd", "--model", "--max-turns", "--resume", "--continue", "--raw"):
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


def test_legacy_engine_flag_supports_continue(monkeypatch, tmp_path: Path) -> None:
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
        calls["resume_session_id"] = resume_session_id
        return CLIExecutionResult(
            adapter="claude",
            argv=("claude", prompt),
            cwd=cwd,
            exit_code=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(engine, "run", fake_run)

    exit_code = main(["ship it", "--engine", "claude", "--continue", "--cwd", str(tmp_path)])

    assert exit_code == 0
    assert calls == {"resume_session_id": "__heru_continue_latest__"}


@pytest.mark.parametrize("engine_name", ENGINE_CHOICES)
def test_cli_resume_flow_reuses_continuation_id(monkeypatch, capsys, tmp_path: Path, engine_name: str) -> None:
    engine = get_engine(engine_name)
    latest_by_engine: dict[str, str] = {}
    prompts_by_session: dict[str, str] = {}

    def fake_run(
        prompt: str,
        cwd: Path,
        model: str | None = None,
        *,
        max_turns: int | None = None,
        resume_session_id: str | None = None,
        emit_unified: bool = False,
    ) -> CLIExecutionResult:
        assert emit_unified is True
        if resume_session_id in (None, "__heru_continue_latest__"):
            session_id = latest_by_engine.get(engine_name, f"{engine_name}-session-1")
            prior_prompt = prompts_by_session.get(session_id)
        else:
            session_id = resume_session_id
            prior_prompt = prompts_by_session.get(session_id)
        if prior_prompt is None:
            message = f"{engine_name} heard: {prompt}"
        else:
            message = f"{engine_name} earlier discussed: {prior_prompt}"
        latest_by_engine[engine_name] = session_id
        prompts_by_session.setdefault(session_id, prompt)
        stdout = "\n".join(
            [
                json.dumps({"kind": "message", "engine": engine_name, "sequence": 0, "content": message}),
                json.dumps(
                    {
                        "kind": "continuation",
                        "engine": engine_name,
                        "sequence": 1,
                        "continuation_id": session_id,
                    }
                ),
            ]
        ) + "\n"
        return CLIExecutionResult(
            adapter=engine_name,
            argv=(engine_name, prompt),
            cwd=cwd,
            exit_code=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(engine, "run", fake_run)

    assert main([engine_name, "hi", "--cwd", str(tmp_path)]) == 0
    first_run = capsys.readouterr()
    continuation_id = json.loads(first_run.out.splitlines()[-1])["continuation_id"]

    assert main([engine_name, "what did we discuss", "--resume", continuation_id, "--cwd", str(tmp_path)]) == 0
    second_run = capsys.readouterr()
    second_events = [json.loads(line) for line in second_run.out.splitlines()]

    assert second_events[0]["content"] == f"{engine_name} earlier discussed: hi"
    assert second_events[-1]["continuation_id"] == continuation_id


def test_usage_without_provider_prints_supported_providers(monkeypatch, capsys) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        heru_quota,
        "check_codex_quota",
        lambda: CodexQuotaStatus(
            primary_window=CodexQuotaWindow(used_percent=62.0, reset_at="2026-04-11T00:00:00Z"),
            secondary_window=CodexQuotaWindow(used_percent=48.0, reset_at="2026-04-12T00:00:00Z"),
        ),
    )
    monkeypatch.setattr(heru_quota, "codex_quota_block_reason", lambda: None)
    monkeypatch.setattr(
        heru_quota,
        "check_claude_quota",
        lambda: ClaudeQuotaStatus(
            five_hour=ClaudeQuotaWindow(used_percent=51.0, reset_at="2026-04-11T05:00:00Z"),
            seven_day=ClaudeQuotaWindow(used_percent=20.0, reset_at="2026-04-17T00:00:00Z"),
        ),
    )
    monkeypatch.setattr(heru_quota, "claude_quota_block_reason", lambda: None)
    monkeypatch.setattr(
        heru_quota,
        "check_copilot_quota",
        lambda: CopilotQuotaStatus(
            premium_remaining=7,
            premium_entitlement=20,
            premium_percent_remaining=35.0,
            quota_reset_date="2026-05-01",
        ),
    )
    monkeypatch.setattr(heru_quota, "copilot_quota_block_reason", lambda: None)
    monkeypatch.setattr(
        heru_quota,
        "check_zai_quota",
        lambda: ZaiQuotaStatus(
            api_calls=ZaiQuotaWindow(used_percent=33.0, window_hours=1, remaining=67, limit=100),
            tokens=ZaiQuotaWindow(used_percent=50.0, window_hours=24, remaining=500, limit=1000),
        ),
    )
    monkeypatch.setattr(heru_quota, "zai_quota_block_reason", lambda: None)

    result = runner.invoke(app, ["usage"])

    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert [line.split(":", 1)[0] for line in lines] == ["codex", "claude", "copilot", "zai"]
    assert "used=62.0" in lines[0]
    assert "limit=100.0" in lines[0]
    assert "remaining=38.0" in lines[0]
    assert "unit=percent" in lines[0]
    assert "reset_window=primary_window" in lines[0]
    assert "used=51.0" in lines[1]
    assert "reset_window=five_hour" in lines[1]
    assert "used=65.0" in lines[2]
    assert "limit=20" in lines[2]
    assert "remaining=7" in lines[2]
    assert "unit=premium_interactions" in lines[2]
    assert "used=500" in lines[3]
    assert "limit=1000" in lines[3]
    assert "remaining=500" in lines[3]
    assert "unit=tokens" in lines[3]
    assert "reset_window=24h" in lines[3]


@pytest.mark.parametrize(
    ("provider", "checker", "blocker", "status_obj", "expected_bits"),
    [
        (
            "codex",
            "check_codex_quota",
            "codex_quota_block_reason",
            CodexQuotaStatus(
                primary_window=CodexQuotaWindow(used_percent=45.0, reset_at="2026-04-11T00:00:00Z"),
                secondary_window=CodexQuotaWindow(used_percent=12.0, reset_at="2026-04-12T00:00:00Z"),
            ),
            ["status=ok", "used=45.0", "reset_window=primary_window"],
        ),
        (
            "claude",
            "check_claude_quota",
            "claude_quota_block_reason",
            ClaudeQuotaStatus(
                five_hour=ClaudeQuotaWindow(used_percent=82.0, reset_at="2026-04-11T05:00:00Z"),
                seven_day=ClaudeQuotaWindow(used_percent=30.0, reset_at="2026-04-17T00:00:00Z"),
            ),
            ["status=blocked", "used=82.0", "block_reason=claude limited"],
        ),
        (
            "copilot",
            "check_copilot_quota",
            "copilot_quota_block_reason",
            CopilotQuotaStatus(
                premium_remaining=3,
                premium_entitlement=10,
                premium_percent_remaining=30.0,
                quota_reset_date="2026-05-01",
            ),
            ["status=ok", "used=70.0", "reset_window=monthly"],
        ),
        (
            "zai",
            "check_zai_quota",
            "zai_quota_block_reason",
            ZaiQuotaStatus(
                api_calls=ZaiQuotaWindow(used_percent=81.0, window_hours=1, remaining=19, limit=100),
                tokens=ZaiQuotaWindow(used_percent=22.0, window_hours=24, remaining=780, limit=1000),
            ),
            ["status=blocked", "used=81", "block_reason=zai limited"],
        ),
    ],
)
def test_usage_single_provider_prints_selected_provider(
    monkeypatch,
    provider: str,
    checker: str,
    blocker: str,
    status_obj: object,
    expected_bits: list[str],
) -> None:
    runner = CliRunner()
    monkeypatch.setattr(heru_quota, checker, lambda: status_obj)
    monkeypatch.setattr(
        heru_quota,
        blocker,
        lambda: "claude limited" if provider == "claude" else "zai limited" if provider == "zai" else None,
    )

    result = runner.invoke(app, ["usage", provider])

    assert result.exit_code == 0
    line = result.stdout.strip()
    assert line.startswith(f"{provider}:")
    for bit in expected_bits:
        assert bit in line


def test_usage_gemini_reports_unsupported() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["usage", "gemini"])

    assert result.exit_code == 0
    assert "gemini: status=unsupported" in result.stdout
    assert "error=unsupported" in result.stdout


def test_usage_unknown_provider_exits_non_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["usage", "wat"])

    assert result.exit_code == 1
    assert "Unknown provider 'wat'." in result.stderr
    for provider in ("codex", "claude", "copilot", "zai", "gemini"):
        assert provider in result.stderr


def test_usage_reports_missing_auth_without_crashing(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        heru_quota,
        "check_codex_quota",
        lambda: CodexQuotaStatus(error="no auth token"),
    )
    monkeypatch.setattr(heru_quota, "codex_quota_block_reason", lambda: None)

    result = runner.invoke(app, ["usage", "codex"])

    assert result.exit_code == 0
    assert "codex: status=error" in result.stdout
    assert "error=no auth token" in result.stdout
    assert "used=unknown" in result.stdout


def test_usage_json_outputs_json_objects(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        heru_quota,
        "check_copilot_quota",
        lambda: CopilotQuotaStatus(
            premium_remaining=2,
            premium_entitlement=10,
            premium_percent_remaining=20.0,
            quota_reset_date="2026-05-01",
        ),
    )
    monkeypatch.setattr(
        heru_quota,
        "copilot_quota_block_reason",
        lambda: "copilot premium requests low",
    )

    result = runner.invoke(app, ["usage", "copilot", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["provider"] == "copilot"
    assert payload["status"] == "blocked"
    assert payload["used"] == 80.0
    assert payload["limit"] == 10
    assert payload["remaining"] == 2
    assert payload["unit"] == "premium_interactions"
    assert payload["reset_window"] == "monthly"
    assert payload["block_reason"] == "copilot premium requests low"
