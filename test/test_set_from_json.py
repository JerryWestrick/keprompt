"""`--set-from-json`: file load, JSON types, merge with `--set`, and failure envelopes.

`--set-from-json` is a CLI flag, so the CLI is the only place its behaviour is defined. The
prompts are fixtures in `test/prompts/vars-*.prompt`; the JSON files are written per test, since
they are the flag's argument rather than the thing under test.
"""

import json

from conftest import TEST_DIR, fails, ok, printed, run_prompt

VARS = TEST_DIR / "vars.json"


def vars_file(payload) -> str:
    VARS.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    return str(VARS)


# --- loading ------------------------------------------------------------------------------------

def test_variables_reach_the_prompt():
    out = ok("vars-echo", "--set-from-json", vars_file({"name": "Jerry"}))
    assert "name=Jerry" in out


def test_json_types_are_preserved():
    """A number stays a number and a nested object stays addressable."""
    out = ok("vars-types", "--set-from-json",
             vars_file({"count": 42, "addr": {"city": "Merida"}}))
    assert "n=42" in out and "city=Merida" in out


def test_empty_object_is_accepted():
    assert "ok" in ok("vars-plain", "--set-from-json", vars_file({}))


# --- merging with --set ---------------------------------------------------------------------

def test_set_wins_on_a_matching_key():
    out = ok("vars-who", "--set-from-json", vars_file({"who": "from-json"}),
             "--set", "who=from-flag")
    assert "who=from-flag" in out


def test_keys_from_both_sources_are_present():
    out = ok("vars-two-keys", "--set-from-json", vars_file({"a": "1"}), "--set", "b=2")
    assert "a=1" in out and "b=2" in out


def test_prompt_statements_override_loaded_variables():
    """`.set` in the prompt runs after the CLI has seeded variables."""
    out = ok("vars-statement-wins", "--set-from-json", vars_file({"who": "from-json"}))
    assert "who=statement" in out


# --- failures are reported in the envelope ----------------------------------------------------

def test_missing_file_fails():
    envelope = fails("vars-plain", "--set-from-json", str(TEST_DIR / "nope.json"))
    text = json.dumps(envelope).lower()
    assert "not found" in text or "no such file" in text, envelope


def test_invalid_json_fails():
    assert "json" in json.dumps(fails("vars-plain", "--set-from-json",
                                      vars_file("{not json"))).lower()


def test_array_is_rejected():
    assert "object" in json.dumps(fails("vars-plain", "--set-from-json",
                                        vars_file([1, 2, 3]))).lower()


def test_scalar_is_rejected():
    assert "object" in json.dumps(fails("vars-plain", "--set-from-json",
                                        vars_file("42"))).lower()


def test_a_bad_file_fails_before_the_prompt_runs():
    """Nothing should execute, so nothing should be printed."""
    envelope, _ = run_prompt("vars-should-not-print", "--set-from-json",
                             str(TEST_DIR / "missing.json"), offline=True)
    assert envelope["success"] is False
    assert "SHOULD-NOT-APPEAR" not in printed(envelope)
