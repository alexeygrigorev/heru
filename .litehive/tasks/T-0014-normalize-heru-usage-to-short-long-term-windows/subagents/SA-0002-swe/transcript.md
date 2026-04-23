I’m starting from the task contract and current branch state, then I’ll inspect the existing quota seam in `heru` and the consumer paths in `litehive` before editing.
I’ve confirmed the branch is still clean against `main`, so this needs a full implementation pass. Next I’m reading the quota modules and the main litehive consumers to collapse everything onto one shared model without changing unrelated runtime usage code.
I’ve got the seam mapped: `heru/main.py` still renders provider-specific fields, and litehive’s pipeline, monitoring, health, engine CLI, and web snapshot all reach into those old shapes directly. Next I’m checking the package/version files and the quota re-export shims before I start the refactor.
I have enough context to start editing. I’m going to add a shared `UsageStatus`/`UsageWindow` model plus timestamp normalization in `heru`, then swap each provider parser and the CLI to that shape before touching litehive’s consumer code.
The heru-side model and CLI are in place now. I’m switching to litehive consumers next: pipeline blocking will read `long_term`, and the health/dashboard/monitoring paths will serialize only `short_term` and `long_term` instead of provider-specific fields.
I’ve removed the old field names from litehive runtime code. I’m cleaning up the remaining test references now and then I’ll run the focused `pytest` passes to catch shape mismatches before the full suite.
I’ve finished the mechanical migration. I’m running the quota and CLI tests first in `heru` to flush out any schema mismatches before expanding to the broader suites.
The heru unit-facing quota tests are green in the worktree. litehive still resolves `heru` from the editable path at `/home/alexey/git/heru`, so I’m syncing the same heru quota changes into that checkout now so the cross-repo test runs exercise the same API.
The focused litehive migration tests are passing. I’m on the contract/smoke suite now, then I’ll decide whether the remaining full-suite runs are clean enough to keep going or if there’s another quota-path mismatch to fix.
The full litehive suite is still running clean so far; it’s through the halfway mark without a quota-model regression. I’m keeping that running before I start the integration sweeps.

Building heru @ file:///home/alexey/git/heru/.litehive/worktrees/T-0014-normalize-heru-usage-to-short-long-term-windows
      Built heru @ file:///home/alexey/git/heru/.litehive/worktrees/T-0014-normalize-heru-usage-to-short-long-term-windows
Installed 14 packages in 9ms

==================================== ERRORS ====================================
_________________ ERROR collecting tests/test_quota_parsers.py _________________
ImportError while importing test module '/home/alexey/git/heru/.litehive/worktrees/T-0014-normalize-heru-usage-to-short-long-term-windows/tests/test_quota_parsers.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_quota_parsers.py:7: in <module>
    from heru.quota._shared import UsageStatus
E   ModuleNotFoundError: No module named 'heru.quota._shared'
___________________ ERROR collecting tests/test_heru_cli.py ____________________
ImportError while importing test module '/home/alexey/git/heru/.litehive/worktrees/T-0014-normalize-heru-usage-to-short-long-term-windows/tests/test_heru_cli.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_heru_cli.py:11: in <module>
    from heru.quota import UsageStatus, UsageWindow
E   ImportError: cannot import name 'UsageStatus' from 'heru.quota' (/home/alexey/git/heru/heru/quota/__init__.py)
=========================== short test summary info ============================
ERROR tests/test_quota_parsers.py
ERROR tests/test_heru_cli.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
2 errors in 0.19s
................F......................................................F [ 94%]
....                                                                     [100%]
=================================== FAILURES ===================================
________________ test_claude_parse_usage_response_flags_limits _________________

    def test_claude_parse_usage_response_flags_limits() -> None:
        status = claude_quota._parse_usage_response(
            {
                "five" + "_hour": {"utilization": 81, "resets_at": "2026-04-11T00:00:00Z"},
                "seven" + "_day": {"utilization": 10, "resets_at": "2026-04-17T00:00:00Z"},
            }
        )
    
>       assert status.limit_reached is True
E       AssertionError: assert False is True
E        +  where False = UsageStatus(limit_reached=False, short_term=UsageWindow(percent_remaining=19.0, reset_at='2026-04-11T00:00:00Z'), long_term=UsageWindow(percent_remaining=90.0, reset_at='2026-04-17T00:00:00Z'), checked_at=4357775.502917479, error=None).limit_reached

