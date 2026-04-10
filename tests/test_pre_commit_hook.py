import json
import os
from pathlib import Path
import shutil
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=True)


def _init_git_repo(path: Path) -> None:
    _run(["git", "init"], cwd=path)
    _run(["git", "config", "user.name", "Test User"], cwd=path)
    _run(["git", "config", "user.email", "test@example.com"], cwd=path)


def _copy_script(relative_path: str, destination_root: Path) -> Path:
    source = REPO_ROOT / relative_path
    destination = destination_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    destination.chmod(0o755)
    return destination


def _seed_heru_repo(path: Path) -> None:
    _init_git_repo(path)
    (path / "heru").mkdir()
    (path / "tests").mkdir()
    (path / "heru" / "__init__.py").write_text("VALUE = 'base'\n", encoding="utf-8")
    (path / "tests" / "test_placeholder.py").write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")
    _copy_script("scripts/pre-commit.sh", path)
    _copy_script("scripts/install-hooks.sh", path)
    _run(["git", "add", "."], cwd=path)
    _run(["git", "commit", "-m", "init"], cwd=path)


def _create_litehive_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "tests").mkdir(exist_ok=True)
    for test_name in (
        "test_runner_workflow.py",
        "test_engine_variants_and_timeline.py",
        "test_heru_cli.py",
        "test_codex_quota.py",
        "test_observability_and_status.py",
    ):
        (path / "tests" / test_name).write_text("", encoding="utf-8")


