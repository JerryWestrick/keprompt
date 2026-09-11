"""Reserved llm_options dict: always present, merged onto the request, old top-level keys stop."""

from unittest.mock import patch

import pytest

from keprompt.AiPrompt import AiMessage, AiTextPart
from keprompt.AiProvider import AiProvider
from keprompt.keprompt_vm import VM, StmtSyntaxError, make_statement


def test_llm_options_always_present():
    vm = VM()
    assert vm.vdict["llm_options"] == {}


def test_prompt_params_set_llm_options():
    vm = VM()
    stmt = make_statement(
        vm,
        0,
        ".prompt",
        '"name":"T", "version":"1.0.0", "params":{"model":"x", "llm_options":{"reasoning_effort":"none"}}',
    )
    stmt.execute(vm)
    assert vm.vdict["llm_options"] == {"reasoning_effort": "none"}
    assert vm.vdict["model"] == "x"


def test_cli_llm_options_not_overwritten_by_prompt():
    vm = VM(params={"llm_options": {"temperature": 0.1}})
    stmt = make_statement(
        vm,
        0,
        ".prompt",
        '"name":"T", "version":"1.0.0", "params":{"llm_options":{"reasoning_effort":"none"}}',
    )
    stmt.execute(vm)
    assert vm.vdict["llm_options"] == {"temperature": 0.1}


def test_top_level_temperature_stops_exec():
    vm = VM()
    vm.vdict["temperature"] = 0.2
    stmt = make_statement(vm, 0, ".exec", "")
    with pytest.raises(StmtSyntaxError, match="temperature must be moved into llm_options"):
        stmt.execute(vm)


def test_top_level_keys_in_exec_json_stop():
    vm = VM()
    stmt = make_statement(vm, 0, ".exec", '{"model":"x", "max_tokens": 10}')
    with pytest.raises(StmtSyntaxError, match="max_tokens must be moved into llm_options"):
        stmt.execute(vm)


class _FakeProvider(AiProvider):
    def prepare_request(self, messages):
        return {"model": "m", "messages": messages}

    def get_api_url(self):
        return "http://example.invalid"

    def get_headers(self):
        return {}

    def to_company_messages(self, messages):
        return [{"role": "user", "content": "hi"}]

    def to_ai_message(self, response):
        return AiMessage(
            vm=self.prompt.vm,
            role="assistant",
            content=[AiTextPart(vm=self.prompt.vm, text="ok")],
        )

    def extract_token_usage(self, response):
        return (0, 0)

    def calculate_costs(self, tokens_in, tokens_out):
        return (0.0, 0.0)


def test_llm_options_merged_onto_request():
    vm = VM()
    vm.vdict["llm_options"] = {"reasoning_effort": "none", "temperature": 0.2}
    captured = {}

    def fake_api(url, headers, data, label):
        captured["data"] = data
        return {}

    provider = _FakeProvider(vm.prompt)
    with (
        patch.object(provider, "make_api_request", side_effect=fake_api),
        patch.object(provider, "call_functions", return_value=None),
        patch.object(provider, "_display_llm_text_response"),
    ):
        provider.call_llm(label="00 .exec")

    assert captured["data"]["reasoning_effort"] == "none"
    assert captured["data"]["temperature"] == 0.2
    assert captured["data"]["model"] == "m"
