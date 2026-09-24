"""Every provider must actually deliver a `.system` statement to the model.

Regression test for DEFECT-002, where Anthropic, Mistral and xAI stashed the system text on the
provider and never sent it, and DeepSeek rewrote it into a "system: ..." user turn.

Three fixtures, each run once per provider with `--set $.llm_model=...`:
`sys-single`, `sys-multi`, `sys-none`.

Nothing in the CLI surface shows a request body, so delivery is proven by knowledge rather than
obedience: the system prompt carries a value the model could not otherwise know, and the test asks
for it back. A model that disobeys an instruction and a provider that dropped the text look
identical; a model that repeats a value it was never told does not.

The value is deliberately mundane. Earlier wordings ("internal codename", "access code") made
cautious models refuse to repeat it, which reads exactly like the dropped system prompt this test
exists to detect.

These are live, billed calls. A provider the account cannot reach is skipped, not failed.
"""

import json
import os

import pytest

from conftest import printed, run_prompt

MARK = "BANANA47"

# provider -> (env var holding its key, a small model that exists in the registry)
PROVIDERS = {
    "openai": ("OPENAI_API_KEY", "openai/gpt-4o-mini"),
    "anthropic": ("ANTHROPIC_API_KEY", "anthropic/claude-haiku-4-5"),
    "deepseek": ("DEEPSEEK_API_KEY", "deepseek/deepseek-chat"),
    "mistral": ("MISTRAL_API_KEY", "mistral/mistral-small-latest"),
    "xai": ("XAI_API_KEY", "xai/grok-2"),
    "cerebras": ("CEREBRAS_API_KEY", "cerebras/gpt-oss-120b"),
    "gemini": ("GOOGLE_API_KEY", "gemini/gemini-2.5-flash-lite"),
    "openrouter": ("OPENROUTER_API_KEY", "openrouter/anthropic/claude-3-haiku"),
}

# A provider the account cannot reach is not a system-prompt defect.
UNREACHABLE = ("not-found", "does not exist", "do not have access", "permission",
               "unauthorized", "invalid api key", "api error:")


def model_for(provider: str) -> str:
    key, model = PROVIDERS[provider]
    if not os.environ.get(key):
        pytest.skip(f"{key} not set")
    return model


def reply(provider: str, fixture: str) -> str:
    """Run a fixture against one provider; skip if the provider is unreachable."""
    envelope, result = run_prompt(fixture, "--set", f"$.llm_model={model_for(provider)}")
    if envelope["success"] is not True:
        detail = (json.dumps(envelope.get("error")) + result.stderr).lower()
        if any(marker in detail for marker in UNREACHABLE):
            pytest.skip(f"{provider} unreachable for this account: {detail[:160]}")
        pytest.fail(f"{provider} run failed: {envelope.get('error')}\n{result.stderr[-1500:]}")
    return printed(envelope)


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_system_prompt_reaches_the_model(provider):
    """The system text must reach the model -- proof it was delivered, not merely built."""
    answer = reply(provider, "sys-single")
    assert MARK in answer, (
        f"{provider} did not receive the system prompt.\nreply: {answer[:400]}")


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_multi_part_system_message_is_not_truncated(provider):
    """Two `.system` statements merge into one message; the second must survive.

    The marker is in the *second* line, so a provider that sends only `content[0]` fails here
    while passing the single-statement test.
    """
    answer = reply(provider, "sys-multi")
    assert MARK in answer, (
        f"{provider} dropped the second .system statement.\nreply: {answer[:400]}")


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_prompt_without_system_statement_still_runs(provider):
    """Gemini used to raise AttributeError when a prompt had no `.system` at all."""
    assert reply(provider, "sys-none").strip(), "no reply came back"
