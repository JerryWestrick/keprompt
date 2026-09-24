"""Module-qualified function specs in `.functions`: bare names, `module.*`, `module.func`, errors.

Fixtures are `test/prompts/fn-*.prompt`, run against `test/prompts/functions/demo_tools.py` -- a
real provider, because providers are discovered by executing them.

Note what the CLI can and cannot see. Every error is visible in the envelope and asserted exactly.
Success is only observable as "the run did not fail": nothing in the CLI surface reports which
functions a `.functions` statement resolved to, short of a real model call with tools.
"""

import json

from conftest import fails, ok, run_cli


def test_provider_is_discovered():
    envelope, _ = run_cli("functions", "list", offline=True)
    listed = json.dumps(envelope)
    assert "alpha" in listed and "beta" in listed


# --- bare names --------------------------------------------------------------------------------

def test_bare_names():
    assert "ok" in ok("fn-bare-names")


def test_bare_name_unknown():
    assert "nope" in json.dumps(fails("fn-bare-unknown"))


def test_builtin_bare_name():
    assert "ok" in ok("fn-builtin")


# --- module.* wildcard --------------------------------------------------------------------

def test_wildcard():
    assert "ok" in ok("fn-wildcard")


def test_wildcard_unknown_module():
    text = json.dumps(fails("fn-wildcard-unknown-module"))
    assert "unknown module" in text and "nosuch" in text


def test_unknown_module_error_lists_what_is_available():
    assert "demo_tools" in json.dumps(fails("fn-wildcard-unknown-module"))


# --- module.func -------------------------------------------------------------------------

def test_module_qualified_function():
    assert "ok" in ok("fn-module-qualified")


def test_module_qualified_unknown_function():
    assert "nope" in json.dumps(fails("fn-module-unknown-func"))


def test_mixed_specs():
    assert "ok" in ok("fn-mixed")


# --- no .functions at all ------------------------------------------------------------------

def test_prompt_without_functions_runs():
    """No `.functions` means the model gets no tools -- the safe default, not an error."""
    assert "ok" in ok("fn-none")


def test_empty_functions_is_an_error():
    assert "required" in json.dumps(fails("fn-empty"))
