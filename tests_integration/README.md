# tests_integration

`tests_integration/` is the real-binary heru adapter suite. It is separate from `tests/` so the default pytest run stays fixture-only, deterministic, and standalone.

## What it covers

- One smoke test file per adapter: `codex`, `claude`, `copilot`, `gemini`, `opencode`, `goz`
- Real subprocess launches through heru's public adapter API: `build_invocation(...)`, `finalize_invocation(...)`, and `subprocess.run(...)`
- Transcript parsing through each adapter's `render_transcript(...)`
- Resume coverage for engines that support it:
  - `codex`, `claude`, `copilot`, `gemini`, `opencode`: unified latest-session continue
  - `goz`: explicit resume id via `--resume-session`

## Opt-in environment

These tests are skipped by default unless you opt in:

```bash
HERU_INTEGRATION_ENGINES=codex,claude,copilot,gemini,opencode,goz uv run pytest tests_integration/ -q
```

Run just one engine:

```bash
HERU_INTEGRATION_ENGINES=codex uv run pytest tests_integration/test_codex.py -q
```

You can also opt into all engines with:

```bash
HERU_INTEGRATION_ENGINES=all uv run pytest tests_integration/ -q
```

Timeouts default to 30 seconds and can be overridden:

```bash
HERU_INTEGRATION_TIMEOUT_SECONDS=60 HERU_INTEGRATION_ENGINES=codex uv run pytest tests_integration/test_codex.py -q
```

## Skip behavior

- If `HERU_INTEGRATION_ENGINES` is unset, the tests skip.
- If an engine is not named in `HERU_INTEGRATION_ENGINES`, that engine's tests skip.
- If the engine binary is not on `PATH`, that engine's tests skip.
- If a supported quota helper reports a block condition, that engine's tests skip.

## Expectations

- `tests/` remains the default suite and must run with no real engine CLIs installed.
- `tests_integration/` is for local verification on machines that already have the target CLIs installed and authenticated.
- A focused proof point for this task is:

```bash
HERU_INTEGRATION_ENGINES=codex uv run pytest tests_integration/test_codex.py -q
```
