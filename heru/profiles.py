"""Launch profile support for heru engine invocations.

Profiles are intentionally engine-adjacent rather than engine-specific: they
describe how to launch an existing adapter with a different command, env, or
preflight command while keeping the adapter's native parsing behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import tomllib
from typing import Any


DEFAULT_PROFILES_PATH = Path("~/.config/heru/profiles.toml")
PROFILES_FILE_ENV_VAR = "HERU_PROFILES_FILE"


class LaunchProfileError(ValueError):
    """Raised when a launch profile cannot be loaded or applied."""


@dataclass(frozen=True, slots=True)
class LaunchProfile:
    """Launch-time overlay for an existing engine adapter."""

    name: str
    engine: str
    command: tuple[str, ...] | None = None
    env: dict[str, str] | None = None
    unset_env: tuple[str, ...] = ()
    preflight: tuple[tuple[str, ...], ...] = ()


def default_profiles_path() -> Path:
    configured = os.environ.get(PROFILES_FILE_ENV_VAR)
    return _expand_path(configured) if configured else _expand_path(str(DEFAULT_PROFILES_PATH))


def load_launch_profiles(path: Path | None = None) -> dict[str, LaunchProfile]:
    config_path = path or default_profiles_path()
    if not config_path.exists():
        return {}
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise LaunchProfileError(f"Could not parse launch profiles at {config_path}: {exc}") from exc

    profile_tables = raw.get("profiles", {})
    if not isinstance(profile_tables, dict):
        raise LaunchProfileError(f"Launch profiles file {config_path} must contain a [profiles] table.")

    profiles: dict[str, LaunchProfile] = {}
    for name, table in profile_tables.items():
        if not isinstance(name, str) or not isinstance(table, dict):
            continue
        profiles[name] = _parse_profile(name, table, config_path=config_path)
    return profiles


def resolve_launch_profile(
    name: str,
    *,
    engine_name: str,
    path: Path | None = None,
) -> LaunchProfile:
    profiles = load_launch_profiles(path)
    try:
        profile = profiles[name]
    except KeyError as exc:
        config_path = path or default_profiles_path()
        raise LaunchProfileError(f"Unknown launch profile '{name}' in {config_path}.") from exc
    if profile.engine != engine_name:
        raise LaunchProfileError(
            f"Launch profile '{name}' is for engine '{profile.engine}', not '{engine_name}'."
        )
    return profile


def _parse_profile(name: str, table: dict[str, Any], *, config_path: Path) -> LaunchProfile:
    engine = table.get("engine")
    if not isinstance(engine, str) or not engine:
        raise LaunchProfileError(f"Launch profile '{name}' in {config_path} must define engine = \"...\".")

    env = _parse_env(table.get("env"), profile_name=name, config_path=config_path)
    unset_env = list(_parse_unset_env(table.get("unset_env"), profile_name=name, config_path=config_path))
    unset_env_files = _string_values(table.get("unset_env_file"), field="unset_env_file", profile_name=name)
    for unset_env_file in unset_env_files:
        unset_env.extend(_read_env_unset_file(_expand_path(unset_env_file), profile_name=name))

    command = table.get("command")
    return LaunchProfile(
        name=name,
        engine=engine,
        command=_parse_command(command, field="command", profile_name=name) if command is not None else None,
        env=env,
        unset_env=tuple(dict.fromkeys(unset_env)),
        preflight=_parse_preflight(table.get("preflight"), profile_name=name),
    )


def _parse_env(raw: object, *, profile_name: str, config_path: Path) -> dict[str, str] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise LaunchProfileError(
            f"Launch profile '{profile_name}' in {config_path} has invalid env; expected a table."
        )
    return {str(key): _expand_env_value(str(value)) for key, value in raw.items()}


def _parse_unset_env(raw: object, *, profile_name: str, config_path: Path) -> tuple[str, ...]:
    if raw is None:
        return ()
    values = _string_values(raw, field="unset_env", profile_name=profile_name)
    if any(not value for value in values):
        raise LaunchProfileError(
            f"Launch profile '{profile_name}' in {config_path} has an empty unset_env entry."
        )
    return tuple(values)


def _parse_command(raw: object, *, field: str, profile_name: str) -> tuple[str, ...]:
    if isinstance(raw, str):
        command = shlex.split(_expand_env_value(raw))
    elif isinstance(raw, list) and all(isinstance(item, str) for item in raw):
        command = [_expand_env_value(item) for item in raw]
    else:
        raise LaunchProfileError(
            f"Launch profile '{profile_name}' has invalid {field}; expected a string or list of strings."
        )
    if not command:
        raise LaunchProfileError(f"Launch profile '{profile_name}' has an empty {field}.")
    return tuple(command)


def _parse_preflight(raw: object, *, profile_name: str) -> tuple[tuple[str, ...], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise LaunchProfileError(
            f"Launch profile '{profile_name}' has invalid preflight; expected a list."
        )
    commands: list[tuple[str, ...]] = []
    for item in raw:
        commands.append(_parse_command(item, field="preflight", profile_name=profile_name))
    return tuple(commands)


def _string_values(raw: object, *, field: str, profile_name: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
        return tuple(raw)
    raise LaunchProfileError(
        f"Launch profile '{profile_name}' has invalid {field}; expected a string or list of strings."
    )


def _read_env_unset_file(path: Path, *, profile_name: str) -> tuple[str, ...]:
    if not path.exists():
        raise LaunchProfileError(
            f"Launch profile '{profile_name}' references missing unset_env_file {path}."
        )
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        names.append(value)
    return tuple(names)


def _expand_path(value: str) -> Path:
    return Path(_expand_env_value(value)).expanduser()


def _expand_env_value(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))
