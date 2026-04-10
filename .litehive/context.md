# heru — Litehive Workspace Context

Process profile: Python

You are editing **heru**, a unified headless CLI for coding agents
(codex, claude, copilot, gemini, opencode, goz). Read this whole file
before touching any file in this repository.

## Project

- **Purpose:** a thin adapter layer that wraps each supported agent CLI
  behind a uniform Python interface, with a unified `heru <engine>
  <prompt>` command, one JSONL event schema across engines, and one
  resume mechanism. heru is the engine-I/O layer; it knows nothing
  about task queues, stages, orchestration, or sandboxing — those are
  litehive concerns.
- **Main package:** `heru/` (at the repo root, below `.git/`). Public
  API lives in `heru/__init__.py`, `heru/base.py`, `heru/types.py`,
  and each `heru/adapters/<engine>.py`. Anything prefixed with `_` is
  internal.
- **Commands to know:**
  - `uv sync --extra dev` — install heru's own venv
  - `uv run pytest` — heru's standalone test suite
  - `uv run heru <engine> <prompt>` — the CLI (WIP per task T-0002)
  - `cd ~/git/litehive && uv run pytest -q tests/test_runner_workflow.py tests/test_engine_variants_and_timeline.py tests/test_heru_cli.py tests/test_codex_quota.py` — **litehive contract smoke tests; run before every commit**

## Directory layout

```
heru/
├── heru/                  # the Python package
│   ├── __init__.py        # get_engine, ENGINE_CHOICES — PUBLIC
│   ├── base.py            # ExternalCLIAdapter, CLIInvocation, run_live — PUBLIC
│   ├── types.py           # shared pydantic types — PUBLIC
│   ├── main.py            # `heru <engine> <prompt>` CLI entry — PUBLIC
│   ├── _engine_detection.py   # internal
│   ├── _continuation.py       # internal
│   ├── adapters/
│   │   ├── codex.py, _codex_impl.py         # CodexCLIAdapter PUBLIC, _impl internal
│   │   ├── claude.py, _claude_impl.py
│   │   ├── copilot.py, _copilot_impl.py
│   │   ├── gemini.py, _gemini_impl.py
│   │   ├── opencode.py, _opencode_impl.py
│   │   ├── goz.py, _goz_impl.py
│   │   └── common.py      # shared helpers
│   └── quota/             # per-provider quota check helpers — PUBLIC
├── tests/                 # heru's standalone unit tests (no litehive imports)
├── pyproject.toml
├── README.md
└── .litehive/             # this workspace (tasks, state)
```

## Public API surface — do not break without a semver bump

Anything **not** prefixed with `_` is public. Changing the signature,
return type, or behavior of any of the following is a **semver-major**
breaking change that requires a version bump in `pyproject.toml`, a
CHANGELOG entry, and a migration note for litehive:

