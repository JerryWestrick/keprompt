"""Every provider must carry a .system statement to the model in its own native slot.

Anthropic, Mistral and XAI used to stash the system text on the provider and never send
it; DeepSeek rewrote it into a "system: ..." user turn; Gemini raised AttributeError when
a prompt had no .system at all.
"""

import json
from unittest.mock import patch

import pytest

# Importing the adapters registers them with ModelManager.
import keprompt.AiAnthropic  # noqa: F401
import keprompt.AiCerebras  # noqa: F401
import keprompt.AiDeepSeek  # noqa: F401
import keprompt.AiGoogle  # noqa: F401
import keprompt.AiMistral  # noqa: F401
import keprompt.AiOpenAi  # noqa: F401
import keprompt.AiOpenRouter  # noqa: F401
import keprompt.AiXai  # noqa: F401
from keprompt.ModelManager import ModelManager
from keprompt.keprompt_vm import VM, make_statement

MARK = "SYSTEM-PROMPT-MARKER-42"

PROVIDERS = ["anthropic", "cerebras", "deepseek", "gemini", "mistral", "openai", "openrouter", "xai"]

# Where each provider is expected to carry the system prompt.
TOP_LEVEL_SYSTEM = {"anthropic"}
SYSTEM_INSTRUCTION = {"gemini"}
# everything else: a {"role": "system"} entry in messages


class _StubModel:
    def get_api_model_name(self):
        return "stub-model"


def build_request(provider: str, system_lines: list[str]):
    vm = VM()
    n = 0
    for line in system_lines:
        make_statement(vm, n, ".system", line).execute(vm)
        n += 1
    make_statement(vm, n, ".user", "Hello there.").execute(vm)

    vm.prompt.model = "stub/stub-model"
    vm.prompt.model_lookup_key = "stub/stub-model"
    provider_obj = ModelManager.handlers[provider](vm.prompt)
    with patch.object(ModelManager, "get_model", return_value=_StubModel()):
        company = provider_obj.to_company_messages(vm.prompt.messages)
        return provider_obj.prepare_request(company)


def locate(req: dict) -> str:
    """Return a label for where MARK appears in the request, or 'absent'."""
    if req.get("system") and MARK in json.dumps(req["system"]):
        return "top-level-system"
    if MARK in json.dumps(req.get("system_instruction", "")):
        return "system-instruction"
    for msg in req.get("messages", []):
        if MARK in json.dumps(msg.get("content", "")):
            return f"message-role-{msg.get('role')}"
    return "absent"


@pytest.mark.parametrize("provider", PROVIDERS)
def test_system_prompt_reaches_the_request(provider):
    req = build_request(provider, [MARK])

    if provider in TOP_LEVEL_SYSTEM:
        expected = "top-level-system"
    elif provider in SYSTEM_INSTRUCTION:
        expected = "system-instruction"
    else:
        expected = "message-role-system"

    assert locate(req) == expected


@pytest.mark.parametrize("provider", PROVIDERS)
def test_prompt_without_system_statement_does_not_raise(provider):
    req = build_request(provider, [])
    assert locate(req) == "absent"
    assert not req.get("system")
    assert not req.get("system_instruction")


@pytest.mark.parametrize("provider", PROVIDERS)
def test_multi_part_system_message_is_not_truncated(provider):
    """Consecutive .system statements merge into one message with several text parts.

    Reading only content[0] silently dropped everything after the first line.
    """
    req = build_request(provider, [MARK, "SECOND-LINE-99"])
    body = json.dumps(req)
    assert MARK in body
    assert "SECOND-LINE-99" in body


def test_anthropic_does_not_put_system_in_messages():
    """Anthropic rejects a system role in messages, and never as messages[0]."""
    req = build_request("anthropic", [MARK])
    assert req["system"] == MARK
    assert all(msg["role"] != "system" for msg in req["messages"])


def test_deepseek_sends_a_real_system_role_not_a_user_turn():
    """Regression: system used to be rewritten to {"role":"user","content":"system: ..."}."""
    req = build_request("deepseek", [MARK])
    system_msgs = [m for m in req["messages"] if m["role"] == "system"]
    assert len(system_msgs) == 1
    assert system_msgs[0]["content"] == MARK
    assert not any("system: " in json.dumps(m) for m in req["messages"] if m["role"] == "user")
