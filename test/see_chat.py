#!/usr/bin/env python3
"""Read a KePrompt chats.db and show each call: what was sent, what came back.

    python3 test/see_chat.py
    http://127.0.0.1:8765/
"""

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DB = Path(__file__).resolve().parent / "prompts" / "chats.db"
HOST = "127.0.0.1"
PORT = 8765


def esc(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def pretty(value) -> str:
    return esc(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def chats():
    db = connect()
    rows = db.execute(
        "SELECT chat_id, created_timestamp, prompt_name, total_cost "
        "FROM chats ORDER BY created_timestamp DESC"
    ).fetchall()
    db.close()
    return rows


def load(chat_id: str):
    db = connect()
    chat = db.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,)).fetchone()
    costs = db.execute(
        "SELECT * FROM cost_tracking WHERE chat_id = ? ORDER BY timestamp, round_trip",
        (chat_id,),
    ).fetchall()
    db.close()
    return chat, costs


def text_of(message) -> str:
    parts = []
    for part in message.get("content") or []:
        if part.get("type") == "text" and part.get("text"):
            parts.append(part["text"])
    return "\n\n".join(parts)


def calls_of(messages):
    """One keprompt invocation per user message. Records before the first user stay with it."""
    calls = []
    current = []
    seen_user = False
    for message in messages:
        if message.get("role") == "user" and seen_user:
            calls.append(current)
            current = [message]
        else:
            if message.get("role") == "user":
                seen_user = True
            current.append(message)
    if current:
        calls.append(current)
    return calls


def panel(title: str, body: str, open_=False) -> str:
    flag = " open" if open_ else ""
    return f"<details{flag}><summary>{esc(title)}</summary><div class='body'>{body}</div></details>"


def record(title: str, value) -> str:
    return panel(title, f"<pre>{pretty(value)}</pre>")


def evaluate_block(message) -> str:
    part = next(p for p in message["content"] if p.get("type") == "ldm")
    answers = part.get("answers") or {}
    kind = ""
    if isinstance(answers, dict) and isinstance(answers.get("kind"), dict):
        kind = str(answers["kind"].get("value") or "")
    sent = {
        "model": part.get("model"),
        "set": part.get("set"),
        "state": part.get("state"),
        "questions": part.get("questions"),
    }
    returned = {
        "answers": answers,
        "provider_selected_model": part.get("provider_selected_model"),
        "usage": part.get("usage"),
    }
    title = "2. .evaluate" + (f" — {kind}" if kind else "")
    body = (
        "<h4>sent</h4><pre>" + pretty(sent) + "</pre>"
        "<h4>returned</h4><pre>" + pretty(returned) + "</pre>"
        + record("stored record", message)
    )
    return panel(title, body)


def llm_block(messages, functions) -> str:
    chunks = [panel(
        "functions defined",
        f"<pre>{esc(', '.join(functions) if functions else '(none)')}</pre>",
    )]
    for message in messages:
        role = message.get("role")
        if role == "system":
            chunks.append(panel(
                "sent to the model — system",
                f"<pre>{esc(text_of(message))}</pre>" + record("stored record", message),
            ))
        elif role == "user":
            chunks.append(panel(
                "sent to the model — user",
                f"<pre>{esc(text_of(message))}</pre>" + record("stored record", message),
            ))
        elif role == "assistant":
            bits = []
            for part in message.get("content") or []:
                if part.get("type") == "tool":
                    bits.append(
                        f"<h4>returned — call {esc(part.get('name'))}</h4>"
                        f"<pre>{pretty(part.get('arguments'))}</pre>"
                    )
                elif part.get("type") == "text":
                    bits.append("<h4>returned — text</h4>" f"<pre>{esc(part.get('text') or '')}</pre>")
            model = message.get("model_name") or ""
            chunks.append(panel(
                f"model returned {model}".strip(),
                "".join(bits) + record("stored record", message),
            ))
        elif role == "tool":
            for part in message.get("content") or []:
                if part.get("type") == "tool_result":
                    chunks.append(panel(
                        "function returned",
                        f"<pre>{esc(part.get('content') or '')}</pre>" + record("stored record", message),
                    ))
    return panel("3. .exec", "".join(chunks) if chunks else "<p>no model call</p>")


