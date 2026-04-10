Validating the claimed acceptance evidence against the repo state now. I’m checking the contract suite, README language, and a few representative tests before issuing the reviewer verdict and reporting it through `litehive`.
The contract suite is present and pytest is collecting 59 cases from it, which clears the directory/discovery requirement. I’m reading the README wording and spot-checking the contract tests for fixture-only behavior before I lock the verdict.
The spot-check matches the implementation claims: the README has the semver-major language, and the contract tests are fixture/stub based rather than integration tests. I’m rerunning the key verification commands now so the acceptance verdict is based on fresh evidence from this workspace, not only prior stage notes.
Fresh verification is coming back clean in heru: the standalone contract suite passes, and the full local pytest run still passes with the new directory included. I’m waiting on the litehive smoke command to finish so the reviewer report can explicitly confirm the editable-install contract stayed intact.
Acceptance criteria are satisfied based on current workspace evidence. I’m submitting a `pass` verdict with the concrete verification summary so the task record reflects exactly what was checked.
Accepted.

I verified the repo state directly: `tests/contract/` exists with 59 collected cases across 30 test functions, covering the public API surface requested, and the tests are fixture/stub-based rather than real engine or network integrations. The README now explicitly marks `tests/contract/` as the semver-major “thou shalt not break” suite and includes the required checklist.

Fresh reviewer verification passed:
- `uv run pytest --collect-only -q tests/contract`
- `uv run pytest -q tests/contract` -> 59 passed
- `uv run pytest -q` -> 232 passed
- `cd ~/git/litehive && uv run pytest tests/test_runner_workflow.py tests/test_engine_variants_and_timeline.py tests/test_heru_cli.py tests/test_codex_quota.py -q` -> 197 passed, 3 warnings

I also submitted the required `litehive report --verdict pass --role reviewer --step accepting ...`.

[stderr]
Reading additional input from stdin...
