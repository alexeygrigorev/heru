# T-0011 Add 'heru quota' CLI subcommand: show quota for all or one engine

- Mode: tasks
- Task type: adapter
- PM complexity: simple
- Planned effort: s

## Goal
Add a new CLI subcommand to heru: 'heru quota' prints quota status for every registered provider (codex, claude, copilot, zai which covers opencode+goz), and 'heru quota <name>' prints quota for one. Build on the existing heru/quota/ Python API (check_codex_quota, check_claude_quota, check_copilot_quota, check_zai_quota, and their *_block_reason helpers). Output should be human-readable by default — one line per provider showing used/limit/remaining/unit, reset window, and a clear indicator when a block_reason is active. Add a --json flag for machine-readable output. Handle providers with no quota support (gemini) by printing 'unsupported' rather than erroring. Handle auth failures (missing token) by printing the provider-specific reason rather than crashing. Add fixture-driven tests under tests/ that mock each provider's check_* function; do not hit any real network. Update README to document the new subcommand.

## Acceptance Criteria
- 'heru quota' (no args) prints one line per supported provider: codex, claude, copilot, zai
- 'heru quota codex' / 'heru quota claude' / 'heru quota copilot' / 'heru quota zai' each prints quota for that single provider
- 'heru quota gemini' prints an 'unsupported' notice rather than crashing
- 'heru quota <unknown>' prints a helpful error listing valid provider names and exits non-zero
- Output includes used, limit, remaining, unit, reset window, and active block_reason if any
- --json flag emits machine-readable output (one JSON object per provider, or a single object for the single-provider form)
- Missing auth / missing credential file is reported per-provider, not as a crash
- Fixture-driven tests under tests/ cover success, unsupported, unknown-name, missing-auth, and --json paths — zero real network calls
- README documents 'heru quota' and 'heru quota <name>'
- uv run pytest tests/ passes
- litehive contract tests from ~/git/litehive still pass

## Constraints
- Keep provider-specific behavior isolated to the adapter boundary.
- Preserve deterministic workspace state and execution flow.

## Plan
- Inspect the existing adapter interface, config wiring, and invocation flow.
- Implement the adapter change close to the integration seam.
- Verify the adapter path with a focused test or representative run.

## PM Sizing
- Complexity: simple
- Planned effort: s

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