def page_chat(chat_id: str) -> str:
    chat, costs = load(chat_id)
    if chat is None:
        return layout(f"<p>No chat {esc(chat_id)}</p>")
    messages = json.loads(chat["messages_json"] or "[]")
    state = json.loads(chat["vm_state_json"] or "{}")
    calls = calls_of(messages)
    blocks = []
    for number, call in enumerate(calls, 1):
        user = next((m for m in call if m.get("role") == "user"), None)
        question = text_of(user) if user else ""
        verb = "chats create" if number == 1 else "chat reply"
        ldm = [m for m in call if m.get("role") == "ldm"]
        rest = [m for m in call if m.get("role") != "ldm"]
        inner = panel("1. keprompt called with", f"<pre>{esc(question)}</pre>")
        if ldm:
            inner += evaluate_block(ldm[0])
        else:
            inner += panel(
                "2. .evaluate",
                "<p>Not executed. A reply adds .user and .exec only.</p>",
            )
        functions = state.get("allowed_functions") or []
        inner += llm_block(rest, functions)
        blocks.append(
            f"<section><h2>{number} of {len(calls)} · {esc(verb)}</h2>{inner}</section>"
        )
    if costs:
        blocks.append(panel(
            "round trips",
            "".join(
                f"<pre>{pretty(dict(row))}</pre>" for row in costs
            ),
        ))
    head = (
        f"<p><a href='/'>chats</a></p>"
        f"<h1>{esc(chat_id)}</h1>"
        f"<p class='meta'>{esc(chat['prompt_name'])} · {esc(chat['created_timestamp'])} · "
        f"model {esc(state.get('model_name') or '')}</p>"
    )
    return layout(head + "".join(blocks))


def page_index() -> str:
    rows = []
    for chat in chats():
        rows.append(
            f"<li><a href='/chat/{esc(chat['chat_id'])}'>{esc(chat['chat_id'])}</a> "
            f"{esc(chat['created_timestamp'])} {esc(chat['prompt_name'] or '')} "
            f"${chat['total_cost'] or 0:.4f}</li>"
        )
    return layout(f"<h1>chats</h1><p class='meta'>{esc(DB)}</p><ul>{''.join(rows)}</ul>")


def layout(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>chat</title>
<style>
body {{ margin: 0; background: #16161a; color: #e8e8e4;
  font: 16px/1.45 ui-sans-serif, sans-serif; }}
main {{ max-width: 920px; margin: 0 auto; padding: 24px 16px 80px; }}
a {{ color: #9ecbff; }}
h1 {{ font-size: 22px; }}
h2 {{ font-size: 18px; margin: 28px 0 8px; }}
h4 {{ margin: 12px 0 4px; font-size: 13px; color: #9a9a94; text-transform: uppercase; }}
.meta {{ color: #9a9a94; }}
details {{ background: #1e1e23; border: 1px solid #2c2c32; border-radius: 8px; margin: 8px 0; }}
summary {{ cursor: pointer; padding: 10px 12px; font-weight: 600; }}
.body {{ padding: 0 12px 12px; }}
pre {{ white-space: pre-wrap; background: #121216; border-radius: 6px; padding: 10px;
  overflow-x: auto; font: 13px/1.4 ui-monospace, monospace; }}
section {{ border-top: 1px solid #2c2c32; padding-top: 8px; }}
</style></head><body><main>
{body}
</main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            html = page_index()
        elif path.startswith("/chat/"):
            html = page_chat(path[len("/chat/"):])
        else:
            self.send_error(404)
            return
        data = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}")


if __name__ == "__main__":
    print(f"http://{HOST}:{PORT}/  ({DB})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
