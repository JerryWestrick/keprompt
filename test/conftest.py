"""Shared harness for driving the keprompt executable.

KePrompt is a command line tool, not a library. The contract is the executable, the `.prompt` file,
the JSON envelope and the database -- so tests run `keprompt` as a subprocess and assert on what a
user can see. Nothing here imports keprompt.

Prompts are real files in `test/prompts/`, not strings built at run time. A test names a prompt and
runs it, so you can open any fixture, edit it, and run the same command by hand:

    cd test
    python3 -m keprompt chats create quote-blank-lines --json
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).resolve().parent
PROMPTS = TEST_DIR / "prompts"


def run_cli(*args: str, offline: bool = False, timeout: int = 300, cwd: Path | None = None):
    """Invoke the executable from `test/`, the way a user does.

    `cwd` chooses another directory. `offline=True` strips provider API keys, proving a run
    needs no network. Returns (envelope, CompletedProcess).
    """
    env = dict(os.environ)
    if offline:
        for key in [k for k in env if k.endswith("_API_KEY")]:
            env.pop(key)

    result = subprocess.run(
        [sys.executable, "-m", "keprompt", *args, "--json"],
        cwd=cwd or TEST_DIR, capture_output=True, text=True, timeout=timeout, env=env,
    )
    note(commands={"args": list(args), "offline": offline})

    start = result.stdout.find("{")
    if start == -1:
        raise AssertionError(
            f"no JSON envelope on stdout\ncmd={args}\nstdout={result.stdout}\n"
            f"stderr={result.stderr[-3000:]}")
    envelope = json.loads(result.stdout[start:])
    note(envelope={"success": envelope.get("success"), "error": envelope.get("error"),
                   "chat_id": envelope.get("chat_id")})
    return envelope, result


def run_prompt(name: str, *extra: str, offline: bool = False, timeout: int = 300):
    """Run `test/prompts/<name>.prompt`."""
    assert (PROMPTS / f"{name}.prompt").exists(), f"missing fixture: prompts/{name}.prompt"
    note(prompts=name)
    return run_cli("chats", "create", name, *extra, offline=offline, timeout=timeout)


def ok(name: str, *extra: str, offline: bool = True) -> str:
    """Run a prompt that must succeed; return what it printed."""
    envelope, result = run_prompt(name, *extra, offline=offline)
    assert envelope["success"] is True, (
        f"{name} failed: {envelope.get('error')}\n{result.stderr[-1500:]}")
    return printed(envelope)


def fails(name: str, *extra: str, offline: bool = True) -> dict:
    """Run a prompt that must fail; return the envelope."""
    envelope, _ = run_prompt(name, *extra, offline=offline)
    assert envelope["success"] is False, f"{name} unexpectedly succeeded"
    return envelope


def printed(envelope: dict) -> str:
    """`.print` output as the user sees it.

    Rich draws a panel and reflows at the console width, so assertions should use short,
    single-line values rather than anything that could wrap.
    """
    return envelope.get("stdout") or ""


def chats_db() -> Path:
    return PROMPTS / "chats.db"


@pytest.fixture(scope="session", autouse=True)
def clean_database():
    """Start from an empty database so counts mean something. It is gitignored."""
    db = chats_db()
    if db.exists():
        db.unlink()
    yield db


# ---------------------------------------------------------------------------------------------
# Run report -- test/report.html, written after every run.
# ---------------------------------------------------------------------------------------------

RECORD: dict = {}
RESULTS: dict = {}


def current_test() -> str:
    return os.environ.get("PYTEST_CURRENT_TEST", "adhoc").split("::")[-1].split(" ")[0]


def note(**fields):
    """Attach a fact about the running test, for the report."""
    entry = RECORD.setdefault(current_test(), {"commands": [], "prompts": [], "chat_ids": []})
    for key, value in fields.items():
        if key in ("commands", "prompts", "chat_ids"):
            bucket = entry.setdefault(key, [])
            if value not in bucket:
                bucket.append(value)
        else:
            entry[key] = value


def pytest_runtest_logreport(report):
    if report.when != "call" and not (report.when == "setup" and report.outcome != "passed"):
        return
    name = report.nodeid.split("::")[-1]
    entry = RESULTS.setdefault(name, {"file": report.nodeid.split("::")[0], "duration": 0.0})
    entry["duration"] += report.duration
    if report.outcome != "passed" or "outcome" not in entry:
        entry["outcome"] = report.outcome
    if report.longrepr is not None:
        entry["detail"] = str(report.longrepr)[-4000:]
    if hasattr(report, "wasxfail"):
        entry["outcome"] = "xfailed"
        entry["detail"] = report.wasxfail


def pytest_sessionfinish(session, exitstatus):
    try:
        path = TEST_DIR / "report.html"
        path.write_text(_render_report())
        print(f"\nrun report: {path}")
    except Exception as e:      # a report must never break the run
        print(f"\ncould not write run report: {e}")


def _esc(text) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_report() -> str:
    from collections import Counter, defaultdict
    from datetime import datetime

    counts = Counter(r.get("outcome", "unknown") for r in RESULTS.values())
    total_time = sum(r.get("duration", 0.0) for r in RESULTS.values())
    by_file = defaultdict(list)
    for name, result in RESULTS.items():
        by_file[result["file"]].append((name, result))

    rows = []
    for filename in sorted(by_file):
        tests = sorted(by_file[filename])
        file_counts = Counter(r.get("outcome", "unknown") for _, r in tests)
        n = len(tests)
        rows.append(f'<p class="file">{_esc(filename)} · {n} {"test" if n == 1 else "tests"} · '
                    f'{" · ".join(f"{v} {k}" for k, v in sorted(file_counts.items()))}</p>')
        rows.extend(_render_test(name, result) for name, result in tests)

    summary = " ".join(f'<span class="pill {k}">{v} {k}</span>' for k, v in sorted(counts.items()))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KePrompt test run</title>
<style>
:root {{ --bg:#fbfbfa; --fg:#1b1b19; --muted:#6b6b66; --line:#e2e2dd; --card:#fff;
         --pass:#1a7f4b; --fail:#b3261e; --skip:#8a6d1f; --xfail:#5b5bd6; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#16161a; --fg:#e8e8e4; --muted:#9a9a94; --line:#2c2c32; --card:#1e1e23;
  --pass:#4ade80; --fail:#f87171; --skip:#fbbf24; --xfail:#a5b4fc; }} }}
:root[data-theme="dark"] {{ --bg:#16161a; --fg:#e8e8e4; --muted:#9a9a94; --line:#2c2c32;
  --card:#1e1e23; --pass:#4ade80; --fail:#f87171; --skip:#fbbf24; --xfail:#a5b4fc; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 ui-sans-serif,-apple-system,
       "Segoe UI",Roboto,sans-serif; padding:24px 16px 64px; }}
.wrap {{ max-width:1000px; margin:0 auto; }}
h1 {{ font-size:22px; margin:0 0 4px; }}
h2 {{ font-size:15px; margin:32px 0 8px; font-family:ui-monospace,Menlo,monospace; }}
.sub {{ color:var(--muted); font-weight:400; font-size:13px;
        font-family:ui-sans-serif,-apple-system,sans-serif; }}
.meta {{ color:var(--muted); font-size:13px; margin-bottom:16px; }}
.pill {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:13px;
         font-weight:600; margin-right:6px; border:1px solid var(--line); }}
.pill.passed {{ color:var(--pass); }} .pill.failed {{ color:var(--fail); }}
.pill.skipped {{ color:var(--skip); }} .pill.xfailed {{ color:var(--xfail); }}
details {{ background:var(--card); border:1px solid var(--line); border-radius:8px;
           margin:6px 0; overflow:hidden; }}
summary {{ cursor:pointer; padding:10px 12px; display:flex; gap:10px; align-items:baseline;
           list-style:none; }}
summary::-webkit-details-marker {{ display:none; }}
.dot {{ width:8px; height:8px; border-radius:50%; flex:none; margin-top:6px; }}
.dot.passed {{ background:var(--pass); }} .dot.failed {{ background:var(--fail); }}
.dot.skipped {{ background:var(--skip); }} .dot.xfailed {{ background:var(--xfail); }}
.tname {{ font-family:ui-monospace,Menlo,monospace; font-size:13px; flex:1; word-break:break-word; }}
.dur {{ color:var(--muted); font-size:12px; flex:none; }}
.file {{ color:var(--muted); font-size:13px; margin:28px 0 8px; font-family:ui-monospace,Menlo,monospace; }}
.test {{ margin: 0 0 8px; }}
.testhead {{ padding: 0 0 8px; }}
.run {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px;
        margin: 0 0 16px; padding: 14px 16px 8px; }}
.run > header {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
.run h3 {{ margin: 0; font-size: 16px; font-family: ui-sans-serif, -apple-system, sans-serif; }}
.inside {{ margin: 4px 0 12px 18px; padding: 2px 0 2px 14px; border-left: 3px solid var(--line); }}
.who {{ font-weight: 600; margin: 12px 0 4px; }}
.said {{ white-space: pre-wrap; margin: 0 0 4px; }}
.badge {{ display:inline-block; padding:4px 12px; border-radius:999px; font-size:13px;
          font-weight:700; letter-spacing:.04em; text-transform:uppercase; color:#fff; }}
.badge.passed {{ background:var(--pass); }}
.badge.failed, .badge.error {{ background:var(--fail); }}
.badge.skipped {{ background:var(--skip); }}
.badge.xfailed {{ background:var(--xfail); }}
h3.testname {{ font-size: 20px; margin: 20px 0 4px; font-family: ui-sans-serif, -apple-system, sans-serif; }}
h3.testname .mark.passed {{ color: var(--pass); }}
h3.testname .mark.failed, h3.testname .mark.error {{ color: var(--fail); }}
h3.testname .mark.skipped {{ color: var(--skip); }}
.question, .reply {{ white-space:pre-wrap; margin:0 0 12px; }}
.kicker {{ margin: 8px 0 12px; font-size: 13px; color: var(--muted); }}
.body {{ padding:0 12px 12px; border-top:1px solid var(--line); }}
.label {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
          margin:12px 0 4px; }}
pre {{ background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:10px;
       overflow-x:auto; font-size:12.5px; margin:0; font-family:ui-monospace,Menlo,monospace; }}
.tag {{ font-size:11px; border:1px solid var(--line); border-radius:4px; padding:1px 6px;
        color:var(--muted); }}
.step {{ margin:14px 0; }}
.step h3 {{ font-size:13px; margin:0 0 6px; font-family:ui-monospace,Menlo,monospace; }}
.step h3 .n {{ color:var(--muted); margin-right:8px; }}
.ok {{ color:var(--pass); }} .bad {{ color:var(--fail); }}
@media (max-width:600px) {{ body {{ padding:16px 16px 48px; }} }}
</style></head><body><div class="wrap">
<h1>KePrompt test run</h1>
<div class="meta">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &middot; {len(RESULTS)} {"test" if len(RESULTS) == 1 else "tests"}
  &middot; {total_time:.1f}s &middot; fixtures in <code>test/prompts/</code></div>
<div>{summary}</div>
{''.join(rows)}
</div></body></html>"""


