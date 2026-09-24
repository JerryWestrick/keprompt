"""Multi-line quotes: `<<<ID` opens, a line of exactly `>>>ID` closes, content is verbatim.

Each case is a real prompt in `test/prompts/quote-*.prompt`. Open one to see exactly what is under
test, or run it yourself:

    cd test && python3 -m keprompt chats create quote-opener-tail --json

These need no network: every fixture ends in `.exit`, so no `.exec` is appended.
"""

import json

from conftest import fails, ok


# --- content is content, not syntax ----------------------------------------------------------

def test_blank_lines_and_indentation_survive():
    out = ok("quote-blank-lines")
    assert "alpha" in out and "indented" in out


def test_dot_keywords_inside_the_quote_are_content():
    """`.exit` in the body must not end the prompt."""
    assert "got=.exit" in ok("quote-keyword-inside")


def test_near_miss_terminator_is_content():
    assert "got=>>>WRONG" in ok("quote-near-miss-terminator")


def test_terminator_tolerates_trailing_space():
    assert "got=body" in ok("quote-trailing-space")


def test_indented_terminator_does_not_close():
    """The terminator must start the line."""
    assert "got=>>>Q" in ok("quote-indented-terminator")


# --- how the body joins the statement --------------------------------------------------------

def test_text_before_the_marker_is_kept():
    assert "hello world" in ok("quote-text-before-marker")


def test_opener_line_continues_after_the_marker():
    """Standard heredoc: the opener does not have to end the line."""
    assert "one middle two" in ok("quote-opener-tail")


def test_identifier_allows_any_non_space_characters():
    assert "got=body" in ok("quote-identifier-charset")


def test_identifier_is_author_chosen():
    """Content colliding with one terminator is handled by choosing another."""
    assert "got=>>>Q here" in ok("quote-author-chosen-id")


# --- substitution ------------------------------------------------------------------------------

def test_variables_inside_the_quote_are_substituted():
    assert "got=Hello World." in ok("quote-substitution")


def test_delimiters_are_not_bound_to_prefix_postfix():
    """Quote markers are parse-time literals; `Prefix`/`Postfix` are runtime state."""
    assert "got=body" in ok("quote-delimiters-fixed")


# --- errors are visible through the envelope ---------------------------------------------------

def test_unclosed_quote_is_an_error():
    assert "never closed" in json.dumps(fails("quote-unclosed"))


def test_quoted_identifier_is_reserved():
    assert "reserved" in json.dumps(fails("quote-reserved-nowdoc"))
