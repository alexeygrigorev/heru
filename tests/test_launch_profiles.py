from pathlib import Path

from heru.profiles import load_launch_profiles


def test_load_launch_profile_reads_env_unset_file(tmp_path: Path) -> None:
    unset_file = tmp_path / "unset.txt"
    unset_file.write_text("# comment\nOPENAI_API_KEY\nCODEX_HOME\n", encoding="utf-8")
    profiles_file = tmp_path / "profiles.toml"
    profiles_file.write_text(
        f"""
[profiles.zodex]
engine = "codex"
command = "codex"
unset_env_file = "{unset_file}"
preflight = [["/bin/true"]]

[profiles.zodex.env]
CODEX_HOME = "{tmp_path}/.zodex"
""",
        encoding="utf-8",
    )

    profiles = load_launch_profiles(profiles_file)

    profile = profiles["zodex"]
    assert profile.engine == "codex"
    assert profile.command == ("codex",)
    assert profile.env == {"CODEX_HOME": f"{tmp_path}/.zodex"}
    assert profile.unset_env == ("OPENAI_API_KEY", "CODEX_HOME")
    assert profile.preflight == (("/bin/true",),)


def test_default_profiles_file_can_be_overridden_with_env(monkeypatch, tmp_path: Path) -> None:
    profiles_file = tmp_path / "profiles.toml"
    profiles_file.write_text('[profiles.fast]\nengine = "claude"\n', encoding="utf-8")
    monkeypatch.setenv("HERU_PROFILES_FILE", str(profiles_file))

    profiles = load_launch_profiles()

    assert profiles["fast"].engine == "claude"
