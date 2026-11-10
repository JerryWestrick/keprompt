"""Chat log for the workspace database.

A closed head asks this program for the next row of HTML. An open head drops
its children in the browser. The database is the one KePrompt writes:
prompts/chats.db in the current directory, or the database URL in config.
"""

import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from pathlib import Path

from keprompt.keprompt_util import sub_path
from urllib.parse import urlparse

DB = Path("prompts/chats.db")
HOST = "127.0.0.1"
PORT = 8765

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>chats</title>
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<style>
  body { margin: 0; color: #16191f; background: #fff;
         font: 13px/1.35 ui-monospace, "Lucida Console", Consolas, monospace; }
  .bar { padding: 12px 16px 8px; border-bottom: 1px solid #eaeded; }
  .bar h1 { margin: 0; font: 600 18px/1.2 system-ui, sans-serif; }
  .meta { margin: 2px 0 0; color: #5f6b7a; font: 12px/1.3 system-ui, sans-serif; }
  .cols { display: flex; gap: 12px; padding: 6px 8px 6px 28px; background: #fafafa;
          border-bottom: 1px solid #eaeded; color: #5f6b7a;
          font: 12px/1.3 system-ui, sans-serif; }
  .cols .when, .head .when { width: 230px; flex: none; }
  .node { margin: 0; }
  .head { display: flex; gap: 12px; align-items: baseline; width: 100%; text-align: left;
          background: #fff; border: 0; border-bottom: 1px solid #eaeded;
          padding: 4px 8px; font: inherit; color: inherit; cursor: pointer; }
  .head:hover, .head.open { background: #f2f8fd; }
  .head::before { content: "\\25B8"; color: #5f6b7a; width: 12px; flex: none; }
  .head.open::before { content: "\\25BE"; color: #0073bb; }
  .head .when, .head .step { color: #5f6b7a; }
  .head .step { width: 28px; flex: none; }
  .head .id { width: 96px; flex: none; }
  .head .name { flex: 1; min-width: 0; white-space: pre-wrap; }
  .head .miss { color: #d13212; }
  .head .cost { width: 72px; flex: none; text-align: right; color: #5f6b7a; }
  .kids { margin: 0 0 0 22px; padding: 0 0 0 8px; border-left: 1px solid #d5dbdb; background: #fafafa; }
  .overview { padding: 4px 8px 8px; }
  .overview h2 { margin: 8px 0 2px; font: 600 12px/1.3 ui-monospace, monospace; color: #0073bb; }
  table.fields { width: 100%; border-collapse: collapse; }
  table.fields th { width: 140px; text-align: left; font-weight: 400; color: #5f6b7a;
                    padding: 2px 12px 2px 0; vertical-align: top; }
  table.fields td { padding: 2px 0; vertical-align: top; white-space: pre-wrap; color: #16191f; }
  pre { white-space: pre-wrap; background: #fff; border: 1px solid #d5dbdb;
        margin: 4px 0; padding: 6px 8px; font: inherit; }
</style></head><body>
<div class="bar"><h1>Log events</h1><p class="meta">__DB__</p></div>
<div class="cols"><span class="when">timestamp</span><span>event</span></div>
__LIST__
<script>
function toggle(head) {
  var kids = head.nextElementSibling;
  if (kids.childElementCount) {
    kids.replaceChildren();
    head.classList.remove("open");
    return;
  }
  head.classList.add("open");
  htmx.ajax("GET", kids.dataset.url, {target: kids, swap: "innerHTML"});
}
</script>
</body></html>
"""


def esc(value) -> str:
    return escape("" if value is None else str(value), quote=True)


def pretty(value) -> str:
    return esc(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def node(label: str, url: str, html: bool = False) -> str:
    shown = label if html else esc(label)
    return (
        '<div class="node">'
        f'<button type="button" class="head" onclick="toggle(this)">{shown}</button>'
        f'<div class="kids" data-url="{esc(url)}"></div>'
        "</div>"
    )


def table(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>" for label, value in rows
    )
    return f'<table class="fields">{body}</table>'


def leaf(value) -> str:
    return f"<pre>{pretty(value)}</pre>"


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def chats() -> list[dict]:
    if not DB.exists():
        return []
    db = connect()
    try:
        rows = []
        for row in db.execute(
            "SELECT chat_id, created_timestamp, prompt_name, total_cost, variables_json "
            "FROM chats ORDER BY created_timestamp"
        ):
            item = dict(row)
            variables = json.loads(item.pop("variables_json") or "{}")
            item["question"] = variables.get("question") or ""
            item["week"] = variables.get("week") or ""
            rows.append(item)
        return rows
    finally:
        db.close()


def load(chat_id: str):
    if not DB.exists():
        return None
    db = connect()
    try:
        row = db.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,)).fetchone()
        if row is None:
            return None
        costs = [dict(item) for item in db.execute(
            "SELECT * FROM cost_tracking WHERE chat_id = ? ORDER BY msg_no, round_trip",
            (chat_id,),
        )]
    finally:
        db.close()
    chat = dict(row)
    chat["messages"] = json.loads(chat.pop("messages_json") or "[]")
    chat["state"] = json.loads(chat.pop("vm_state_json") or "{}")
    chat["variables"] = json.loads(chat.pop("variables_json") or "{}")
    chat["statements"] = json.loads(chat.pop("statements_json") or "[]")
    chat["costs"] = costs
    return chat


def text_of(message) -> str:
    parts = []
    for part in message.get("content") or []:
        if part.get("type") == "text" and part.get("text"):
            parts.append(part["text"])
    return "\n".join(parts)


def answer_lines(part) -> list[str]:
    lines = []
    answers = part.get("answers") or {}
    if not answers:
        return ["(no answers)"]
    for name, answer in answers.items():
        if isinstance(answer, dict):
            lines.append(
                f"{name} = {answer.get('value')}  confidence {answer.get('confidence')}"
            )
        else:
            lines.append(f"{name} = {answer}")
    return lines


def lookup(variables: dict, name: str):
    if name.startswith("VM."):
        return None
    path = name
    if name == "$" or name.startswith("$."):
        path = "_prompt" + name[1:]
    elif name == "?" or name.startswith("?."):
        path = "_prompt.question" + name[1:]
    elif name == "#" or name.startswith("#."):
        path = "_prompt.guard" + name[1:]
    node_value = variables
    for key in path.split("."):
        if not isinstance(node_value, dict) or key not in node_value:
            return None
        node_value = node_value[key]
    if isinstance(node_value, (dict, list)):
        return None
    return "" if node_value is None else str(node_value)


def substitute(text: str, variables: dict) -> str:
    prefix, postfix = "<<", ">>"
    for _ in range(20):
        if postfix not in text:
            break
        front, back = text.split(postfix, 1)
        begin = front.rfind(prefix)
        if begin < 0:
            break
        value = lookup(variables, front[begin + len(prefix):])
        if value is None:
            break
        text = front[:begin] + value + back
    return text


def sqlite_path(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise SystemExit(f"keprompt-chats reads a sqlite database, not {url}")
    return Path(url[len(prefix):])


def chats_db() -> Path:
    from keprompt.config import Config
    return sqlite_path(Config().get_database_url())


def sub_open_path(source: str) -> str:
    """The file a `.sub` statement opens, including the `prompts/` default for a bare name."""
    text = source.strip()
    if text.startswith("guard="):
        _, _, text = text.partition(" ")
        text = text.strip()
    return sub_path(text)


def workspace_text(path: str):
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / path
    if candidate.is_file():
        return candidate.read_text()
    return None


def attached(chat, statement) -> list[dict]:
    number = statement.get("msg_no")
    found = []
    for message in chat["messages"]:
        role = message.get("role")
        stmt = message.get("stmt_no")
        if role in ("ldm", "guard") and stmt == number:
            found.append(message)
        elif role not in ("ldm", "guard") and stmt == number + 1:
            found.append(message)
    return found


def ldm_part(chat, statement):
    for message in attached(chat, statement):
        for part in message.get("content") or []:
            if part.get("type") == "ldm":
                return part
    return None


def system_texts(chat) -> list[str]:
    texts = []
    for message in chat["messages"]:
        if message.get("role") != "system":
            continue
        for part in message.get("content") or []:
            if part.get("type") == "text":
                texts.append(part.get("text") or "")
    return texts


def one_line(text: str, limit: int = 160) -> str:
    flat = " ".join((text or "").split())
    if len(flat) <= limit:
        return flat
    return flat[:limit] + "…"


def exec_events(chat, statement) -> list[dict]:
    """The model calls and routine results inside one .exec, in the order they ran."""
    costs = calls_for(chat, statement.get("msg_no"))
    names = {}
    events = []
    assistant_n = 0
    for message in attached(chat, statement):
        role = message.get("role")
        parts = message.get("content") or []
        if role == "assistant":
            cost = costs[assistant_n] if assistant_n < len(costs) else None
            assistant_n += 1
            cost_rows = []
            if cost:
                cost_rows.append((
                    "call",
                    f"{cost.get('model')}  round {cost.get('round_trip')}  "
                    f"in {cost.get('tokens_in')} out {cost.get('tokens_out')}  "
                    f"${cost.get('estimated_costs')}",
                ))
            tool_parts = [part for part in parts if part.get("type") == "tool"]
            if tool_parts:
                for part in tool_parts:
                    arguments = part.get("arguments")
                    args_text = (
                        arguments if isinstance(arguments, str)
                        else json.dumps(arguments, ensure_ascii=False, default=str)
                    )
                    names[part.get("id")] = part.get("name") or ""
                    events.append({
                        "kind": "call",
                        "line": f"{part.get('name')} {one_line(args_text)}",
                        "miss": False,
                        "rows": cost_rows,
                        "blocks": [("arguments", args_text)],
                    })
                    cost_rows = []
            else:
                reply = "\n".join(
                    part.get("text") or "" for part in parts if part.get("type") == "text"
                ).strip()
                events.append({
                    "kind": "llm",
                    "line": one_line(reply) or "(no text)",
                    "miss": False,
                    "rows": cost_rows,
                    "blocks": [("reply", reply or "(no reply)")],
                })
        elif role == "tool":
            for part in parts:
                if part.get("type") != "tool_result":
                    continue
                body = part.get("content") or ""
                name = names.get(part.get("tool_use_id")) or "result"
                first = body.splitlines()[0] if body.splitlines() else ""
                events.append({
                    "kind": "result",
                    "line": f"{name}  {one_line(body) or '(empty)'}",
                    "miss": first.lower().startswith(("error", "rejected")),
                    "rows": [("tool_use_id", part.get("tool_use_id") or "")],
                    "blocks": [("returned", body or "(empty)")],
                })
    return events


def narrate(chat) -> list[dict]:
    """One entry per statement, in the order the program ran."""
    variables = chat["variables"]
    texts = system_texts(chat)
    cursor = 0
    granted = chat["state"].get("allowed_functions") or []
    steps = []
    for index, statement in enumerate(chat["statements"]):
        keyword = statement.get("keyword") or ""
        source = statement.get("value") or ""
        line = source.strip()
        miss = False
        rows = [("source", source)]
        blocks = []
        if keyword == ".prompt":
            line = f"{chat.get('prompt_name')} {chat.get('prompt_version')}  {chat['state'].get('model_name')}"
        elif keyword == ".question":
            line = " ".join(source.split())
            name = source.split()[0] if source.split() else ""
            question = ((variables.get("_prompt") or {}).get("question") or {}).get(name) or {}
            if isinstance(question, dict):
                for key, branch in question.items():
                    if isinstance(branch, dict) and "_definition" in branch:
                        definition = branch["_definition"]
                        blocks.append((key, json.dumps(definition, indent=2, ensure_ascii=False)))
        elif keyword == ".evaluate":
            part = ldm_part(chat, statement)
            if part:
                line = "   ".join(answer_lines(part))
                rows.append(("state", part.get("state") or ""))
                rows.append(("model", part.get("model") or ""))
                for name, answer in (part.get("answers") or {}).items():
                    if isinstance(answer, dict):
                        rows.append((name, f"{answer.get('value')}  confidence {answer.get('confidence')}"))
                        if answer.get("probabilities"):
                            rows.append(("probabilities", json.dumps(answer["probabilities"], ensure_ascii=False)))
            else:
                line, miss = "no answer stored", True
        elif keyword == ".print":
            line = substitute(source, variables)
            rows.append(("printed", line))
        elif keyword in (".system", ".include", ".sub"):
            path = substitute(source, variables).strip()
            lookup = sub_open_path(path) if keyword == ".sub" else path
            file_text = workspace_text(lookup) if keyword in (".include", ".sub") else None
            take = cursor < len(texts) and (
                keyword != ".sub" or file_text is None or ".system" in file_text
            )
            added = texts[cursor] if take else ""
            if take:
                cursor += 1
            if keyword == ".system":
                flat = " ".join(added.split())
                line = flat[:110] + ("…" if len(flat) > 110 else "")
                blocks.append(("added", added))
            elif keyword == ".include":
                line = path
                blocks.append(("file", file_text if file_text is not None else added))
            else:
                declared = ""
                if file_text:
                    for file_line in file_text.splitlines():
                        if file_line.startswith(".functions"):
                            declared = file_line[len(".functions"):].strip()
                line = path + (f"  functions {declared}" if declared else "")
                rows.append(("functions", declared or "(none declared in the file)"))
                blocks.append(("file", file_text or "(file not on disk)"))
                if added:
                    blocks.append(("added", added))
        elif keyword == ".user":
            line = substitute(source, variables)
            for message in attached(chat, statement):
                text = text_of(message)
                if text:
                    line = text
            blocks.append(("said", line))
        elif keyword == ".exec":
            events = exec_events(chat, statement)
            grant = ", ".join(granted) if granted else "(none)"
            rows.append(("granted", grant))
            called = [event["line"] for event in events if event["kind"] == "call"]
            if called:
                line = f"granted {grant}. " + "  ".join(called)
            else:
                line = f"granted {grant}. no function called"
                miss = bool(granted)
            if any(event["miss"] for event in events):
                miss = True
            if not called:
                for event in events:
                    if event["kind"] == "llm":
                        event["miss"] = bool(granted)
        elif keyword == ".exit":
            line = "stopped"
        else:
            line = substitute(source, variables)
        if keyword != ".exec":
            for cost in calls_for(chat, statement.get("msg_no")):
                rows.append((
                    "call",
                    f"{cost.get('model')}  in {cost.get('tokens_in')} out {cost.get('tokens_out')}  "
                    f"${cost.get('estimated_costs')}",
                ))
        steps.append({
            "index": index,
            "keyword": keyword,
            "line": line,
            "miss": miss,
            "rows": rows,
            "blocks": blocks,
            "events": events if keyword == ".exec" else [],
        })
    return steps


def trace(chat) -> str:
    variables = chat["variables"]
    base = f"/open/{chat['chat_id']}"
    body = (
        '<div class="overview"><h2>@parameters</h2>'
        + table([
            ("question", variables.get("question") or ""),
            ("week", variables.get("week") or ""),
            ("channel", variables.get("channel") or ""),
            ("model", chat["state"].get("model_name") or ""),
        ])
        + "</div>"
    )
    for step in narrate(chat):
        result = f'<span class="miss">{esc(step["line"])}</span>' if step["miss"] else esc(step["line"])
        body += node(
            f'<span class="step">{step["index"]:02d}</span>'
            f'<span class="id">{esc(step["keyword"])}</span>'
            f'<span class="name">{result}</span>',
            f"{base}/step/{step['index']}",
            html=True,
        )
    body += node("record", base + "/record")
    return body


def step_page(chat, index: int) -> str:
    step = narrate(chat)[index]
    if step["keyword"] == ".exec":
        return exec_page(chat, step)
    body = table(step["rows"])
    for title, text in step["blocks"]:
        body += f"<h2>@{esc(title)}</h2><pre>{esc(text)}</pre>"
    return body


def exec_page(chat, step) -> str:
    body = table(step["rows"])
    base = f"/open/{chat['chat_id']}/step/{step['index']}"
    for number, event in enumerate(step["events"]):
        shown = f'<span class="miss">{esc(event["line"])}</span>' if event["miss"] else esc(event["line"])
        body += node(
            f'<span class="step">{number:02d}</span>'
            f'<span class="id">{esc(event["kind"])}</span>'
            f'<span class="name">{shown}</span>',
            f"{base}/event/{number}",
            html=True,
        )
    if not step["events"]:
        body += "<p>no calls stored</p>"
    return body


def event_page(chat, index: int, number: int) -> str:
    event = narrate(chat)[index]["events"][number]
    body = table(event["rows"])
    for title, text in event["blocks"]:
        body += f"<h2>@{esc(title)}</h2><pre>{esc(text)}</pre>"
    return body


def columns_of(chat) -> dict:
    skip = {"messages", "state", "variables", "statements", "costs"}
    return {key: value for key, value in chat.items() if key not in skip}


def calls_for(chat, msg_no) -> list[dict]:
    return [cost for cost in chat["costs"] if cost.get("msg_no") == msg_no]


def render_record(chat, rest: list[str]) -> str:
    base = f"/open/{chat['chat_id']}/record"
    if not rest:
        return (
            node("columns", base + "/columns")
            + node("vm state", base + "/vm_state")
            + node("variables", base + "/variables")
        )
    if rest[0] == "columns":
        return leaf(columns_of(chat))
    if rest[0] == "vm_state":
        return leaf(chat["state"])
    if rest[0] == "variables":
        return leaf(chat["variables"])
    return "<p>unknown</p>"


def render(path: str) -> tuple[str, int]:
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2 or parts[0] != "open":
        return "<p>not found</p>", 404
    chat = load(parts[1])
    if chat is None:
        return f"<p>No chat {esc(parts[1])}</p>", 404
    rest = parts[2:]
    try:
        if not rest:
            return trace(chat), 200
        if rest[0] == "step" and len(rest) >= 4 and rest[2] == "event":
            return event_page(chat, int(rest[1]), int(rest[3])), 200
        if rest[0] == "step":
            return step_page(chat, int(rest[1])), 200
        if rest[0] == "record":
            return render_record(chat, rest[1:]), 200
    except (IndexError, ValueError):
        return "<p>not found</p>", 404
    return "<p>not found</p>", 404


def page() -> str:
    if not DB.exists():
        listing = f"<p>database {esc(DB)} does not exist</p>"
    else:
        listing = "".join(
            node(
                f'<span class="when">{esc(row["created_timestamp"])}</span>'
                f'<span class="id">{esc(row["chat_id"])}</span>'
                f'<span class="name">{esc(row["question"])}  week {esc(row["week"])}</span>'
                f'<span class="cost">${row["total_cost"] or 0:.4f}</span>',
                f"/open/{row['chat_id']}",
                html=True,
            )
            for row in chats()
        ) or "<p>no chats</p>"
    return PAGE.replace("__DB__", esc(DB)).replace("__LIST__", listing)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body, code = page(), 200
        elif path.startswith("/open/"):
            body, code = render(path)
        else:
            body, code = "not found", 404
        data = body.encode()
        self.send_response(code)
        kind = "text/html; charset=utf-8" if path == "/" or path.startswith("/open/") else "text/plain; charset=utf-8"
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        return


def main(argv=None):
    global DB, PORT
    parser = argparse.ArgumentParser(
        prog="keprompt-chats",
        description="Show the chats database in a browser.",
    )
    parser.add_argument("--port", type=int, default=8765, help="port to listen on (default 8765)")
    args = parser.parse_args(argv)
    PORT = args.port
    DB = chats_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}/  {DB.resolve()}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
