# CLAUDE.md

Agent working notes for the **heru** repository.

## What this project is

heru is a unified headless CLI for coding agents (codex, claude,
copilot, gemini, opencode, goz). It wraps each supported agent CLI
behind a uniform Python interface with one event schema and one
resume mechanism. Point it at any supported agent, get the same
shape out.

heru is the **engine-I/O layer**. It knows nothing about task
queues, stages, orchestration pipelines, sandboxing, or git commit
workflows — those concerns belong in [litehive](https://github.com/alexeygrigorev/litehive),
the main consumer of heru.

## Before you edit anything

Read `.litehive/context.md` in full. It has the complete public API
contract, hard rules, and pre-commit check procedure. This file
(`CLAUDE.md`) is the short version; `.litehive/context.md` is the
authoritative long version.

## Hard rules (short version)

1. **Zero imports from `litehive`**. heru is a leaf package with one
   runtime dep: `pydantic`.
2. **Do not break litehive**. Run litehive's contract tests before
   every commit:
   ```
   cd ~/git/litehive && uv run pytest tests/test_runner_workflow.py \
       tests/test_engine_variants_and_timeline.py \
       tests/test_heru_cli.py tests/test_codex_quota.py -q
   ```
3. **`StageReport` and friends are litehive concepts** — they live in
   `heru/types.py` temporarily and will move. Don't extend them here.
4. **Tests under `tests/` must be standalone** — no `from litehive`
   imports, no real subprocess calls to engine CLIs. Fixture-driven
   only.
5. **Anything not `_`-prefixed is public API** — changing it is a
   semver-major breaking change.
6. **Each adapter needs both a public class and a `_impl` module** —
   keep the symmetry.

## Quick commands

```bash
# Set up the heru venv
uv sync --extra dev

# Run heru's standalone tests
uv run pytest

# Invoke the CLI
uv run heru codex "hello"

# Contract check against litehive
cd ~/git/litehive && uv run pytest -q
```

## Layout

```
heru/
├── heru/                  # the Python package (public, unless _prefixed)
│   ├── __init__.py
│   ├── base.py            # ExternalCLIAdapter, CLIInvocation, run_live
│   ├── types.py           # shared pydantic types
│   ├── main.py            # `heru <engine> <prompt>` entry
│   ├── adapters/          # one module per engine (+ _impl helpers)
│   └── quota/             # per-provider quota checks
├── tests/                 # standalone pytest suite
├── pyproject.toml
└── README.md
```

## How tasks work here

This repo has its own `.litehive/` workspace. Tasks are created in
`.litehive/tasks/` and executed by the litehive daemon from within
the heru directory. The daemon runs each task through the normal
grooming → implementing → testing → accepting → commit_to_git
pipeline, with the heru repo as the working directory.

Tasks in the heru backlog focus exclusively on the engine-I/O layer:
adding adapters, unifying event schemas, expanding test coverage,
tightening the public API contract. Anything that mentions "tasks",
"stages", "retries", or "sandboxing" is misfiled and belongs in the
litehive workspace instead.
