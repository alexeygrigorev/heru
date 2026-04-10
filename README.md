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
