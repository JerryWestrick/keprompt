"""`llm_options` is the only place for model request options.

Fixtures are `test/prompts/opt-*.prompt`.

One behaviour is not asserted here: that `llm_options` is merged onto the outgoing request.
Nothing in the CLI surface shows a request body, so proving it would mean a billed call and
trusting a provider's error text. What the CLI can prove is the contract that matters to a prompt
author -- the old top-level names are refused, loudly, before any call is made.
"""

import json

from conftest import fails, ok, printed, run_prompt


# --- always present, addressable ------------------------------------------------------------

def test_llm_options_exists_by_default():
    assert "opts={}" in ok("opt-default")


def test_prompt_params_populate_it():
    assert "effort=none" in ok("opt-from-params")


def test_cli_set_wins_over_prompt_params():
    """`--set-from-json` overrides what the prompt declares."""
    from conftest import TEST_DIR
    path = TEST_DIR / "opts.json"
    path.write_text(json.dumps({"llm_options": {"reasoning_effort": "high"}}))
    assert "effort=high" in ok("opt-from-params", "--set-from-json", str(path))


def test_the_same_option_inside_llm_options_is_accepted():
    """The name is not banned -- only its placement."""
    assert "t=0.2" in ok("opt-temperature-inside")


# --- the old top-level names stop the run ------------------------------------------------------

def assert_refused(name: str, option: str):
    text = json.dumps(fails(name))
    assert option in text and "llm_options" in text, text[:600]


def test_top_level_temperature_is_refused():
    assert_refused("opt-top-level-temperature", "temperature")


def test_top_level_max_tokens_is_refused():
    assert_refused("opt-exec-json-max-tokens", "max_tokens")


def test_top_level_top_p_is_refused():
    assert_refused("opt-top-level-top-p", "top_p")


def test_top_level_top_k_is_refused():
    assert_refused("opt-top-level-top-k", "top_k")


def test_prompt_params_top_level_option_is_refused():
    assert_refused("opt-params-top-level", "temperature")


def test_refusal_stops_execution_without_contacting_a_provider():
    """`.exec` refuses on the spot: nothing after it runs.

    The run is made with provider keys stripped, so reaching the refusal at all proves it happens
    before any provider is contacted.
    """
    envelope, _ = run_prompt("opt-top-level-temperature", offline=True)
    assert envelope["success"] is False
    assert "SHOULD-NOT-APPEAR" not in printed(envelope)
