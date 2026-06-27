# Changelog

## 2.1.1 - 2026-06-27

- Added launch profiles with `heru <engine> --profile <name>`.
- Profiles can override the launch command, set environment variables, unset
  environment variables from files, and run preflight commands.
- Documented Z.AI-routed `zodex` and `zlaude` profile examples without adding
  them as first-class engines.
- Added CI publishing on `v*` tag pushes.

## 2.1.0 - 2026-05-24

- Removed the `heru usage` convenience command.
- Cross-provider quota reporting now belongs to `quse`; call `quse`
  directly for normalized usage windows.

## 2.0.0 - 2026-04-23

- Removed the legacy prompt-first `--engine` CLI form.
- Kept the positional contract as the only supported syntax:
  `heru <engine> <prompt>`.
- Added a migration note for Litehive and other callers in
  `docs/migrations/2.0.0-remove-legacy-engine-flag.md`.
