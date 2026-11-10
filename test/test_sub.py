""".sub runs a file of keprompt lines on this VM, then returns to the caller.

Fragments live in `test/prompts/*.lines` so they are not programs. Each parent ends in `.exit`,
so these need no network. Open a fixture and run it the same way:

    cd test && python3 -m keprompt chats create sub-set --json
"""

import json

from conftest import PROMPTS, fails, ok


def test_a_set_in_the_fragment_is_visible_after_sub():
    out = ok("sub-set")
    assert "marker=FROM-SUB" in out


def test_the_statement_after_sub_runs():
    assert "after" in ok("sub-set")


def test_exit_in_the_fragment_skips_the_rest_of_the_caller():
    out = ok("sub-exit")
    assert "inside" in out and "after" not in out


def test_the_path_is_substituted():
    assert "marker=FROM-SUB" in ok("sub-path", "--set", "which", "sub-set")


def test_a_bare_name_opens_under_prompts():
    out = ok("sub-bare")
    assert "marker=FROM-SUB" in out and "after" in out


def test_an_absolute_path_is_opened_as_written():
    where = str(PROMPTS / "sub-set.lines")
    assert "marker=FROM-SUB" in ok("sub-abs", "--set", "where", where)


def test_a_dot_path_is_opened_as_written():
    text = json.dumps(fails("sub-dot"))
    assert "./sub-set.lines" in text and "prompts/./" not in text and "prompts/sub-set.lines" not in text


def test_a_bare_missing_name_is_looked_up_under_prompts():
    assert "prompts/no-such-fragment.lines" in json.dumps(fails("sub-bare-missing"))


def test_a_fragment_does_not_get_an_automatic_exec():
    assert "only-print" in ok("sub-noexec")


def test_a_missing_file_fails():
    assert "no-such-fragment.lines" in json.dumps(fails("sub-missing"))


def test_a_nested_sub_returns_to_the_outer_fragment_then_the_parent():
    out = ok("sub-nested")
    assert "marker=FROM-SUB" in out and "outer" in out and "parent" in out


def test_functions_in_the_fragment_run_and_the_parent_continues():
    out = ok("sub-functions")
    assert "granted" in out and "after" in out


def test_an_unknown_guard_fails_before_the_fragment_runs():
    envelope = fails("sub-unknown-guard")
    text = json.dumps(envelope)
    assert "#._missing" in text and "ran" not in text
