# T-0013 Normalize heru usage output to two unified windows: hours and weeks

- Mode: tasks
- Task type: refactor
- PM complexity: moderate
- Planned effort: m

## Goal
heru's quota/usage output is currently per-provider and inconsistent: codex exposes primary_window/secondary_window, claude exposes five_hour/seven_day, zai exposes api_calls/tokens with a window_hours field, copilot is flat with a monthly quota_reset_date. Unify this so every provider returns the same shape: two windows named 'hours' (roughly 5-hour) and 'weeks' (roughly 1-week). Each window reports used/remaining as a percentage and a reset timestamp normalized to ISO8601 UTC. Collapse the per-provider dataclasses (CodexQuotaStatus, CodexQuotaWindow, ClaudeQuotaStatus, ClaudeQuotaWindow, ZaiQuotaStatus, ZaiQuotaWindow, CopilotQuotaStatus and friends) into a single shared data model — no more one-off fields like premium_remaining, premium_entitlement, window_hours, primary_window, secondary_window, five_hour, seven_day, api_calls, tokens. Hardcoding rules the user has specified: codex reports hours as 100% remaining (treat as non-binding); zai reports weeks as 100% remaining (treat as non-binding). Copilot only has a monthly window upstream — decide a reasonable mapping into the (hours, weeks) shape without inventing a third window. 'heru usage' and 'heru usage <name>' CLI output follows the new shape, and the --json form emits the unified schema. This is a breaking change to heru's public quota API.

## Acceptance Criteria
- heru/quota exposes a single unified usage status dataclass with exactly two windows: hours and weeks
- Each window carries percent_remaining and reset_at (ISO8601 UTC string or None)
- No per-provider window or status dataclasses remain in heru/quota/
- codex's hours window is 100% remaining regardless of API response
- zai's weeks window is 100% remaining regardless of API response
- All reset timestamps are normalized to ISO8601 UTC across providers (None if unknown/unsupported)
- 'heru usage' and 'heru usage <name>' print the unified (hours, weeks) shape for every supported provider
- 'heru usage --json' emits the unified schema
- heru tests/ updated to cover the new shape and all providers; fixture-only, no network
- uv run pytest tests/ passes
- README's 'heru usage' section updated to document the unified shape
- litehive contract tests from ~/git/litehive still pass (heru must not break the contract; the litehive-side adoption of the new shape is tracked in a separate litehive task)

## Constraints
- Avoid broad opportunistic cleanup outside the chosen seam.
- Preserve existing behavior unless the task explicitly includes functional changes.

## Plan
- Identify the narrow seam to refactor and the behavior that must stay stable.
- Restructure the code in small, reviewable steps.
- Run focused verification to confirm behavior is preserved.

## PM Sizing
- Complexity: moderate
- Planned effort: m

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