- `heru.get_engine(name)`, `heru.ENGINE_CHOICES`
- `heru.base.ExternalCLIAdapter` (subclass, don't modify shape)
- `heru.base.CLIInvocation`, `heru.base.CLIExecutionResult`
- Each adapter class: `CodexCLIAdapter`, `ClaudeCLIAdapter`,
  `CopilotCLIAdapter`, `GeminiCLIAdapter`, `OpencodeCLIAdapter`,
  `GozCLIAdapter`
- Every pydantic model in `heru/types.py`
- `heru.main.main` (the CLI entry)

**Internal** (change freely, no semver implications): every
`_`-prefixed module, every private method on public classes, and the
exact text of rendered transcripts.

## Hard rules — do NOT break these

1. **No imports from `litehive`.** heru is a leaf package. One runtime
   dep: `pydantic`. If your diff adds `from litehive …`, stop — the
   code belongs in litehive, not heru.

2. **Do not break litehive.** litehive depends on heru via an editable
   path install, so every heru change propagates immediately. Before
   you finish any stage that touched code, you MUST run:
   ```
   cd ~/git/litehive && uv run pytest tests/test_runner_workflow.py \
       tests/test_engine_variants_and_timeline.py \
       tests/test_heru_cli.py tests/test_codex_quota.py -q
   ```
   If any fail, your change broke the contract. Either fix heru to
   preserve the contract, or explicitly call out the breakage in your
   stage report with a proposed litehive-side migration.

3. **Stage reports are a litehive concept, not heru's.** `StageReport`,
   `StageResultSubmission`, `StageResultTests`, and `TaskUpdateSubmission`
   currently live in `heru/types.py` as a temporary compromise — they
   are slated to move to litehive. Do not add new stage-report logic
   or fields inside heru. If your task requires you to edit stage
   report semantics, flag it back: it is misfiled and belongs in
   litehive.

4. **Tests must be standalone.** No test under `tests/` may import
   from `litehive`. Every heru test must run in a fresh venv with
   only `heru + pydantic + pytest` installed. For JSONL fixtures,
   hand-craft strings or files under `tests/fixtures/` — do NOT
   shell out to real engine CLIs during tests.

5. **Respect the contract tests** (once `tests/contract/` exists per
   T-0007). Changing an assertion in `tests/contract/` is by
   definition a breaking change and requires the full semver
   checklist.

6. **Every new adapter needs both a public class AND a `_impl` helper
   module.** Shape: `adapters/<engine>.py` for the public class,
   `adapters/_<engine>_impl.py` for parsing/quota internals. Keep the
   symmetry — the base class expects it.

## Before you write code — ask yourself

- **Is this a heru concern or a litehive concern?** If you need task
  queues, retries, worktrees, commit pipelines, sandbox profiles, or
  the `STAGE_RESULT:` agent protocol, this is probably litehive.
  Stop and surface the concern in grooming.
- **Does this change the public API?** If yes, note the intended
  semver bump in your report and explicitly list what litehive needs
  to update.
- **Can I write this as a fixture-driven unit test?** If not, your
  code is probably too coupled to the real CLI subprocess — refactor
  to take parsed inputs.
- **Have I run the litehive contract tests?** If not, the task is not
  done, no matter what your implementation report says.

## Relationship to litehive

heru is maintained **alongside** litehive at `~/git/litehive`. They
share a developer (you) and live on the same laptop. litehive depends
on heru via `uv add --editable ~/git/heru`, so every heru save is
immediately visible to litehive without any reinstall.

**If a heru task requires changes in litehive to stay consistent**
(e.g. adding a new adapter method that litehive needs to call), open
a companion task in the litehive workspace referencing this task,
and land the heru side FIRST. Litehive can then safely bump its own
expectations.

## Process overlay
- Source of truth: tasks and implementation state live under `.litehive/`.
- Task source of truth: issues or task records define scope; prompts and transcripts are supporting evidence.
- Orchestrator model: the local runner is the manager and owns stage routing.
- Routing model: routing stays deterministic and local; subagents execute assigned stages but do not self-route.
- Shared stages: grooming -> implementing -> testing -> accepting -> commit_to_git.
- Role model: `planner` frames the task, `reviewer` performs final PM-style acceptance, `swe` edits code, and `qa` runs focused verification.
- TDD expectations: add or update focused tests near the changed Python module before broad suites.
- Verification discipline: prefer targeted `pytest` evidence close to the changed module before broader smoke coverage.
- Acceptance flow: verify behavior with targeted `pytest` coverage and note any residual risk.
- Commit and recovery: keep checkpoint commits deterministic and easy to recover.

## Project overlay
- Python package or application workflow with pytest-oriented verification.
- Favor incremental, reviewable changes over broad refactors.
- Keep implementation, verification, and acceptance evidence explicit.
- Prefer focused `pytest` coverage for the changed modules.
- Keep dependency and packaging changes explicit and minimal.

## Init scaffold
- Scaffold `.litehive/context.md` from the generic base process template.
- Layer the project profile summary, workspace overlay, and stage overlay onto that base.
- Treat process profiles as overlays on the shared contract rather than separate workflows.
- Keep the task/issue source of truth, verification commands, and recovery policy visible in the scaffold.
- Seed Python workspaces with package layout, test entrypoints, and `uv` or virtualenv expectations.

## Prompt scaffold
- Start from the shared process contract, then add repository context and task data.
- Combine the generic base prompt with the selected project overlay instead of replacing the base.
- Apply stage defaults first, then append any project-specific stage overlay for that step.
- Keep stage prompts explicit about role, verification expectations, and final report format.

## Stage prompt scaffolding

### grooming
Act as the planner: clarify the user problem, inspect the repo if needed, and produce a concrete execution plan.
Focus on scope clarification, acceptance criteria quality, decomposition, follow-up tasks, and PM sizing.
Do not make code changes in this stage.

### implementing
Implement the task in this repository.
Keep changes tightly scoped and complete the work needed for the acceptance criteria.
Write tests so each assertion would fail if the feature is broken.
Do not spend test coverage on framework behavior or library guarantees.
Do not add tests that only restate defaults, constants, or static data.
Keep each test focused on one behavior.
Avoid duplicate coverage; extend an existing test only when it is the same behavior.
- Write or update focused tests alongside the code change when feasible.
- Use `pytest` for automated verification.
- Use `tmp_path` or pytest fixtures instead of manual tempfiles in repo code or `/tmp` setup.
- Mock external calls and integration edges, not the internal logic under test.
- Do not use `time.sleep` in tests; use deterministic synchronization or time control.

### testing
Validate the implementation.
Run focused checks or tests where possible and report failures precisely.
Only make minimal fixes if absolutely necessary.
Reject tests whose assertions would still pass if the feature were broken.
Reject tests that duplicate existing coverage instead of covering a new behavior.
Reject tests longer than 50 lines unless a shorter structure is genuinely impossible.
Reject monolithic tests that exercise 5 or more behaviors in one flow.
- Prefer targeted `pytest` invocations before broader test commands.
- Verify new or updated tests use `pytest` idioms and fixtures.
- Reject tests that use manual tempfiles where `tmp_path` would make isolation explicit.
- Reject tests that mock the unit's internal logic instead of external boundaries.
- Reject tests that rely on `time.sleep` instead of deterministic control.

### accepting
Act as the reviewer: validate the end-user outcome against the acceptance criteria and decide whether it should be accepted or sent back.
Be strict about regression detection, evidence quality, and final done versus not-done judgment.

## Python specifics
- Prefer `pytest` for automated verification.
- Keep module boundaries and import hygiene clear.
- Record virtualenv, `uv`, or toolchain expectations when they matter.

## Development rules
- Keep changes scoped to the current task.
- Prefer targeted tests over broad test suites.
- Record assumptions clearly in the final report.

## Tool usage
- Use `uv run pytest -q` for the current smoke test suite.
- Update litehive task artifacts instead of inventing external state stores.
- If you add a new command or workflow, document it here for future runs.
