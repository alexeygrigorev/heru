# T-0009 Move tests/contract/ to tests_integration/ and document the split

- Mode: tasks
- Task type: refactor
- PM complexity: simple
- Planned effort: s

## Goal
T-0007 shipped tests/contract/ under an earlier goal. heru's rule is that tests/ must be standalone (no 'from litehive' imports, no real engine subprocess calls), so contract-style tests belong in a separate top-level folder. Move tests/contract/ to tests_integration/ at the repo root. Update CLAUDE.md and .litehive/context.md to document the split: tests/ runs by default and in pre-commit; tests_integration/ is opt-in and may depend on a litehive checkout or real engine CLIs. Ensure 'uv run pytest tests/' and 'uv run pytest tests_integration/' both pass after the move.

## Acceptance Criteria
- tests_integration/ exists at repo root and contains the files previously under tests/contract/
- tests/contract/ no longer exists
- tests/ still contains zero 'from litehive' imports and zero real engine subprocess calls
- CLAUDE.md documents the tests/ vs tests_integration/ split and when each runs
- .litehive/context.md updated to reflect the new layout
- uv run pytest tests/ passes standalone
- uv run pytest tests_integration/ passes
- litehive contract tests from ~/git/litehive still pass

## Constraints
- Avoid broad opportunistic cleanup outside the chosen seam.
- Preserve existing behavior unless the task explicitly includes functional changes.

## Plan
- Identify the narrow seam to refactor and the behavior that must stay stable.
- Restructure the code in small, reviewable steps.
- Run focused verification to confirm behavior is preserved.

## PM Sizing
- Complexity: simple
- Planned effort: s

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
