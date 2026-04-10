# heru

Engine adapter layer for CLI-based coding agents. Wraps `codex`, `claude`,
`copilot`, `gemini`, `opencode`, and `goz` CLIs behind a uniform interface,
handling per-engine quota parsing, continuation extraction, and sandboxing
metadata.

Extracted from [litehive](https://github.com/alexeygrigorev/litehive).

## Status

**Not yet fully standalone.** `heru/types.py` currently imports 16 shared
types from `litehive.models` (`EngineUsageObservation`, `StageReport`,
`RuntimeEngineContinuation`, `SubagentRef`, etc.). Until those are moved
into heru, this package can only be used inside a litehive development
environment where `litehive.models` is importable on sys.path. Fixing this
is tracked as litehive task T-0316.

## Layout

```
heru/
  adapters/    per-engine CLI wrappers (codex, claude, copilot, gemini, opencode, goz)
  quota/       per-provider quota / rate-limit parsing
  base.py      ExternalCLIAdapter base class + CLIInvocation
  types.py     shared type re-exports (will become authoritative after T-0316)
```

## Install (dev)

Path-editable into an existing Python environment that also has `litehive`
importable:

```bash
uv add --editable /path/to/heru
```

Standalone install (`pip install heru`) will not work today until T-0316
lands and the upward import into `litehive.models` is removed.