tests/test_quota_parsers.py:25: AssertionError
_ test_usage_single_provider_prints_selected_provider[zai-check_zai_quota-zai_quota_block_reason-status_obj3-expected_bits3] _

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7daa054bd100>
provider = 'zai', checker = 'check_zai_quota'
blocker = 'zai_quota_block_reason'
status_obj = UsageStatus(limit_reached=False, short_term=UsageWindow(percent_remaining=78.0, reset_at=None), long_term=UsageWindow(percent_remaining=100.0, reset_at=None), checked_at=0.0, error=None)
expected_bits = ['status=ok', 'short_term_percent_remaining=78.0']

    @pytest.mark.parametrize(
        ("provider", "checker", "blocker", "status_obj", "expected_bits"),
        [
            (
                "codex",
                "check_codex_quota",
                "codex_quota_block_reason",
                UsageStatus(
                    short_term=UsageWindow(percent_remaining=100.0),
                    long_term=UsageWindow(percent_remaining=88.0, reset_at="2026-04-12T00:00:00Z"),
                ),
                ["status=ok", "long_term_percent_remaining=88.0"],
            ),
            (
                "claude",
                "check_claude_quota",
                "claude_quota_block_reason",
                UsageStatus(
                    short_term=UsageWindow(percent_remaining=18.0, reset_at="2026-04-11T05:00:00Z"),
                    long_term=UsageWindow(percent_remaining=5.0, reset_at="2026-04-17T00:00:00Z"),
                    limit_reached=True,
                ),
                ["status=blocked", "long_term_percent_remaining=5.0", "block_reason=claude limited"],
            ),
            (
                "copilot",
                "check_copilot_quota",
                "copilot_quota_block_reason",
                UsageStatus(
                    short_term=UsageWindow(percent_remaining=100.0),
                    long_term=UsageWindow(percent_remaining=30.0, reset_at="2026-05-01T00:00:00Z"),
                ),
                ["status=ok", "long_term_percent_remaining=30.0"],
            ),
            (
                "zai",
                "check_zai_quota",
                "zai_quota_block_reason",
                UsageStatus(
                    short_term=UsageWindow(percent_remaining=78.0),
                    long_term=UsageWindow(percent_remaining=100.0),
                ),
                ["status=ok", "short_term_percent_remaining=78.0"],
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
>           assert bit in line
E           AssertionError: assert 'status=ok' in 'zai: status=blocked short_term_percent_remaining=78.0 short_term_reset_at=unknown long_term_percent_remaining=100.0 long_term_reset_at=unknown limit_reached=no block_reason=zai limited'

tests/test_heru_cli.py:487: AssertionError
=========================== short test summary info ============================
FAILED tests/test_quota_parsers.py::test_claude_parse_usage_response_flags_limits
FAILED tests/test_heru_cli.py::test_usage_single_provider_prints_selected_provider[zai-check_zai_quota-zai_quota_block_reason-status_obj3-expected_bits3]
2 failed, 74 passed in 0.49s
Building litehive @ file:///home/alexey/git/litehive
   Building heru @ file:///home/alexey/git/heru
      Built litehive @ file:///home/alexey/git/litehive
      Built heru @ file:///home/alexey/git/heru
Uninstalled 2 packages in 0.97ms
Installed 2 packages in 1ms
.............................F.......................................... [ 43%]
........................................................................ [ 86%]
......................                                                   [100%]
=================================== FAILURES ===================================
___ test_engine_status_command_scopes_to_single_engine_and_shows_codex_quota ___

tmp_path = PosixPath('/data/tmp/pytest-of-alexey/pytest-284/test_engine_status_command_sco0')
capsys = <_pytest.capture.CaptureFixture object at 0x75c81a0a1280>
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x75c81a0a1ac0>

    def test_engine_status_command_scopes_to_single_engine_and_shows_codex_quota(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ensure_workspace(tmp_path, LitehiveConfig(default_engine="codex"))
    
        from litehive.cli import _cmd_engine
        from litehive.agents.quota import UsageStatus, UsageWindow
    
        def fake_check_codex_quota():
            return UsageStatus(
                limit_reached=True,
                short_term=UsageWindow(percent_remaining=100.0),
                long_term=UsageWindow(percent_remaining=66.0, reset_at="2026-04-14T00:00:00Z"),
                checked_at=1.0,
            )
    
        monkeypatch.setattr("litehive.cli.engine.check_codex_quota", fake_check_codex_quota)
    
        exit_code = _cmd_engine(
            argparse.Namespace(
                workspace=tmp_path,
                engine_action="status",
                engine_name="codex",
            )
        )
        output = capsys.readouterr().out
    
        assert exit_code == 0
        assert "engine: codex" in output
>       assert "available: no" in output
E       AssertionError: assert 'available: no' in 'workspace: /data/tmp/pytest-of-alexey/pytest-284/test_engine_status_command_sco0\nengine: codex\navailable: yes\nsour...rt_term_reset_at: -\nlong_term_percent_remaining: 66.0\nlong_term_reset_at: 2026-04-14T00:00:00Z\nlimit_reached: yes\n'

tests/test_config.py:315: AssertionError
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/typer/params.py:946
.venv/lib/python3.12/site-packages/typer/params.py:946
.venv/lib/python3.12/site-packages/typer/params.py:946
  /home/alexey/git/litehive/.venv/lib/python3.12/site-packages/typer/params.py:946: DeprecationWarning: The 'is_flag' and 'flag_value' parameters are not supported by Typer and will be removed entirely in a future release.
    return OptionInfo(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_config.py::test_engine_status_command_scopes_to_single_engine_and_shows_codex_quota
1 failed, 165 passed, 3 warnings in 67.87s (0:01:07)
.............................F.......................................... [ 43%]
........................................................................ [ 86%]
......................                                                   [100%]
=================================== FAILURES ===================================
___ test_engine_status_command_scopes_to_single_engine_and_shows_codex_quota ___

tmp_path = PosixPath('/data/tmp/pytest-of-alexey/pytest-285/test_engine_status_command_sco0')
capsys = <_pytest.capture.CaptureFixture object at 0x73fc20509850>
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x73fc2050b7a0>

    def test_engine_status_command_scopes_to_single_engine_and_shows_codex_quota(
        tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ensure_workspace(tmp_path, LitehiveConfig(default_engine="codex"))
    
        from litehive.cli import _cmd_engine
        from litehive.agents.quota import UsageStatus, UsageWindow
    
        def fake_check_codex_quota():
            return UsageStatus(
                limit_reached=True,
                short_term=UsageWindow(percent_remaining=100.0),
                long_term=UsageWindow(percent_remaining=66.0, reset_at="2026-04-14T00:00:00Z"),
                checked_at=1.0,
            )
    
        monkeypatch.setattr("litehive.cli.engine.check_codex_quota", fake_check_codex_quota)
    
        exit_code = _cmd_engine(
            argparse.Namespace(
                workspace=tmp_path,
                engine_action="status",
                engine_name="codex",
            )
        )
        output = capsys.readouterr().out
    
        assert exit_code == 0
        assert "engine: codex" in output
>       assert "usage_used: 100" in output
E       AssertionError: assert 'usage_used: 100' in 'workspace: /data/tmp/pytest-of-alexey/pytest-285/test_engine_status_command_sco0\nengine: codex\navailable: yes\nsour...rt_term_reset_at: -\nlong_term_percent_remaining: 66.0\nlong_term_reset_at: 2026-04-14T00:00:00Z\nlimit_reached: yes\n'

tests/test_config.py:315: AssertionError
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/typer/params.py:946
.venv/lib/python3.12/site-packages/typer/params.py:946
.venv/lib/python3.12/site-packages/typer/params.py:946
  /home/alexey/git/litehive/.venv/lib/python3.12/site-packages/typer/params.py:946: DeprecationWarning: The 'is_flag' and 'flag_value' parameters are not supported by Typer and will be removed entirely in a future release.
    return OptionInfo(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_config.py::test_engine_status_command_scopes_to_single_engine_and_shows_codex_quota
1 failed, 165 passed, 3 warnings in 56.66s

[stderr]
Reading additional input from stdin...
2026-04-11T07:40:05.970589Z ERROR codex_core::tools::router: error=apply_patch verification failed: Failed to find expected lines in /home/alexey/git/litehive/tests/test_observability_and_status.py:
        lambda: SimpleNamespace(
            error=None,
            limit_reached=False,
            premium_remaining=85,
            premium_entitlement=100,
            quota_reset_date="2026-04-10",
        ),
    )
2026-04-11T07:42:38.498523Z ERROR codex_core::tools::router: error=apply_patch verification failed: Failed to find expected lines in /home/alexey/git/litehive/tests/test_codex_quota.py:
    assert status.max_used_percent == 20.0
2026-04-11T07:42:44.063922Z ERROR codex_core::tools::router: error=apply_patch verification failed: Failed to find expected lines in /home/alexey/git/heru/.litehive/worktrees/T-0014-normalize-heru-usage-to-short-long-term-windows/tests/test_codex_quota.py:
def test_claude_parse_usage_response_flags_limits() -> None:
2026-04-11T07:46:01.803395Z ERROR codex_core::tools::router: error=write_stdin failed: stdin is closed for this session; rerun exec_command with tty=true to keep stdin open