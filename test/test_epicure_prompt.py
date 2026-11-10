"""One week through the copied Epicure prompt, against the dev database."""

import json
import os
import sqlite3
import subprocess
from datetime import date
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from conftest import note

EPICURE = Path("/home/jerry/Epicure")
ROOT = Path("/home/jerry/keprompt/test")
KEPROMPT = Path("/home/jerry/keprompt/.venv/bin/python")
PROMPT = ROOT / "prompts/epicure.prompt"
ENV = dict(os.environ)
ENV["PATH"] = f"{EPICURE}/.venv/bin:{ENV.get('PATH', '')}"
CLIENT = "ZZTEST KEPROMPT"
CHATS: list[str] = []


def exec_cmd(command: str) -> None:
    out = subprocess.run(
        command, shell=True, cwd=ROOT, text=True, capture_output=True, timeout=180, env=ENV,
    ).stdout
    start = out.find("{")
    assert start != -1, out[-500:]
    envelope = json.loads(out[start:])
    assert envelope.get("success") is True, envelope.get("error")
    CHATS.append(envelope["chat_id"])
    note(chat_ids=envelope["chat_id"])


def tool_calls(chat_ids: list[str]) -> list[dict]:
    db = sqlite3.connect(ROOT / "prompts/chats.db")
    calls = []
    for chat_id in chat_ids:
        row = db.execute(
            "SELECT messages_json FROM chats WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        if row is None:
            continue
        for message in json.loads(row[0]):
            for part in message.get("content") or []:
                if part.get("type") == "tool" and part.get("name"):
                    calls.append({"name": part["name"], "arguments": part.get("arguments")})
    db.close()
    return calls


def test_epicure_prompt_runs_a_week():
    week = "2026-10-29"
    assert date(2026, 10, 29).weekday() == 3
    conn = psycopg.connect("dbname=epicure", row_factory=dict_row)
    saved = conn.execute(
        "SELECT value FROM config WHERE key = %s", ("current_week",)
    ).fetchone()["value"]
    assert week != saved
    conn.execute(
        "DELETE FROM order_items WHERE remision IN (SELECT remision FROM orders WHERE cliente = %s)",
        (CLIENT,),
    )
    conn.execute("DELETE FROM orders WHERE cliente = %s", (CLIENT,))
    conn.execute("DELETE FROM clients WHERE nombre = %s", (CLIENT,))
    conn.commit()

    CHATS.clear()
    try:
        exec_cmd(
            f"{KEPROMPT} -m keprompt chats create {PROMPT} --json "
            f"--set week {saved} --set question 'Cambia la semana actual al jueves {week}.'"
        )
        assert conn.execute(
            "SELECT value FROM config WHERE key = %s", ("current_week",)
        ).fetchone()["value"] == week

        exec_cmd(
            f"{KEPROMPT} -m keprompt chats create {PROMPT} --json "
            f"--set week {week} --set question 'Nuevo cliente ZZTEST KEPROMPT, tipo chef, pago efectivo, envío 50.'"
        )
        assert conn.execute(
            "SELECT nombre FROM clients WHERE nombre = %s", (CLIENT,)
        ).fetchall() == [{"nombre": CLIENT}]

        exec_cmd(
            f"{KEPROMPT} -m keprompt chats create {PROMPT} --json "
            f"--set week {week} --set question 'Pedido nuevo #1 ZZTEST KEPROMPT\n2 violas\n1 tortillas harina chipotle'"
        )
        exec_cmd(
            f"{KEPROMPT} -m keprompt chats create {PROMPT} --json "
            f"--set week {week} --set question 'En el pedido #1 de ZZTEST KEPROMPT cambia las violas a 5 y el envío a 80.'"
        )
        exec_cmd(
            f"{KEPROMPT} -m keprompt chats create {PROMPT} --json "
            f"--set week {week} --set question 'Pedido nuevo #2 ZZTEST KEPROMPT\n1 violas'"
        )
        exec_cmd(
            f"{KEPROMPT} -m keprompt chats create {PROMPT} --json "
            f"--set week {week} --set question 'Cancela el pedido #2 de ZZTEST KEPROMPT.'"
        )
        exec_cmd(
            f"{KEPROMPT} -m keprompt chats create {PROMPT} --json "
            f"--set week {week} "
            f"--set question 'Muestre todos los ordenes del cliente ZZTEST KEPROMPT, con su remisión, el producto y la cantidad.'"
        )

        orders = conn.execute(
            "SELECT o.orden_num, o.envio, p.nombre AS producto, oi.cantidad "
            "FROM orders o "
            "JOIN order_items oi ON oi.remision = o.remision "
            "JOIN products p ON p.id = oi.product_id "
            "WHERE o.cliente = %s "
            "ORDER BY p.nombre",
            (CLIENT,),
        ).fetchall()
        assert len({row["orden_num"] for row in orders}) == 1
        by_product = {row["producto"]: row for row in orders}
        assert by_product["VIOLAS"]["cantidad"] == 5
        assert by_product["TORTILLAS HARINA CHIPOTLE"]["cantidad"] == 1
        assert all(row["envio"] == 80 for row in orders)
        names = [call["name"] for call in tool_calls(CHATS)]
        assert "select" in names
        assert "set_week" in names and "new_client" in names and "new_order" in names
        assert "cancel_order" in names
    finally:
        conn.execute(
            "DELETE FROM order_items WHERE remision IN (SELECT remision FROM orders WHERE cliente = %s)",
            (CLIENT,),
        )
        conn.execute("DELETE FROM orders WHERE cliente = %s", (CLIENT,))
        conn.execute("DELETE FROM clients WHERE nombre = %s", (CLIENT,))
        conn.execute(
            "INSERT INTO config (key, value) VALUES (%s, %s) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("current_week", saved),
        )
        conn.commit()
        conn.close()
