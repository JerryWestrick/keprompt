"""Multi-line quotes: `<<<ID` opens, a line of exactly `>>>ID` closes, content is verbatim."""

import pytest

from keprompt.keprompt_vm import VM, StmtSyntaxError


def parse(tmp_path, body: str) -> VM:
    path = tmp_path / "t.prompt"
    path.write_text('.prompt "name":"T", "version":"1.0.0"\n' + body)
    return VM(filename=str(path))


def values(vm: VM) -> dict[str, str]:
    """Last value seen per keyword, ignoring the auto-appended completion statements."""
    return {s.keyword: s.value for s in vm.statements}


def test_content_is_verbatim(tmp_path):
    vm = parse(tmp_path, ".system <<<SYS\nline one\n\n    indented\n>>>SYS\n")
    assert values(vm)[".system"] == "line one\n\n    indented"


def test_keywords_inside_quote_are_content(tmp_path):
    vm = parse(tmp_path, ".system <<<SYS\n.exit\n.user not a statement\n>>>SYS\n.print after\n")
    assert values(vm)[".system"] == ".exit\n.user not a statement"
    assert values(vm)[".print"] == "after"


def test_near_miss_terminator_is_content(tmp_path):
    vm = parse(tmp_path, ".system <<<SYS\n>>>WRONG\n  >>>SYS\n>>>SYS\n")
    assert values(vm)[".system"] == ">>>WRONG\n  >>>SYS"


def test_terminator_tolerates_trailing_space(tmp_path):
    vm = parse(tmp_path, ".system <<<SYS\nbody\n>>>SYS   \n")
    assert values(vm)[".system"] == "body"


def test_text_before_marker_is_kept(tmp_path):
    vm = parse(tmp_path, ".user Hello <<<MSG\nworld\n>>>MSG\n")
    assert values(vm)[".user"] == "Hello world"


def test_set_name_survives_quote(tmp_path):
    vm = parse(tmp_path, ".set greeting <<<G\nhola\nadios\n>>>G\n")
    assert values(vm)[".set"] == "greeting hola\nadios"


def test_variables_are_substituted_at_runtime(tmp_path):
    vm = parse(tmp_path, ".system <<<SYS\nHello <<who>>.\n>>>SYS\n")
    vm.set_variable("who", "World")
    assert vm.substitute(values(vm)[".system"]) == "Hello World."


def test_identifier_is_author_chosen(tmp_path):
    vm = parse(tmp_path, ".system <<<ZZZ\n>>>SYS is only text here\n>>>ZZZ\n")
    assert values(vm)[".system"] == ">>>SYS is only text here"


def test_identifier_allows_any_non_space_characters(tmp_path):
    vm = parse(tmp_path, ".system <<<user-text\nbody\n>>>user-text\n.user <<<msg.2_a!\nmore\n>>>msg.2_a!\n")
    assert values(vm)[".system"] == "body"
    assert values(vm)[".user"] == "more"


def test_unclosed_quote_is_an_error(tmp_path):
    with pytest.raises(StmtSyntaxError, match="never closed"):
        parse(tmp_path, ".system <<<SYS\nno terminator\n")


def test_quoted_identifier_is_reserved(tmp_path):
    with pytest.raises(StmtSyntaxError, match="reserved"):
        parse(tmp_path, ".system <<<'SYS'\nbody\n>>>SYS\n")


def test_delimiters_ignore_prefix_postfix(tmp_path):
    """Prefix/Postfix are runtime variables; the quote markers are parse-time literals."""
    vm = parse(tmp_path, ".set Prefix ((\n.set Postfix ))\n.system <<<SYS\nbody\n>>>SYS\n")
    assert values(vm)[".system"] == "body"
