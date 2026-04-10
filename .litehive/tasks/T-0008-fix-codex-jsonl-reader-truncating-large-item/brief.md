# T-0008 Fix codex JSONL reader truncating large item.completed events

- Mode: tasks
- Task type: bugfix
- PM complexity: moderate
- Planned effort: m

## Goal
heru's codex adapter reader truncates JSONL lines containing large aggregated_output fields, producing 'Unterminated string' parse errors and silently dropping item.completed events. Find the line-length / buffer cap in the codex stream reader and raise or remove it so full events make it to downstream consumers. Also dedupe the skip-logging: each truncated line is currently logged 6-10 times by overlapping layers (codex:, iter_jsonl_payloads:).

## Acceptance Criteria
- Codex events with aggregated_output > 8KB parse successfully end-to-end
- No duplicate skip-log messages for a single malformed/truncated line
- Regression test with a fixture containing a large aggregated_output line
- litehive contract tests still pass

## Constraints
- Prefer the smallest change that removes the failure mode.
- Call out any remaining edge cases or follow-up risk explicitly.

## Plan
- Reproduce or localize the failing behavior.
- Implement the minimal targeted fix.
- Run focused regression coverage for the affected behavior.

## PM Sizing
- Complexity: moderate
- Planned effort: m

## Template Guidance
- Describe the broken behavior, trigger, and expected correct behavior before changing code.
- Aim at root cause, not just the visible symptom.
- Include regression coverage or equivalent focused proof that the failure is gone.

## Intake Notes

### Bug and Reproduction
- Describe the failing behavior, trigger, and expected result.

_TBD_

### Root Cause
- Note the suspected or confirmed cause in the affected path.

_TBD_

### Regression Coverage
- Record the exact test or check that prevents recurrence.

_TBD_