def _result_failed(text: str) -> bool:
    head = text.lstrip().lower()
    return head.startswith("error") or head.startswith("rejected")


def _badge(outcome: str, word: str | None = None) -> str:
    cls = "failed" if outcome == "error" else outcome
    label = word or {"passed": "Passed", "failed": "Failed", "error": "Failed",
                     "skipped": "Skipped", "xfailed": "Xfailed"}.get(outcome, outcome)
    return f'<span class="badge {cls}">{label}</span>'


def _evaluate_text(part: dict) -> str:
    """The answers an .evaluate call stored on the chat."""
    lines = [part.get("set") or ""]
    answers = part.get("answers") or {}
    if not isinstance(answers, dict):
        lines.append(str(answers))
        return "\n".join(line for line in lines if line)
    for name, answer in answers.items():
        if not isinstance(answer, dict):
            lines.append(f"{name} = {answer}")
            continue
        lines.append(f"{name} = {answer.get('value')}")
        if answer.get("confidence") is not None:
            lines.append(f"confidence = {answer.get('confidence')}")
        for choice, probability in (answer.get("probabilities") or {}).items():
            lines.append(f"{choice} = {probability}")
    return "\n".join(line for line in lines if line)


def _params(arguments) -> str:
    if not isinstance(arguments, dict) or not arguments:
        return json.dumps(arguments, ensure_ascii=False, indent=2)
    lines = []
    for key, value in arguments.items():
        if isinstance(value, (dict, list)):
            shown = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            shown = str(value)
        lines.append(f"{key} = {shown}")
    return "\n".join(lines)


