import json
import logging

from heru.base import iter_jsonl_payloads


def test_iter_jsonl_payloads_warns_on_invalid_json(caplog) -> None:
    stdout = '{"type": "ok"}\nNOT_JSON_LINE\n{"type": "also_ok"}\n'

    with caplog.at_level(logging.WARNING, logger="litehive.agents.base"):
        payloads = iter_jsonl_payloads(stdout)

    assert len(payloads) == 2
    assert any("unparseable line 2" in rec.message for rec in caplog.records)


def test_iter_jsonl_payloads_warns_on_non_dict_json(caplog) -> None:
    stdout = '{"type": "ok"}\n[1, 2, 3]\n"just a string"\n42\n'

    with caplog.at_level(logging.WARNING, logger="litehive.agents.base"):
        payloads = iter_jsonl_payloads(stdout)

    assert len(payloads) == 1
    assert sum("non-object JSON" in rec.message for rec in caplog.records) == 3


def test_iter_jsonl_payloads_no_warning_on_blank_lines(caplog) -> None:
    stdout = '{"type": "ok"}\n\n  \n{"type": "also_ok"}\n'

    with caplog.at_level(logging.WARNING, logger="litehive.agents.base"):
        payloads = iter_jsonl_payloads(stdout)

    assert len(payloads) == 2
    assert not caplog.records


def test_claude_delta_fallback_warns_on_decode_failure(caplog) -> None:
    from heru.adapters.claude import _extract_claude_text_delta_fallback

    stdout = '{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"\\uZZZZ"}}\n'

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.claude"):
        result = _extract_claude_text_delta_fallback(stdout)

    assert result == []
    assert any("claude delta fallback" in rec.message and "line 1" in rec.message for rec in caplog.records)


def test_claude_delta_fallback_no_warning_on_valid_payload(caplog) -> None:
    from heru.adapters.claude import _extract_claude_text_delta_fallback

    stdout = '{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"hello"}}\n'

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.claude"):
        result = _extract_claude_text_delta_fallback(stdout)

    assert result == ["hello"]
    assert not caplog.records


def test_goz_extract_text_warns_on_unrecognized_dict(caplog) -> None:
    from heru.adapters.goz import _goz_extract_text

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.goz"):
        result = _goz_extract_text({"unknown_key": "some value", "another": 42})

    assert result is None
    assert any("_goz_extract_text could not extract text" in rec.message for rec in caplog.records)


def test_goz_extract_text_no_warning_on_known_keys(caplog) -> None:
    from heru.adapters.goz import _goz_extract_text

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.goz"):
        result = _goz_extract_text({"text": "hello"})

    assert result == "hello"
    assert not caplog.records


def test_goz_extract_text_no_warning_on_empty_dict(caplog) -> None:
    from heru.adapters.goz import _goz_extract_text

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.goz"):
        result = _goz_extract_text({})

    assert result is None
    assert not caplog.records


def test_codex_transcript_warns_on_non_dict_item(caplog) -> None:
    from heru.adapters.codex import _extract_codex_transcript

    stdout = json.dumps({"type": "item.completed", "item": "not_a_dict"}) + "\n"

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.codex"):
        result = _extract_codex_transcript(stdout)

    assert result == ""
    assert any("non-dict item" in rec.message for rec in caplog.records)


def test_codex_transcript_warns_on_missing_text(caplog) -> None:
    from heru.adapters.codex import _extract_codex_transcript

    stdout = json.dumps({"type": "item.completed", "item": {"type": "agent_message"}}) + "\n"

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.codex"):
        result = _extract_codex_transcript(stdout)

    assert result == ""
    assert any("no text field" in rec.message for rec in caplog.records)


def test_opencode_transcript_warns_on_non_dict_part(caplog) -> None:
    from heru.adapters.opencode import _extract_opencode_transcript

    stdout = json.dumps({"type": "text", "part": "not_a_dict"}) + "\n"

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.opencode"):
        result = _extract_opencode_transcript(stdout)

    assert result == ""
    assert any("non-dict part" in rec.message for rec in caplog.records)


def test_opencode_transcript_warns_on_missing_text(caplog) -> None:
    from heru.adapters.opencode import _extract_opencode_transcript

    stdout = json.dumps({"type": "text", "part": {"image": "data"}}) + "\n"

    with caplog.at_level(logging.WARNING, logger="litehive.agents.adapters.opencode"):
        result = _extract_opencode_transcript(stdout)

    assert result == ""
    assert any("no text field" in rec.message for rec in caplog.records)
