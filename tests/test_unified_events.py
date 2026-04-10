import json

from heru import get_engine


def test_codex_translates_agent_message_to_unified_event() -> None:
    payload = {
        "type": "item.completed",
        "item": {"id": "msg_1", "type": "agent_message", "text": "hello from codex"},
    }

    event = get_engine("codex").translate_native_event(payload)

    assert event is not None
    assert event.kind == "message"
    assert event.engine == "codex"
    assert event.role == "assistant"
    assert event.content == "hello from codex"
    assert event.raw == payload


def test_claude_translates_tool_call_to_unified_event() -> None:
    payload = {
        "type": "content_block_start",
        "content_block": {"type": "tool_use", "name": "bash", "input": {"cmd": "pwd"}},
    }

    event = get_engine("claude").translate_native_event(payload)

    assert event is not None
    assert event.kind == "tool_call"
    assert event.engine == "claude"
    assert event.tool_name == "bash"
    assert json.loads(event.tool_input or "{}") == {"cmd": "pwd"}
    assert event.raw == payload


def test_copilot_translates_usage_to_unified_event() -> None:
    payload = {
        "type": "assistant.usage",
        "data": {"inputTokens": 10, "outputTokens": 4, "model": "gpt-5"},
    }

    event = get_engine("copilot").translate_native_event(payload)

    assert event is not None
    assert event.kind == "usage"
    assert event.engine == "copilot"
    assert event.usage_delta == {"inputTokens": 10, "outputTokens": 4, "model": "gpt-5"}
    assert event.raw == payload


def test_copilot_translates_continuation_to_unified_event() -> None:
    payload = {
        "type": "assistant.message",
        "data": {"content": "hello", "sessionId": "copilot-session"},
    }

    events = get_engine("copilot").translate_native_events(payload)

    assert [event.kind for event in events] == ["message", "continuation"]
    assert events[-1].continuation_id == "copilot-session"
    assert all(event.raw == payload for event in events)


def test_gemini_translates_init_to_continuation_event() -> None:
    payload = {"type": "init", "session_id": "gemini-session", "model": "gemini-2.5-pro"}

    event = get_engine("gemini").translate_native_event(payload)

    assert event is not None
    assert event.kind == "continuation"
    assert event.engine == "gemini"
    assert event.continuation_id == "gemini-session"
    assert event.raw == payload


def test_opencode_translates_step_finish_to_usage_and_continuation_events() -> None:
    payload = {
        "type": "step_finish",
        "sessionID": "opencode-session",
        "part": {
            "tokens": {"total": 17, "input": 10, "output": 7},
            "cost": 0.42,
        },
    }

    events = get_engine("opencode").translate_native_events(payload)

    assert [event.kind for event in events] == ["usage", "continuation"]
    assert events[0].usage_delta == {
        "total_tokens": 17,
        "input_tokens": 10,
        "output_tokens": 7,
        "cost": "0.420000",
    }
    assert events[1].continuation_id == "opencode-session"
    assert all(event.raw == payload for event in events)


def test_goz_translates_tool_result_to_unified_event() -> None:
    payload = {"type": "tool_result", "tool": "grep", "result": {"matches": 3}}

    event = get_engine("goz").translate_native_event(payload)

    assert event is not None
    assert event.kind == "tool_result"
    assert event.engine == "goz"
    assert event.tool_name == "grep"
    assert json.loads(event.tool_output or "{}") == {"matches": 3}
    assert event.raw == payload


def test_render_unified_output_serializes_jsonl_with_sequence_and_raw() -> None:
    stdout = (
        '{"type":"assistant.message","data":{"content":"first"}}\n'
        '{"type":"assistant.usage","data":{"inputTokens":3,"outputTokens":2}}\n'
    )

    rendered = get_engine("copilot").render_unified_output(stdout)
    lines = [json.loads(line) for line in rendered.splitlines()]

    assert [line["kind"] for line in lines] == ["message", "usage"]
    assert [line["sequence"] for line in lines] == [0, 1]
    assert lines[0]["raw"]["type"] == "assistant.message"
    assert lines[1]["usage_delta"] == {"inputTokens": 3, "outputTokens": 2}


def test_render_unified_output_appends_continuation_event_at_end() -> None:
    stdout = (
        '{"type":"init","session_id":"gemini-session","model":"gemini-2.5-pro"}\n'
        '{"type":"content","text":"hello again"}\n'
    )

    rendered = get_engine("gemini").render_unified_output(stdout)
    lines = [json.loads(line) for line in rendered.splitlines()]

    assert [line["kind"] for line in lines] == ["message", "continuation"]
    assert lines[-1]["continuation_id"] == "gemini-session"
    assert lines[-1]["sequence"] == 1
