import pytest
from pydantic import ValidationError

from heru.types import (
    EngineUsageObservation,
    EngineUsageWindow,
    LiveEvent,
    LiveTimeline,
    ResourceLimitEvent,
    RuntimeEngineContinuation,
    StageReport,
    StageResultSubmission,
    StageResultTests,
    SubagentRef,
    TaskUpdateSubmission,
    UnifiedEvent,
)


def test_engine_usage_window_preserves_constructor_fields() -> None:
    usage = EngineUsageWindow(used=4, limit=10, remaining=6, unit="tokens", reset_at="2026-04-11T00:00:00Z")

    assert usage.used == 4
    assert usage.limit == 10
    assert usage.remaining == 6
    assert usage.unit == "tokens"
    assert usage.reset_at == "2026-04-11T00:00:00Z"


def test_engine_usage_observation_defaults_metadata_and_timestamp() -> None:
    observation = EngineUsageObservation(provider="openai")

    assert observation.source == "local"
    assert observation.provider == "openai"
    assert observation.invocation_count == 1
    assert observation.metadata == {}
    assert observation.observed_at.endswith("+00:00")


def test_unified_event_preserves_public_schema_fields() -> None:
    event = UnifiedEvent(kind="message", engine="codex", role="assistant", content="done", continuation_id="sess-1")

    assert event.kind == "message"
    assert event.engine == "codex"
    assert event.role == "assistant"
    assert event.content == "done"
    assert event.continuation_id == "sess-1"


def test_live_event_is_a_unified_event_shape() -> None:
    event = LiveEvent(kind="usage", engine="claude", metadata={"input_tokens": 1})

    assert event.kind == "usage"
    assert event.metadata == {"input_tokens": 1}


def test_live_timeline_recompute_counts_summarizes_by_kind() -> None:
    timeline = LiveTimeline(
        events=[
            LiveEvent(kind="message", engine="codex"),
            LiveEvent(kind="message", engine="codex"),
            LiveEvent(kind="usage", engine="codex"),
        ],
        engine="codex",
    )

    timeline.recompute_counts()

    assert timeline.event_counts == {"message": 2, "usage": 1}


def test_runtime_engine_continuation_prefers_session_id_for_resume_id() -> None:
    continuation = RuntimeEngineContinuation(session_id="sess-1", thread_id="thread-1")

    assert continuation.resume_id == "sess-1"


def test_runtime_engine_continuation_falls_back_to_thread_id_for_resume_id() -> None:
    continuation = RuntimeEngineContinuation(thread_id="thread-1")

    assert continuation.resume_id == "thread-1"


def test_resource_limit_event_preserves_optional_measurements() -> None:
    event = ResourceLimitEvent(reason="memory exceeded", memory_mb=512, exit_code=137)

    assert event.resource == "resource"
    assert event.reason == "memory exceeded"
    assert event.memory_mb == 512
    assert event.exit_code == 137


def test_subagent_ref_defaults_public_status_and_sandbox_fields() -> None:
    ref = SubagentRef(id="sub-1", role="qa", engine="codex", path="/tmp/sub")

    assert ref.status == "created"
    assert ref.sandboxed is False
    assert ref.sandbox_summary == ""


def test_stage_result_tests_defaults_to_zero_counts() -> None:
    counts = StageResultTests()

    assert counts.added == 0
    assert counts.passing == 0


def test_task_update_submission_accepts_public_planning_fields() -> None:
    update = TaskUpdateSubmission(
        title="Add contract tests",
        acceptance_criteria=["criterion 1"],
        plan=["step 1"],
        pm_complexity="moderate",
        planned_effort="m",
        mode="implementation",
    )

    assert update.title == "Add contract tests"
    assert update.acceptance_criteria == ["criterion 1"]
    assert update.plan == ["step 1"]
    assert update.pm_complexity == "moderate"
    assert update.planned_effort == "m"
    assert update.mode == "implementation"


def test_stage_result_submission_normalizes_accept_to_pass() -> None:
    submission = StageResultSubmission(verdict="accept", summary="done")

    assert submission.verdict == "pass"
    assert submission.tests == StageResultTests()


def test_stage_result_submission_normalizes_fail_to_reject() -> None:
    submission = StageResultSubmission(verdict="fail", summary="broken")

    assert submission.verdict == "reject"


def test_stage_result_submission_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        StageResultSubmission(verdict="pass", summary="done", unexpected=True)


def test_stage_report_preserves_public_defaults() -> None:
    report = StageReport(task_id="T-1", step="implementing", verdict="pass", summary="done")

    assert report.source == "agent"
    assert report.tests == {"added": 0, "passing": 0}
    assert report.retry_source == "global"
    assert report.created_at.endswith("+00:00")
