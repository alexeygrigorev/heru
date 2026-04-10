# T-0010 Add tests_integration/ — real-engine CLI smoke tests for all heru adapters

- Mode: tasks
- Task type: adapter
- PM complexity: moderate
- Planned effort: m

## Goal
Create tests_integration/ at the repo root with one smoke-test file per engine adapter (codex, claude, copilot, gemini, opencode, goz). Each test spawns the REAL engine CLI as a subprocess via heru's own adapter (build_invocation + finalize_invocation + subprocess.run) and verifies heru's stream reader correctly parses the output transcript. Adapt the relevant patterns from ~/git/litehive/tests_integration/ — specifically helpers.py and the per-engine test files — but strip out all litehive-specific machinery: no 'from litehive' imports, no task/verdict/report/nudge flows, no LitehiveConfig, no ensure_workspace. Use HERU_INTEGRATION_ENGINES (not LITEHIVE_*) as the opt-in env var, default-skip when unset, skip per-engine when binary is not on PATH, skip on quota (use heru/quota/). Also include one resume/continuation smoke test per engine that supports it, to guard T-0003's unified --resume/--continue work. Add tests_integration/README.md explaining how to run the suite. Update CLAUDE.md to document the tests/ vs tests_integration/ split: tests/ is fixture-only and runs by default; tests_integration/ requires HERU_INTEGRATION_ENGINES and installed CLIs.

## Acceptance Criteria
- tests_integration/ exists at repo root with conftest.py, helpers.py, README.md, and test_<engine>.py for each of codex/claude/copilot/gemini/opencode/goz
- tests_integration/ contains zero 'from litehive' imports
- Each per-engine test skips cleanly when its binary is not on PATH or when HERU_INTEGRATION_ENGINES is unset
- Each per-engine file has a smoke test that actually spawns the engine CLI, pipes the JSONL through heru's stream reader, and asserts the expected reply text appears in the transcript
- Each engine that supports resume has an integration test exercising heru's unified --resume/--continue path
- HERU_INTEGRATION_ENGINES and HERU_INTEGRATION_TIMEOUT_SECONDS env vars are honored and documented in tests_integration/README.md
- CLAUDE.md documents the tests/ vs tests_integration/ split
- uv run pytest tests/ still passes standalone (no HERU_INTEGRATION_ENGINES set)
- HERU_INTEGRATION_ENGINES=codex uv run pytest tests_integration/test_codex.py passes on a machine with codex installed (document the expectation; do not require it to run in CI)
- litehive contract tests from ~/git/litehive still pass

## Constraints
- Keep provider-specific behavior isolated to the adapter boundary.
- Preserve deterministic workspace state and execution flow.

## Plan
- Inspect the existing adapter interface, config wiring, and invocation flow.
- Implement the adapter change close to the integration seam.
- Verify the adapter path with a focused test or representative run.

## PM Sizing
- Complexity: moderate
- Planned effort: m

## Template Guidance
- State the target adapter seam, external dependency, and expected contract up front.
- Call out config, invocation, and failure-path changes explicitly.
- Prefer verification that exercises the adapter boundary rather than unrelated paths.

## Intake Notes

### Adapter Surface
- Identify the entrypoint, inputs, outputs, and external system involved.

_TBD_

### Config and Execution Path
- Note which settings, command wiring, or failure handling must change.

_TBD_

### Verification Evidence
- Capture the focused run or test that proves the adapter path works.

_TBD_