def _chat_html(chat_id: str) -> str:
    """One block per keprompt call: what it was given, what it called, what came back."""
    path = chats_db()
    if not path.exists():
        return f'<p class="meta">database {_esc(path)} does not exist</p>'
    db = sqlite3.connect(path)
    try:
        row = db.execute(
            "SELECT messages_json, vm_state_json FROM chats WHERE chat_id = ?", (chat_id,)
        ).fetchone()
    finally:
        db.close()
    if not row:
        return f'<p class="meta">chat {_esc(chat_id)} is not in {_esc(path)}</p>'

    state = json.loads(row[1]) if row[1] else {}
    defined = state.get("allowed_functions") or []
    grant = ", ".join(defined) if defined else "(none)"

    turns: list[dict] = []
    current = None
    pending: dict[str, dict] = {}
    pending_evals: list[dict] = []

    def turn() -> dict:
        nonlocal current
        if current is None:
            current = {"question": "", "calls": [], "reply": [], "evaluations": []}
            turns.append(current)
        return current

    for message in json.loads(row[0]):
        role = message.get("role") or ""
        if role == "system":
            continue
        for part in message.get("content") or []:
            kind = part.get("type")
            if kind == "ldm":
                if current is None:
                    pending_evals.append(part)
                else:
                    current.setdefault("evaluations", []).append(part)
            elif kind == "text" and role == "user" and part.get("text"):
                current = {"question": part["text"].strip(), "calls": [], "reply": [],
                           "evaluations": pending_evals}
                pending_evals = []
                turns.append(current)
            elif kind == "text" and role == "assistant" and part.get("text"):
                turn()["reply"].append(part["text"].strip())
            elif kind == "tool":
                call = {"name": part.get("name") or "", "arguments": part.get("arguments") or {},
                        "return": None}
                pending[part.get("id")] = call
                turn()["calls"].append(call)
            elif kind == "tool_result":
                call = pending.get(part.get("tool_use_id"))
                if call is None:
                    call = {"name": "", "arguments": {}, "return": part.get("content", "")}
                    turn()["calls"].append(call)
                else:
                    call["return"] = part.get("content", "")

    asked = [item for item in turns if item["question"]]
    total = len(asked)
    blocks = [f'<p class="kicker">keprompt called {total} {"time" if total == 1 else "times"}</p>']
    for number, item in enumerate(asked, 1):
        failed = any(
            _result_failed(call["return"] or "")
            for call in item["calls"]
            if call["return"] is not None
        )
        mark = "failed" if failed else "passed"
        verb = "chats create" if number == 1 else "chat reply"
        bits = [
            '<section class="run">',
            f'<header><h3>{number} of {total} · {_esc(verb)}</h3>'
            f'{_badge(mark, "Fail" if failed else "Pass")}</header>',
        ]
        for part in item.get("evaluations") or []:
            bits.append('<p class="who">.evaluate</p>'
                        f'<div class="said">{_esc(_evaluate_text(part))}</div>')
        bits.append(
            '<p class="who">keprompt was called with</p>'
            f'<div class="said">{_esc(item["question"])}</div>'
            '<p class="who">functions defined</p>'
            f'<div class="said">{_esc(grant)}</div>'
        )
        if item["calls"]:
            bits.append('<div class="inside">')
            for call in item["calls"]:
                returned = call["return"] if call["return"] is not None else ""
                call_failed = _result_failed(returned)
                name = call["name"] or "function"
                bits.append(
                    f'<p class="who">keprompt called {_esc(name)}</p>'
                    f'<div class="said">{_esc(_params(call["arguments"]))}</div>'
                    f'<p class="who">{_esc(name)} responded {_badge("failed" if call_failed else "passed", "Fail" if call_failed else "Pass")}</p>'
                    f'<div class="said">{_esc(returned)}</div>'
                )
            bits.append('</div>')
        if item["reply"]:
            bits.append('<p class="who">keprompt responded</p>'
                        f'<div class="said">{_esc(chr(10).join(item["reply"]))}</div>')
        bits.append("</section>")
        blocks.append("".join(bits))
    return "".join(blocks) if asked else '<p class="meta">no messages</p>'


