import pytest

from radar_intelligence.llm import LLMClient, extract_json, stage_enabled


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose_and_trailing_logs():
    text = 'Here is my analysis:\n{"candidate": true, "reason": "x"}\ntokens used\n11,343\n'
    assert extract_json(text)["candidate"] is True


def test_extract_json_takes_last_object():
    text = '{"old": 1}\nprogress line\n{"final": true}\n"tokens used" note'
    assert extract_json(text) == {"final": True}


def test_extract_json_nested():
    text = 'result: {"topics": [{"slug": "a", "n": {"b": 2}}], "ok": 1} done'
    assert extract_json(text)["topics"][0]["n"] == {"b": 2}


def test_extract_json_failure():
    with pytest.raises(Exception):
        extract_json("no json here at all")


def test_provider_model_labels():
    c = LLMClient.__new__(LLMClient)  # skip __init__ (reads settings)
    c.provider = "claude-cli"; c.model = ""
    assert c.model_label == "claude-cli:default"
    c.provider = "codex-cli"; c.model = "gpt-5.1-codex"
    assert c.model_label == "codex-cli:gpt-5.1-codex"
    c.provider = "openai"; c.model = ""
    assert c.model_label == "gpt-4o-mini"
