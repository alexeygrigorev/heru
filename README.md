# heru

**Unified headless CLI for coding agents.** One interface, one JSONL output
format, one resume mechanism — regardless of which underlying agent you use:

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
```

All output is streamed as a unified JSONL format — one event shape
regardless of the underlying engine. The underlying engine's native
format is preserved in the raw payload for cases where you need the
detail.

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

- [ ] Unified JSONL output format — currently each adapter streams the
      engine's native events; normalizing to a single envelope is next.
- [ ] Unified `--resume` across all engines — adapters all accept a
      `resume_session_id` parameter, but the CLI layer hasn't been
      unified to match.
- [ ] Positional engine argument (`heru codex <prompt>`) — current CLI
      uses `--engine codex`, will switch to positional.
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
