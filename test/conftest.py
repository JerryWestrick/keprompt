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
import subprocess
import sys
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).resolve().parent
PROMPTS = TEST_DIR / "prompts"


def run_cli(*args: str, offline: bool = False, timeout: int = 300):
    """Invoke the executable from `test/`, the way a user does.

    `offline=True` strips provider API keys, proving a run needs no network.
    Returns (envelope, CompletedProcess).
    """
    env = dict(os.environ)
    if offline:
        for key in [k for k in env if k.endswith("_API_KEY")]:
            env.pop(key)

    result = subprocess.run(
        [sys.executable, "-m", "keprompt", *args, "--json"],
        cwd=TEST_DIR, capture_output=True, text=True, timeout=timeout, env=env,
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
    entry = RECORD.setdefault(current_test(), {"commands": [], "prompts": []})
    for key, value in fields.items():
        if key in ("commands", "prompts"):
            if value not in entry[key]:
                entry[key].append(value)
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
        rows.append(f'<h2>{_esc(filename)} <span class="sub">{len(tests)} tests &middot; '
                    f'{" &middot; ".join(f"{v} {k}" for k, v in sorted(file_counts.items()))}'
                    f'</span></h2>')
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
.body {{ padding:0 12px 12px; border-top:1px solid var(--line); }}
.label {{ font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
          margin:12px 0 4px; }}
pre {{ background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:10px;
       overflow-x:auto; font-size:12.5px; margin:0; font-family:ui-monospace,Menlo,monospace; }}
.tag {{ font-size:11px; border:1px solid var(--line); border-radius:4px; padding:1px 6px;
        color:var(--muted); }}
@media (max-width:600px) {{ body {{ padding:16px 16px 48px; }} }}
</style></head><body><div class="wrap">
<h1>KePrompt test run</h1>
<div class="meta">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &middot; {len(RESULTS)} tests
  &middot; {total_time:.1f}s &middot; fixtures in <code>test/prompts/</code></div>
<div>{summary}</div>
{''.join(rows)}
</div></body></html>"""


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

    for command in recorded.get("commands", []):
        tag = "offline" if command["offline"] else "live"
        parts.append(f'<div class="label">command <span class="tag">{tag}</span></div>'
                     f'<pre>cd test\npython3 -m keprompt '
                     f'{_esc(" ".join(command["args"]))} --json</pre>')

    envelope = recorded.get("envelope")
    if envelope:
        parts.append('<div class="label">envelope</div>'
                     f'<pre>{_esc(json.dumps(envelope, indent=2))}</pre>')

    if result.get("detail"):
        label = "failure" if outcome in ("failed", "error") else "reason"
        parts.append(f'<div class="label">{label}</div><pre>{_esc(result["detail"])}</pre>')

    body = f'<div class="body">{"".join(parts)}</div>' if parts else ""
    return (f'<details{" open" if outcome in ("failed", "error") else ""}>'
            f'<summary><span class="dot {outcome}"></span>'
            f'<span class="tname">{_esc(name)}</span>'
            f'<span class="dur">{result.get("duration", 0):.2f}s</span></summary>{body}</details>')
