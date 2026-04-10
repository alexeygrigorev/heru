from pathlib import Path

import pytest

from heru import get_engine
from heru.base import LATEST_CONTINUATION_SENTINEL


@pytest.mark.parametrize(
    ("engine_name", "expected_argv"),
    [
        ("codex", ["codex", "exec", "resume", "--json", "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check", "continue please"]),
        ("claude", ["claude", "--resume", "-p", "continue please", "--output-format", "stream-json", "--include-partial-messages", "--verbose", "--dangerously-skip-permissions"]),
        ("copilot", ["copilot", "-p", "continue please", "--output-format", "json", "--allow-all-tools", "--autopilot", "--no-auto-update", "--add-dir", "/tmp/workspace", "--continue"]),
        ("gemini", ["gemini", "-p", "continue please", "--output-format", "stream-json", "--yolo", "--resume"]),
        ("opencode", ["opencode", "run", "--format", "json", "--dir", "/tmp/workspace", "--continue", "continue please"]),
    ],
)
def test_supported_engines_map_latest_resume_to_native_continue_flag(
    engine_name: str,
    expected_argv: list[str],
) -> None:
    invocation = get_engine(engine_name).build_invocation(
        "continue please",
        Path("/tmp/workspace"),
        resume_session_id=LATEST_CONTINUATION_SENTINEL,
    )

    assert list(invocation.argv) == expected_argv


def test_goz_requires_explicit_resume_id_for_latest_continue() -> None:
    with pytest.raises(ValueError, match="goz does not support resuming the latest session"):
        get_engine("goz").build_invocation(
            "continue please",
            Path("/tmp/workspace"),
            resume_session_id=LATEST_CONTINUATION_SENTINEL,
        )

