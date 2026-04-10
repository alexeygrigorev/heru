"""Public CLI entrypoint for heru.

This module owns the stable ``heru <engine> <prompt>`` command shape and
the legacy ``--engine`` compatibility path documented in the README API
Contract section.
"""

from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path
from typing import Annotated

import click
import typer

from heru import ENGINE_CHOICES, get_engine
from heru.base import LATEST_CONTINUATION_SENTINEL

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)


def _run_engine(
    engine_name: str,
    prompt: str,
    cwd: Path,
    *,
    model: str | None = None,
    max_turns: int | None = None,
    resume: str | None = None,
    continue_latest: bool = False,
    raw: bool = False,
) -> int:
    engine = get_engine(engine_name)
    if resume is not None and continue_latest:
        raise click.ClickException("Cannot combine --resume with --continue.")
    if continue_latest:
        if not engine.supports_continue_latest():
            raise click.ClickException(
                f"{engine_name} does not support --continue; pass --resume <id> instead."
            )
        resume = LATEST_CONTINUATION_SENTINEL
    run_kwargs = {
        "model": model,
        "max_turns": max_turns,
        "resume_session_id": resume,
    }
    if "emit_unified" in inspect.signature(engine.run).parameters:
        run_kwargs["emit_unified"] = not raw
    execution = engine.run(prompt, cwd.resolve(), **run_kwargs)
    if execution.stdout:
        sys.stdout.write(execution.stdout)
    if execution.stderr:
        sys.stderr.write(execution.stderr)
    return execution.exit_code


PromptArgument = Annotated[str, typer.Argument(help="Prompt to send to the selected engine.")]
CwdOption = Annotated[Path, typer.Option(help="Working directory for the engine subprocess.")]
ModelOption = Annotated[str | None, typer.Option(help="Override the engine model name.")]
MaxTurnsOption = Annotated[int | None, typer.Option(help="Limit the number of turns for the run.")]
ResumeOption = Annotated[
    str | None,
    typer.Option(help="Resume a prior engine session by continuation or session ID."),
]
ContinueOption = Annotated[
    bool,
    typer.Option("--continue", help="Resume the most recent session for this engine."),
]
RawOption = Annotated[bool, typer.Option(help="Emit the engine's raw JSON/JSONL output.")]


def _engine_command_factory(engine_name: str):
    def command(
        prompt: PromptArgument,
        cwd: CwdOption = Path.cwd(),
        model: ModelOption = None,
        max_turns: MaxTurnsOption = None,
        resume: ResumeOption = None,
        continue_: ContinueOption = False,
        raw: RawOption = False,
    ) -> int:
        return _run_engine(
            engine_name,
            prompt,
            cwd,
            model=model,
            max_turns=max_turns,
            resume=resume,
            continue_latest=continue_,
            raw=raw,
        )

    command.__name__ = f"{engine_name}_command"
    command.__doc__ = f"Run a prompt with the {engine_name} adapter."
    return command


for _engine_name in ENGINE_CHOICES:
    app.command(_engine_name)(_engine_command_factory(_engine_name))


def build_legacy_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="heru", add_help=False)
    parser.add_argument("prompt")
    parser.add_argument("--engine", choices=ENGINE_CHOICES, required=True)
    parser.add_argument("--model")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--resume")
    parser.add_argument("--resume-session-id")
    parser.add_argument("--continue", dest="continue_", action="store_true")
    parser.add_argument("--raw", action="store_true")
    return parser


def _is_legacy_invocation(argv: list[str]) -> bool:
    return "--engine" in argv


def _run_legacy_cli(argv: list[str]) -> int:
    args = build_legacy_parser().parse_args(argv)
    resume = args.resume if args.resume is not None else args.resume_session_id
    print(
        "Deprecation warning: `heru <prompt> --engine <engine>` is deprecated; "
        "use `heru <engine> <prompt>` instead.",
        file=sys.stderr,
    )
    return _run_engine(
        args.engine,
        args.prompt,
        args.cwd,
        model=args.model,
        max_turns=args.max_turns,
        resume=resume,
        continue_latest=args.continue_,
        raw=args.raw,
    )


def main(argv: list[str] | None = None) -> int:
    """Public CLI entrypoint preserving heru's supported argv contract."""
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if _is_legacy_invocation(effective_argv):
            return _run_legacy_cli(effective_argv)
        result = app(
            args=effective_argv,
            prog_name="heru",
            standalone_mode=False,
        )
    except click.exceptions.Exit as exc:
        return exc.exit_code
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        return exc.exit_code
    return 0 if result is None else int(result)


if __name__ == "__main__":
    raise SystemExit(main())
