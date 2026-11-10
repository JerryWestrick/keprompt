"""`.print` goes through Rich Markdown, which turns a plain newline into a space."""

from rich.console import Console
from rich.markdown import Markdown

from keprompt.keprompt_vm import VM, markdown_keep_breaks


def _render(text: str) -> str:
    console = Console(width=80, record=True, force_terminal=True)
    console.print(Markdown(markdown_keep_breaks(text)))
    return console.export_text()


def test_output_flag_is_the_child_format_switch():
    vm = VM()
    assert vm.substitute("keprompt chats create epicure-query <<VM.output_flag>>") == (
        "keprompt chats create epicure-query --json"
    )
    vm.output_flag = "--pretty"
    assert vm.substitute("<<VM.output_flag>>") == "--pretty"


def test_json_lines_stay_lines():
    text = '{\n  "success": true,\n  "chat_id": "746c3409"\n}'
    out = _render(text)
    success = next(ln for ln in out.splitlines() if "success" in ln)
    assert "chat_id" not in success
    assert '"chat_id": "746c3409"' in out


def test_markdown_table_still_renders():
    text = "| a | b |\n|---|---|\n| 1 | 2 |"
    out = _render(text)
    assert "────" in out
    rows = [ln for ln in out.splitlines() if "a" in ln or "1" in ln]
    assert len(rows) >= 2
