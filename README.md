# heru

**Unified headless CLI for coding agents.** One interface, one JSONL event
envelope, one resume mechanism — regardless of which underlying agent you use:

- [codex](https://github.com/openai/codex) (OpenAI)
- [claude](https://github.com/anthropics/claude-code) (Anthropic)
- [copilot](https://github.com/github/copilot-cli) (GitHub)
- [gemini](https://github.com/google-gemini/gemini-cli) (Google)
- [opencode](https://github.com/sst/opencode) (any OpenAI-compatible)
- [goz](https://github.com/z-ai/goz) (Z.AI)

## Why

Every coding-agent CLI has its own flags, its own event format, its own
notion of "session", its own quota endpoint, and its own quirks. If you
want to drive them headlessly from a script or higher-level orchestrator,
you end up writing a separate wrapper for each — and when a new one ships
you start over.

heru is that wrapper, once. Point it at any supported CLI and get the
same shape out.

## Usage

```bash
# Fresh run
heru codex "summarize the diff between main and my branch"

# Resume a prior session
heru codex --resume <session-id> "now also run the tests"

# Different engine, same CLI shape
heru claude "find the bug in src/foo.py"

# Deprecated for one release
heru "find the bug in src/foo.py" --engine claude
```

All output is streamed as unified JSONL by default. Pass `--raw` to get
the engine's native JSON/JSONL stream back for debugging.

## Unified Event Schema

Each stdout line is a `UnifiedEvent` JSON object with these common fields:

- `kind`: `message`, `tool_call`, `tool_result`, `usage`, `error`, `status`, or `continuation`
- `engine`: the emitting engine name (`codex`, `claude`, `copilot`, `gemini`, `opencode`, `goz`)
- `sequence`: zero-based event order within the run
- `timestamp`: ISO-8601 timestamp for the emitted event
- `role`: optional role (`assistant`, `user`, `system`)
- `content`: assistant or status text when present
- `tool_name`: tool identifier for tool-related events
- `tool_input`: serialized tool input when present
- `tool_output`: serialized tool output when present
- `error`: error text when present
- `usage_delta`: per-event usage fields extracted from the provider payload
- `continuation_id`: session/thread identifier when the engine emits one
- `raw`: the original provider-native payload

Example:

```json
{"kind":"message","engine":"claude","sequence":0,"timestamp":"2026-04-10T19:00:00+00:00","role":"assistant","content":"Done.","raw":{"type":"assistant","message":{"content":"Done."}}}
```

## Install

```bash
pip install heru
# or
uv add heru
```

## Status

**v0.1.0 is a physical extraction from
[litehive](https://github.com/alexeygrigorev/litehive),** which uses
heru as its engine execution layer. Several things from the vision
above are still in flight:

- [x] Unified JSONL output format — `heru` now emits one documented
      event envelope across all supported engines by default.
- [x] Unified `--resume` across all engines.
- [x] Positional engine argument (`heru codex <prompt>`).
- [ ] Standalone sandboxing — heru currently executes agents directly;
      sandbox integration is a follow-up.

## Layout

```
heru/
  adapters/    per-engine CLI wrappers (codex, claude, copilot, gemini, opencode, goz)
  quota/       per-provider quota / rate-limit parsing
  base.py      ExternalCLIAdapter base class + CLIInvocation
  types.py     shared types (StageReport etc. are here temporarily — see below)
  main.py      entrypoint for `heru <engine> <prompt>`

tests/         unit tests for adapters, quota parsing, inactivity timeout
```

## API Contract

The names below are heru's stable public contract. Changes to their
signature, return shape, required fields, or documented behavior are
breaking changes and require a semver-major release.

### Public entrypoints

- `heru.get_engine(name)`: resolves a stable engine name such as `codex` or `claude` to the adapter instance heru will execute.
- `heru.ENGINE_CHOICES`: lists the stable engine names accepted by the CLI and `get_engine`.
- `heru.main.main(argv=None)`: provides the public `heru` CLI entrypoint and preserves the supported argument contract.

### Base adapter contract

- `heru.base.ExternalCLIAdapter`: base class callers may subclass against; heru preserves its constructor shape and override points as the adapter contract.
- `heru.base.CLIInvocation`: immutable invocation description containing argv, cwd, env, and optional stdin payload for a launch.
- `heru.base.CLIExecutionResult`: immutable execution record containing exit status, stdout/stderr, pid, and transcript accessors for a finished run.

### Engine adapters

- `heru.adapters.codex.CodexCLIAdapter`: stable adapter for Codex CLI command building, transcript rendering, usage extraction, and continuation discovery.
- `heru.adapters.claude.ClaudeCLIAdapter`: stable adapter for Claude Code invocation and unified stream parsing.
- `heru.adapters.copilot.CopilotCLIAdapter`: stable adapter for GitHub Copilot CLI invocation and stream parsing.
- `heru.adapters.gemini.GeminiCLIAdapter`: stable adapter for Gemini CLI invocation, usage extraction, and continuation parsing.
- `heru.adapters.opencode.OpenCodeAdapter`: stable adapter for OpenCode CLI invocation and stream parsing under the current exported class name.
- `heru.adapters.goz.GozCLIAdapter`: stable adapter for Goz CLI invocation, transcript extraction, and continuation parsing.

### `heru.types` models

- `EngineUsageWindow`: normalized usage-window counters and reset metadata extracted from provider output.
- `EngineUsageObservation`: normalized per-run usage or quota observation reported by adapters and quota helpers.
- `UnifiedEvent`: stable JSONL event schema emitted across engines.
- `LiveEvent`: a `UnifiedEvent` instance used inside live timelines.
- `LiveTimeline`: ordered live-event container with summary counts and task/subagent metadata.
- `ResourceLimitEvent`: normalized process-resource failure details attached to stage reports.
- `RuntimeEngineContinuation`: stable continuation/session handle for resume flows across engines.
- `SubagentRef`: stable reference to a spawned subagent as reported in pipeline payloads.
- `StageResultTests`: stable count payload for tests added and passing in a structured stage result.
- `TaskUpdateSubmission`: stable schema for structured task updates submitted during grooming.
- `StageResultSubmission`: stable schema for structured stage verdict payloads submitted by agents.
- `StageReport`: stable persisted stage-report record exchanged with litehive today.

### Internal modules

The modules below are internal implementation details and may change
without notice in any release:

- `heru._engine_detection`
- `heru._continuation`
- `heru.adapters._codex_impl`
- `heru.adapters._claude_impl`
- `heru.adapters._copilot_impl`
- `heru.adapters._gemini_impl`
- `heru.adapters._opencode_impl`
- `heru.adapters._goz_impl`

The same rule applies to private helpers and any `_`-prefixed name in a
public module unless this README explicitly lists it as part of the
stable contract.

### Stability Matrix

| heru version | Public API breakage |
| --- | --- |
| `v0.1.0` | Initial extracted public contract. No documented breaking public API changes yet. |

### Submitting A Breaking Change

If you need to break any public API listed above:

1. Bump heru's semver major version in `pyproject.toml`.
2. Add a CHANGELOG entry that names the broken public API and the replacement.
3. Add a migration note for litehive and any other known consumer that relies on the changed contract.

## Caveat — stage reports

`heru/types.py` currently defines `StageReport`, `StageResultSubmission`,
`StageResultTests`, and `TaskUpdateSubmission`. These are really a
litehive pipeline concept (the `STAGE_RESULT:` agent protocol, retry
bookkeeping, outcome classification) and will eventually move out of
heru into litehive. Tracking in the litehive task backlog.

## Tests

```bash
uv run pytest
```

## Development

Install the versioned git hook with:

```bash
./scripts/install-hooks.sh
```

The installer symlinks `scripts/pre-commit.sh` into your real git hook directory using `git rev-parse --git-path hooks/pre-commit`, so it works from normal checkouts and git worktrees.

When staged files touch `heru/` or `tests/`, the hook treats that commit as a potential change to heru's public contract with litehive and runs this focused smoke suite in the litehive repo:

```bash
cd ../litehive && uv run pytest -q \
  tests/test_runner_workflow.py \
  tests/test_engine_variants_and_timeline.py \
  tests/test_heru_cli.py \
  tests/test_codex_quota.py \
  tests/test_observability_and_status.py
```

The hook looks for litehive in a sibling checkout at `../litehive`, then falls back to `LITEHIVE_REPO`. If neither exists, it prints a warning and skips the smoke run so standalone heru users are not blocked.

The smoke suite is intended to protect the editable-install contract between heru and litehive: litehive imports heru directly from your local checkout, so breaking `heru` method names, CLI argv shape, event schema, or quota helpers can regress litehive immediately. If you need to bypass the hook intentionally, commit with `git commit --no-verify`, but that should be the exception rather than the default workflow.
