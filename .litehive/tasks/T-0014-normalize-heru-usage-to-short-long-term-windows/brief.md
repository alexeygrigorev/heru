# T-0014 Normalize heru usage to short/long-term windows and migrate litehive consumers atomically

- Mode: tasks
- Task type: refactor
- PM complexity: complex
- Planned effort: l

## Goal
heru's quota/usage output is per-provider and inconsistent, and the duration-based labels (5h, 7d, monthly) are meaningless to consumers — what matters is whether a limit is short-term (imminent, session-scoped) or long-term (the one used for blocking decisions at high utilization). Reshape heru's quota API so every provider returns the same unified shape: exactly two windows distinguishing short-term from long-term utilization. Each window reports percent remaining and a reset timestamp normalized to ISO8601 UTC. Collapse all per-provider dataclasses (CodexQuotaStatus, CodexQuotaWindow, ClaudeQuotaStatus, ClaudeQuotaWindow, CopilotQuotaStatus, ZaiQuotaStatus, ZaiQuotaWindow and friends) into one shared data model — no more one-off fields like primary_window, secondary_window, five_hour, seven_day, api_calls, tokens, window_hours, premium_remaining, premium_entitlement, quota_reset_date, max_used_percent.

Per-provider mapping constraints:
- codex: short-term window is hardcoded to 100% remaining (treated as non-binding). Long-term window reads from the codex API's weekly signal.
- claude: short-term window maps to the 5-hour signal; long-term window maps to the 7-day signal.
- copilot: upstream only exposes a single monthly window. Map that monthly signal into the long-term window (long-term is the broader 'longest usage-bearing window we know about'). Short-term is hardcoded to 100% remaining.
- zai: short-term maps to the tokens signal only — drop the api_calls / TIME_LIMIT window entirely, it is not useful to consumers. Long-term is hardcoded to 100% remaining.
- gemini: no usage endpoint exists; 'heru usage gemini' continues to report 'unsupported'.

'heru usage' and 'heru usage <name>' CLI output follows the new shape, including the --json form.

This is a breaking change to heru's public quota API, and litehive is the main consumer. To keep the two repos in sync, this task must also update litehive's call sites atomically: delete references to the removed per-provider fields, migrate every consumer (engine monitoring, health, dashboard, dry-run, web snapshot, pool control, pipeline models, tests) to the new unified (short-term, long-term) shape, and bump the heru dependency pin in litehive's pyproject.toml. litehive's blocking logic at high utilization should read from the long-term window. Run heru's tests/ suite, heru's tests_integration/ suite across every supported engine, litehive's full tests/ suite, litehive's tests_integration/ suite across every supported engine, and litehive's contract test suite run from ~/git/litehive before finishing. Both repos should land in a coordinated way so litehive is never broken against heru.

## Acceptance Criteria
- heru exposes a single unified usage status dataclass with exactly two windows distinguishing short-term and long-term utilization
- Each window carries percent remaining and reset_at (ISO8601 UTC string or None)
- All per-provider quota/window dataclasses are removed from heru/quota/
- codex short-term window is 100% remaining regardless of API response
- zai long-term window is 100% remaining regardless of API response
- zai exposes only the tokens signal; the api_calls / TIME_LIMIT window is gone
- copilot's monthly upstream signal maps into the long-term window; short-term is 100% remaining
- claude maps 5-hour → short-term and 7-day → long-term
- gemini continues to report 'unsupported' in 'heru usage'
- All reset timestamps across providers are ISO8601 UTC (or None when unknown/unsupported)
- 'heru usage' and 'heru usage <name>' print the unified shape; --json emits the unified schema
- heru tests/ updated and passing, fixture-only, no network
- heru tests_integration/ passes for every supported engine (codex, claude, copilot, gemini, opencode, goz) when the engine is available
- heru README documents the unified usage shape
- litehive has zero references to primary_window, secondary_window, five_hour, seven_day, api_calls, tokens, window_hours, premium_remaining, premium_entitlement, quota_reset_date, or max_used_percent
- litehive's blocking logic at high utilization reads from the long-term window
- heru dependency pin in litehive's pyproject.toml bumped to include the unified shape
- litehive tests/ passes end-to-end
- litehive tests_integration/ passes for every supported engine (codex, claude, copilot, gemini, opencode, goz) when the engine is available
- litehive's contract test suite run from ~/git/litehive still passes

## Constraints
- Avoid broad opportunistic cleanup outside the chosen seam.
- Preserve existing behavior unless the task explicitly includes functional changes.

## Plan
- Identify the narrow seam to refactor and the behavior that must stay stable.
- Restructure the code in small, reviewable steps.
- Run focused verification to confirm behavior is preserved.

## PM Sizing
- Complexity: complex
- Planned effort: l

## Template Guidance
- Name the seam being refactored and the behavior that must not change.
- Keep the scope structural unless the task explicitly includes functional change.
- Use focused verification to prove behavior stayed stable.

## Intake Notes

### Refactor Seam
- Identify the module, function, or flow being reshaped.

_TBD_

### Behavior to Preserve
- List the user-visible or contract-level behavior that must stay the same.

_TBD_

### Verification
- Capture the checks that confirm the refactor did not regress behavior.

_TBD_