def _write_fake_uv(path: Path, capture_path: Path, *, heru_repo: Path, exit_code: int = 0) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        f"capture = pathlib.Path({str(capture_path)!r})\n"
        f"heru_repo = pathlib.Path({str(heru_repo)!r})\n"
        "heru_init_path = heru_repo / 'heru' / '__init__.py'\n"
        "capture.write_text(json.dumps({\n"
        "    'argv': sys.argv[1:],\n"
        "    'cwd': os.getcwd(),\n"
        "    'heru_init_exists': heru_init_path.exists(),\n"
        "    'heru_init': heru_init_path.read_text(encoding='utf-8') if heru_init_path.exists() else None,\n"
        "}), encoding='utf-8')\n"
        "sys.stderr.write('fake uv stderr\\n')\n"
        f"raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_pre_commit_runs_litehive_smoke_tests_against_staged_state(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    heru_repo = workspace / "heru"
    litehive_repo = workspace / "litehive"
    capture = tmp_path / "uv-capture.json"

    heru_repo.mkdir(parents=True)
    _seed_heru_repo(heru_repo)
    _create_litehive_repo(litehive_repo)

    tracked_file = heru_repo / "heru" / "__init__.py"
    tracked_file.write_text("VALUE = 'staged'\n", encoding="utf-8")
    _run(["git", "add", "heru/__init__.py"], cwd=heru_repo)
    tracked_file.write_text("VALUE = 'unstaged'\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_uv(fake_bin / "uv", capture, heru_repo=heru_repo)
    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")

    result = subprocess.run(
        ["bash", str(heru_repo / "scripts" / "pre-commit.sh")],
        cwd=heru_repo,
        env=env,
        text=True,
        capture_output=True,
    )

    recorded = json.loads(capture.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert recorded["cwd"] == str(litehive_repo)
    assert recorded["argv"] == [
        "run",
        "pytest",
        "-q",
        "tests/test_runner_workflow.py",
        "tests/test_engine_variants_and_timeline.py",
        "tests/test_heru_cli.py",
        "tests/test_codex_quota.py",
        "tests/test_observability_and_status.py",
    ]
    assert recorded["heru_init"] == "VALUE = 'staged'\n"
    assert tracked_file.read_text(encoding="utf-8") == "VALUE = 'unstaged'\n"
    assert "litehive smoke tests passed" in result.stderr


def test_pre_commit_uses_litehive_repo_env_var_when_no_sibling_exists(tmp_path: Path) -> None:
    heru_repo = tmp_path / "heru"
    litehive_repo = tmp_path / "elsewhere" / "litehive"
    capture = tmp_path / "uv-capture.json"

    heru_repo.mkdir()
    _seed_heru_repo(heru_repo)
    _create_litehive_repo(litehive_repo)

    tracked_file = heru_repo / "tests" / "test_placeholder.py"
    tracked_file.write_text("def test_placeholder():\n    assert 1 == 1\n", encoding="utf-8")
    _run(["git", "add", "tests/test_placeholder.py"], cwd=heru_repo)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_uv(fake_bin / "uv", capture, heru_repo=heru_repo)
    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}", LITEHIVE_REPO=str(litehive_repo))

    result = subprocess.run(
        ["bash", str(heru_repo / "scripts" / "pre-commit.sh")],
        cwd=heru_repo,
        env=env,
        text=True,
        capture_output=True,
    )

    recorded = json.loads(capture.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert recorded["cwd"] == str(litehive_repo)


def test_pre_commit_warns_and_skips_when_litehive_repo_is_missing(tmp_path: Path) -> None:
    heru_repo = tmp_path / "heru"
    heru_repo.mkdir()
    _seed_heru_repo(heru_repo)

    tracked_file = heru_repo / "heru" / "__init__.py"
    tracked_file.write_text("VALUE = 'changed'\n", encoding="utf-8")
    _run(["git", "add", "heru/__init__.py"], cwd=heru_repo)

    result = subprocess.run(
        ["bash", str(heru_repo / "scripts" / "pre-commit.sh")],
        cwd=heru_repo,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "litehive was not found" in result.stderr
    assert "skipping litehive smoke tests" in result.stderr


def test_pre_commit_rejects_commit_when_litehive_smoke_tests_fail(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    heru_repo = workspace / "heru"
    litehive_repo = workspace / "litehive"
    capture = tmp_path / "uv-capture.json"

    heru_repo.mkdir(parents=True)
    _seed_heru_repo(heru_repo)
    _create_litehive_repo(litehive_repo)

    tracked_file = heru_repo / "heru" / "__init__.py"
    tracked_file.write_text("VALUE = 'broken'\n", encoding="utf-8")
    _run(["git", "add", "heru/__init__.py"], cwd=heru_repo)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_uv(fake_bin / "uv", capture, heru_repo=heru_repo, exit_code=1)
    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")

    result = subprocess.run(
        ["bash", str(heru_repo / "scripts" / "pre-commit.sh")],
        cwd=heru_repo,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "fake uv stderr" in result.stderr
    assert "litehive smoke tests failed" in result.stderr
    assert "commit rejected" in result.stderr


def test_pre_commit_runs_for_staged_deletions_under_heru(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    heru_repo = workspace / "heru"
    litehive_repo = workspace / "litehive"
    capture = tmp_path / "uv-capture.json"

    heru_repo.mkdir(parents=True)
    _seed_heru_repo(heru_repo)
    _create_litehive_repo(litehive_repo)

    _run(["git", "rm", "heru/__init__.py"], cwd=heru_repo)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_uv(fake_bin / "uv", capture, heru_repo=heru_repo)
    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")

    result = subprocess.run(
        ["bash", str(heru_repo / "scripts" / "pre-commit.sh")],
        cwd=heru_repo,
        env=env,
        text=True,
        capture_output=True,
    )

    recorded = json.loads(capture.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert recorded["cwd"] == str(litehive_repo)
    assert recorded["heru_init_exists"] is False
    assert "running litehive smoke tests" in result.stderr


def test_install_hooks_links_pre_commit_into_git_hook_path(tmp_path: Path) -> None:
    source_repo = tmp_path / "source"
    worktree = tmp_path / "worktree"

    source_repo.mkdir()
    _init_git_repo(source_repo)
    (source_repo / "README.md").write_text("base\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=source_repo)
    _run(["git", "commit", "-m", "init"], cwd=source_repo)
    _run(["git", "branch", "feature"], cwd=source_repo)
    _run(["git", "worktree", "add", str(worktree), "feature"], cwd=source_repo)

    _copy_script("scripts/pre-commit.sh", worktree)
    _copy_script("scripts/install-hooks.sh", worktree)

    result = subprocess.run(
        ["bash", str(worktree / "scripts" / "install-hooks.sh")],
        cwd=worktree,
        text=True,
        capture_output=True,
    )

    hook_path = source_repo / ".git" / "hooks" / "pre-commit"

    assert result.returncode == 0
    assert hook_path.is_symlink()
    assert hook_path.resolve() == (worktree / "scripts" / "pre-commit.sh").resolve()
