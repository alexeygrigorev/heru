import pytest

from heru import extract_engine_timeline


@pytest.mark.parametrize("stdout", ["", "   \n  \n  ", "not jsonl at all\njust plain text"])
def test_extract_engine_timeline_returns_none_without_events(stdout: str) -> None:
    assert extract_engine_timeline("opencode", stdout) is None


def test_extract_engine_timeline_assigns_task_and_subagent_ids() -> None:
    stdout = '{"type":"text","part":{"text":"VERDICT: PASS\\nSUMMARY: did the thing"}}\n'

    timeline = extract_engine_timeline(
        "opencode",
        stdout,
        task_id="T-0001",
        subagent_id="SA-0001",
    )

    assert timeline is not None
    assert timeline.engine == "opencode"
    assert timeline.task_id == "T-0001"
    assert timeline.subagent_id == "SA-0001"
    assert len(timeline.events) == 1
    assert timeline.events[0].kind == "message"
    assert timeline.events[0].role == "assistant"
    assert "VERDICT: PASS" in timeline.events[0].content
    assert timeline.event_counts == {"message": 1}


def test_extract_engine_timeline_records_mixed_message_and_usage_events() -> None:
    stdout = (
        '{"type":"assistant.message_delta","delta":"Thinking..."}\n'
        '{"type":"usage","usage":{"input_tokens":75,"output_tokens":25,"total_tokens":100},"cost":{"total_usd":0.0015}}\n'
    )

    timeline = extract_engine_timeline(
        "goz",
        stdout,
        task_id="T-0010",
        subagent_id="SA-0003",
    )

    assert timeline is not None
    assert timeline.engine == "goz"
    assert timeline.task_id == "T-0010"
    assert timeline.subagent_id == "SA-0003"
    assert len(timeline.events) == 2
    assert timeline.events[0].kind == "message"
    assert timeline.events[0].content == "Thinking..."
    assert timeline.events[1].kind == "usage"
    assert timeline.events[1].metadata["total_tokens"] == 100
    assert timeline.events[1].metadata["cost"] == "0.001500"
    assert timeline.event_counts == {"message": 1, "usage": 1}