def _render_test(name: str, result: dict) -> str:
    outcome = result.get("outcome", "unknown")
    # RECORD is keyed by the sanitised test name, so a parametrised test's brackets must be
    # matched the same way or it renders with an empty body.
    recorded = RECORD.get(name) or RECORD.get(re.sub(r"[^A-Za-z0-9_-]", "-", name), {})
    parts = []

    for prompt in recorded.get("prompts", []):
        path = PROMPTS / f"{prompt}.prompt"
        body = path.read_text() if path.exists() else "(missing)"
        parts.append(f'<div class="label">test/prompts/{_esc(prompt)}.prompt</div>'
                     f'<pre>{_esc(body)}</pre>')

    chat_ids = list(recorded.get("chat_ids") or [])
    single = recorded.get("chat_id")
    if single and single not in chat_ids:
        chat_ids.append(single)
    for chat_id in chat_ids:
        parts.append(f'<div class="label">chat {_esc(chat_id)}</div>' + _chat_html(chat_id))

    calls = recorded.get("calls") or []
    if calls and not chat_ids:
        steps = []
        for i, call in enumerate(calls, 1):
            mark = "ok" if call.get("ok", True) else "bad"
            args = json.dumps(call.get("args") or {}, indent=2, ensure_ascii=False)
            steps.append(
                f'<div class="step"><h3><span class="n">{i:02d}</span>'
                f'<span class="{mark}">{_esc(call.get("fn", ""))}</span></h3>'
                f'<div class="label">arguments</div><pre>{_esc(args)}</pre>'
                f'<div class="label">result</div><pre>{_esc(call.get("result", ""))}</pre></div>'
            )
        parts.append("".join(steps))

    for command in recorded.get("commands", []):
        tag = "offline" if command["offline"] else "live"
        parts.append(f'<div class="label">command <span class="tag">{tag}</span></div>'
                     f'<pre>cd test\npython3 -m keprompt '
                     f'{_esc(" ".join(command["args"]))} --json</pre>')

    envelope = recorded.get("envelope")
    if envelope and not chat_ids:
        parts.append('<div class="label">envelope</div>'
                     f'<pre>{_esc(json.dumps(envelope, indent=2))}</pre>')

    if result.get("detail"):
        label = "failure" if outcome in ("failed", "error") else "reason"
        parts.append(f'<div class="label">{label}</div><pre>{_esc(result["detail"])}</pre>')

    meta = f'{result.get("duration", 0):.2f}s'
    if chat_ids:
        meta += " · " + " ".join(_esc(chat_id) for chat_id in chat_ids)
    word = {"passed": "Passed", "failed": "Failed", "error": "Failed",
            "skipped": "Skipped", "xfailed": "Xfailed"}.get(outcome, outcome)
    mark = "failed" if outcome == "error" else outcome
    body = "".join(parts)
    return (f'<h3 class="testname">{_esc(name)} : <span class="mark {mark}">{word}</span></h3>'
            f'<article class="test {outcome}">'
            f'<header class="testhead">'
            f'<p class="meta">{_esc(result.get("file", ""))} · {meta}</p></header>'
            f'{body}</article>')
