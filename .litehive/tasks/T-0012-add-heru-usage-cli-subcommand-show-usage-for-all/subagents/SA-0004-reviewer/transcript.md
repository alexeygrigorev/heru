Reviewing the implementation against the acceptance criteria now. I’m checking the CLI entrypoint, the new tests, and the README, then I’ll rerun the relevant pytest coverage and submit the acceptance verdict through `litehive report`.
The command wiring is in place. I’m reading the normalization and formatting logic now to confirm the output shape matches the acceptance criteria rather than only trusting the test names.
The formatter and normalization layer match the intended CLI seam. I’m running the focused CLI tests plus the required broader suites to verify the implementation behaves as claimed, not just that the code exists.
The focused CLI coverage passed. I’m running the full heru suite and the required litehive contract smoke suite now, since acceptance depends on verifying there’s no regression outside the new subcommand.
The heru suite passed cleanly. I’m waiting on the litehive smoke run to finish so the acceptance report can include the contract-regression evidence the task explicitly requires.
Verification is complete. I’m submitting a pass verdict with the concrete evidence the next stage needs: the command surface reviewed, the behaviors confirmed, and the exact test runs that passed.
Accepted and reported via `litehive report`.

I verified the new `heru usage` CLI behavior in [heru/main.py](/home/alexey/git/heru/.litehive/worktrees/T-0012-add-heru-usage-cli-subcommand-show-usage-for-all/heru/main.py), the fixture-driven coverage in [tests/test_heru_cli.py](/home/alexey/git/heru/.litehive/worktrees/T-0012-add-heru-usage-cli-subcommand-show-usage-for-all/tests/test_heru_cli.py), and the docs in [README.md](/home/alexey/git/heru/.litehive/worktrees/T-0012-add-heru-usage-cli-subcommand-show-usage-for-all/README.md). The command covers all-provider output, single-provider output, `gemini` as `unsupported`, helpful unknown-provider failure, provider-specific auth errors, and `--json`.

Verification evidence:
- `uv run pytest tests/test_heru_cli.py -q` -> 50 passed
- `uv run pytest tests/test_cli_smoke.py -q` -> 3 passed
- `uv run pytest tests/ -q` -> 243 passed
- In `~/git/litehive`: `uv run pytest tests/test_runner_workflow.py tests/test_engine_variants_and_timeline.py tests/test_heru_cli.py tests/test_codex_quota.py -q` -> 198 passed, 3 Typer deprecation warnings only

No acceptance gaps found.

[stderr]
Reading additional input from stdin...
