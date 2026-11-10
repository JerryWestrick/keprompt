"""A prompt calls keprompt. The answer comes back. The child's work stays in the child."""

import json
import os
import sqlite3
import subprocess
from pathlib import Path

from conftest import note

ROOT = Path("/home/jerry/keprompt/test")
KEPROMPT = Path("/home/jerry/keprompt/.venv/bin/python")
ENV = dict(os.environ)
ENV["PATH"] = f"/home/jerry/keprompt/.venv/bin:{ENV.get('PATH', '')}"


def exec_cmd(command: str) -> dict:
    out = subprocess.run(
        command, shell=True, cwd=ROOT, text=True, capture_output=True, timeout=180, env=ENV,
    ).stdout
    start = out.find("{")
    assert start != -1, out[-500:]
    envelope = json.loads(out[start:])
    assert envelope.get("success") is True, envelope.get("error")
    note(chat_ids=envelope["chat_id"])
    return envelope


def chat_row(chat_id: str) -> sqlite3.Row:
    db = sqlite3.connect(ROOT / "prompts/chats.db")
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,)).fetchone()
    db.close()
    return row


def tool_calls(messages_json: str) -> list[dict]:
    calls = []
    for message in json.loads(messages_json):
        for part in message.get("content") or []:
            if part.get("type") == "tool" and part.get("name"):
                calls.append({"name": part["name"], "arguments": part.get("arguments")})
    return calls


def tool_results(messages_json: str) -> list[str]:
    results = []
    for message in json.loads(messages_json):
        for part in message.get("content") or []:
            if part.get("type") == "tool_result":
                results.append(part.get("content") or "")
    return results


def test_keprompt_call_returns_the_answer_without_the_child_context():
    envelope = exec_cmd(f"{KEPROMPT} -m keprompt chats create call-date --json")
    parent = chat_row(envelope["chat_id"])
    variables = json.loads(parent["variables_json"])
    answer = json.loads(variables["answer"])
    assert answer.get("success") is True, answer.get("error")

    child = chat_row(answer["chat_id"])
    child_calls = tool_calls(child["messages_json"])
    assert [call["name"] for call in child_calls] == ["execcmd"]
    result = tool_results(child["messages_json"])[0].strip()
    assert result
    assert result in (answer.get("ai_response") or "")

    parent_calls = tool_calls(parent["messages_json"])
    assert parent_calls == []
    assert result not in (parent["messages_json"] or "")
