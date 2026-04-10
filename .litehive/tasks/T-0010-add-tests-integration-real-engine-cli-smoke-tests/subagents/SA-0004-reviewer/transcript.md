Reviewing the implementation against the acceptance criteria now. I’m checking the new integration suite structure, verifying the skip and resume seams in the code, and rerunning the required validation commands before I decide pass vs reject.
The required default and downstream suites are running cleanly so far. Next I’m reading the helper and per-engine tests to verify they actually use the public adapter seam, honor the env gates, and cover continuation behavior where required.
The helper layer matches the intended seam: the tests launch real subprocesses through `get_engine(...)->build_invocation(...)->finalize_invocation(...)->subprocess.run(...)`, then assert against `render_transcript(...)` and extracted continuations. I’m doing one more pass on the integration fixtures and adapter resume handling before I lock the verdict.
The code and validation evidence are consistent with the task: structure is present, the helper centralizes env/PATH/quota gating, continuation coverage matches the adapter capabilities, and the default plus downstream contract suites are still green. I’m submitting an acceptance report with the concrete verification evidence now.
Accepted and reported.

I verified the new `tests_integration/` suite exists with the required files, confirmed there are no `litehive` imports, and inspected the helper/per-engine tests to ensure they use the public adapter seam: `get_engine(...) -> build_invocation(...) -> finalize_invocation(...) -> subprocess.run(...) -> render_transcript(...)`, with continuation coverage aligned to each adapter’s contract.

Validation rerun in review:
- `uv run pytest tests/ -q` -> `234 passed`
- `uv run pytest tests_integration/test_codex.py -q` with `HERU_INTEGRATION_ENGINES` unset -> `2 skipped`
- `cd /home/alexey/git/litehive && uv run pytest tests/test_runner_workflow.py tests/test_engine_variants_and_timeline.py tests/test_heru_cli.py tests/test_codex_quota.py -q` -> `197 passed`

I also confirmed `tests_integration/README.md` and `CLAUDE.md` document the `tests/` vs `tests_integration/` split and the `HERU_INTEGRATION_ENGINES` / `HERU_INTEGRATION_TIMEOUT_SECONDS` env vars.

/home/alexey/git/heru/.litehive/worktrees/T-0010-add-tests-integration-real-engine-cli-smoke-tests
tests_integration/helpers.py
tests_integration/test_gemini.py
tests_integration/test_goz.py
tests_integration/test_opencode.py
tests_integration/test_copilot.py
tests_integration/test_codex.py
tests_integration/README.md
tests_integration/test_claude.py
tests_integration/__init__.py
tests_integration/conftest.py

[stderr]
Reading additional input from stdin...
