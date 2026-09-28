#!/usr/bin/env python3
"""Upgrade a KePrompt SQLite database to a requested KePrompt version."""

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from typing import Callable

from keprompt.version import __version__

PRE_INFO_VERSION = "2.15.0"

COST_TRACKING_DDL = """
CREATE TABLE "cost_tracking" (
  "chat_id" VARCHAR(8) NOT NULL, "msg_no" INTEGER NOT NULL,
  "round_trip" INTEGER NOT NULL, "call_id" VARCHAR(50) NOT NULL,
  "timestamp" DATETIME NOT NULL, "tokens_in" INTEGER NOT NULL,
  "tokens_out" INTEGER NOT NULL, "cost_in" DECIMAL(10, 6) NOT NULL,
  "cost_out" DECIMAL(10, 6) NOT NULL, "estimated_costs" DECIMAL(10, 6) NOT NULL,
  "elapsed_time" DECIMAL(8, 3) NOT NULL, "tool_time" DECIMAL(8, 3) NOT NULL,
  "model" VARCHAR(100) NOT NULL, "provider" VARCHAR(50) NOT NULL,
  "success" INTEGER NOT NULL, "error_message" TEXT,
  "temperature" DECIMAL(3, 2), "max_tokens" INTEGER, "context_length" INTEGER,
  "prompt_semantic_name" VARCHAR(255), "prompt_version_tracking" VARCHAR(50),
  "expected_params" TEXT, "execution_mode" VARCHAR(20) NOT NULL,
  "parameters" TEXT, "environment" VARCHAR(20),
  PRIMARY KEY ("chat_id", "msg_no", "round_trip"))
"""

COST_TRACKING_INDEXES = (
    'CREATE INDEX IF NOT EXISTS "costtracking_timestamp" ON "cost_tracking" ("timestamp")',
    'CREATE INDEX IF NOT EXISTS "costtracking_model" ON "cost_tracking" ("model")',
    'CREATE INDEX IF NOT EXISTS "costtracking_chat_id" ON "cost_tracking" ("chat_id")',
)
INFO_DDL = """
CREATE TABLE IF NOT EXISTS "info" (
  "id" INTEGER NOT NULL PRIMARY KEY,
  "version" VARCHAR(20) NOT NULL,
  "updated" DATETIME NOT NULL)
"""
CHATS_COLUMNS = (
    ("total_round_trips", "INTEGER NOT NULL DEFAULT 0"),
    ("total_api_time", "DECIMAL(10, 3) NOT NULL DEFAULT 0"),
    ("total_tool_time", "DECIMAL(10, 3) NOT NULL DEFAULT 0"),
)
CARRIED_COST_COLUMNS = (
    "chat_id", "msg_no", "call_id", "timestamp", "tokens_in", "tokens_out",
    "cost_in", "cost_out", "estimated_costs", "elapsed_time", "model", "provider",
    "success", "error_message", "temperature", "max_tokens", "context_length",
    "prompt_semantic_name", "prompt_version_tracking", "expected_params",
    "execution_mode", "parameters", "environment",
)


class MigrationError(RuntimeError):
    """Raised when no safe migration path exists."""


def normalize_version(version: str) -> str:
    parts = str(version).strip().split(".")
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        parts.append("0")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise MigrationError(f"invalid database version: {version!r}")
    return ".".join(str(int(part)) for part in parts)


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')]


def get_stored_version(conn: sqlite3.Connection) -> str:
    if "info" not in _tables(conn):
        return PRE_INFO_VERSION
    row = conn.execute("SELECT version FROM info ORDER BY id DESC LIMIT 1").fetchone()
    return str(row[0]).strip() if row else PRE_INFO_VERSION


def get_database_version(conn: sqlite3.Connection) -> str:
    return normalize_version(get_stored_version(conn))


def _stamp(conn: sqlite3.Connection, version: str) -> None:
    conn.execute(INFO_DDL)
    conn.execute("DELETE FROM info")
    conn.execute(
        "INSERT INTO info (version, updated) VALUES (?, ?)",
        (version, datetime.now().isoformat(sep=" ", timespec="seconds")),
    )


def migrate_2_15_0_to_2_16_0(conn: sqlite3.Connection, log=print) -> None:
    """Re-cut cost accounting at one row per billed API round trip."""
    tables = _tables(conn)
    if "chats" in tables:
        existing = set(_columns(conn, "chats"))
        for name, ddl in CHATS_COLUMNS:
            if name not in existing:
                conn.execute(f'ALTER TABLE chats ADD COLUMN "{name}" {ddl}')

    if "cost_tracking" in tables and "round_trip" not in _columns(conn, "cost_tracking"):
        carried = [name for name in CARRIED_COST_COLUMNS
                   if name in _columns(conn, "cost_tracking")]
        quoted = ", ".join(f'"{name}"' for name in carried)
        rows = conn.execute("SELECT count(*) FROM cost_tracking").fetchone()[0]
        conn.execute("ALTER TABLE cost_tracking RENAME TO cost_tracking_legacy")
        for (index,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name='cost_tracking_legacy' AND sql IS NOT NULL"
        ).fetchall():
            conn.execute(f'DROP INDEX IF EXISTS "{index}"')
        conn.execute(COST_TRACKING_DDL)
        for statement in COST_TRACKING_INDEXES:
            conn.execute(statement)
        conn.execute(
            f"INSERT INTO cost_tracking ({quoted}, round_trip, tool_time) "
            f"SELECT {quoted}, 1, 0 FROM cost_tracking_legacy"
        )
        conn.execute("DROP TABLE cost_tracking_legacy")
        log(f"  cost_tracking: preserved {rows} row(s) as round_trip = 1")

    if "server_registry" in tables:
        conn.execute("DROP TABLE server_registry")


def migrate_2_16_0_to_2_16_1(conn: sqlite3.Connection, log=print) -> None:
    """No database changes in KePrompt 2.16.1."""


def migrate_2_16_1_to_2_16_2(conn: sqlite3.Connection, log=print) -> None:
    """No database changes in KePrompt 2.16.2."""


def migrate_2_16_2_to_3_0_0(conn: sqlite3.Connection, log=print) -> None:
    """No database changes in KePrompt 3.0.0."""


def migrate_3_0_0_to_3_0_1(conn: sqlite3.Connection, log=print) -> None:
    """No database changes in KePrompt 3.0.1."""


def migrate_3_0_1_to_3_1_0(conn: sqlite3.Connection, log=print) -> None:
    """No database changes in KePrompt 3.1.0."""


def migrate_3_1_0_to_4_0_0(conn: sqlite3.Connection, log=print) -> None:
    """No database changes in KePrompt 4.0.0; multi-line quotes are a parser feature."""


def migrate_4_0_0_to_4_1_0(conn: sqlite3.Connection, log=print) -> None:
    """No schema change. An LDM call is an execute: it is billed in `cost_tracking` and its content
    is an LDM message in the chat's `messages_json`, exactly like an LLM call."""


def migrate_4_1_0_to_4_2_0(conn: sqlite3.Connection, log=print) -> None:
    """No schema change."""


def _rename_set_model_keys(value):
    """In stored memory, each question set's `_model` (the model that answered) becomes
    `_provider_selected_model`, then `_ldm_model` (the model asked for) becomes `_model`."""
    if isinstance(value, dict):
        root = value.get("_prompt")
        question = root.get("question") if isinstance(root, dict) else None
        if isinstance(question, dict):
            for question_set in question.values():
                if not isinstance(question_set, dict):
                    continue
                if "_model" in question_set:
                    question_set["_provider_selected_model"] = question_set.pop("_model")
                if "_ldm_model" in question_set:
                    question_set["_model"] = question_set.pop("_ldm_model")
        for child in value.values():
            _rename_set_model_keys(child)
    elif isinstance(value, list):
        for child in value:
            _rename_set_model_keys(child)


def _rename_ldm_part_field(value):
    """In stored messages, an LDM part's `model_served` becomes `provider_selected_model`."""
    if isinstance(value, dict):
        if "model_served" in value:
            value["provider_selected_model"] = value.pop("model_served")
        for child in value.values():
            _rename_ldm_part_field(child)
    elif isinstance(value, list):
        for child in value:
            _rename_ldm_part_field(child)


def migrate_4_2_0_to_4_3_0(conn: sqlite3.Connection, log=print) -> None:
    """The model that answered is `provider_selected_model` everywhere: a `cost_tracking` column,
    the LDM part's field (was `model_served`), and `_provider_selected_model` in a question set
    (was `_model`, whose name now holds the set's model, was `_ldm_model`)."""
    tables = _tables(conn)
    if "cost_tracking" in tables and "provider_selected_model" not in _columns(conn, "cost_tracking"):
        conn.execute('ALTER TABLE cost_tracking ADD COLUMN "provider_selected_model" VARCHAR(100)')

    if "chats" not in tables:
        return
    columns = set(_columns(conn, "chats"))
    renames = [(column, fix) for column, fix in (("messages_json", _rename_ldm_part_field),
                                                 ("vm_state_json", _rename_set_model_keys),
                                                 ("variables_json", _rename_set_model_keys))
               if column in columns]
    changed = 0
    for chat_id, *texts in conn.execute(
            f'SELECT chat_id, {", ".join(column for column, _ in renames)} FROM chats').fetchall():
        updates = {}
        for (column, fix), text in zip(renames, texts):
            if not text:
                continue
            data = json.loads(text)
            fix(data)
            if data != json.loads(text):
                updates[column] = json.dumps(data)
        if updates:
            assignments = ", ".join(f'"{column}" = ?' for column in updates)
            conn.execute(f'UPDATE chats SET {assignments} WHERE chat_id = ?',
                         (*updates.values(), chat_id))
            changed += 1
    log(f"  chats: renamed stored model keys in {changed} chat(s)")


def migrate_4_3_0_to_4_4_0(conn: sqlite3.Connection, log=print) -> None:
    """No schema change. A guard execution is a `guard` message in `messages_json` plus its
    `cost_tracking` row, like any other LDM call."""


Migration = tuple[str, Callable[[sqlite3.Connection, Callable], None]]
MIGRATIONS: dict[str, Migration] = {
    "2.15.0": ("2.16.0", migrate_2_15_0_to_2_16_0),
    "2.16.0": ("2.16.1", migrate_2_16_0_to_2_16_1),
    "2.16.1": ("2.16.2", migrate_2_16_1_to_2_16_2),
    "2.16.2": ("3.0.0", migrate_2_16_2_to_3_0_0),
    "3.0.0": ("3.0.1", migrate_3_0_0_to_3_0_1),
    "3.0.1": ("3.1.0", migrate_3_0_1_to_3_1_0),
    "3.1.0": ("4.0.0", migrate_3_1_0_to_4_0_0),
    "4.0.0": ("4.1.0", migrate_4_0_0_to_4_1_0),
    "4.1.0": ("4.2.0", migrate_4_1_0_to_4_2_0),
    "4.2.0": ("4.3.0", migrate_4_2_0_to_4_3_0),
    "4.3.0": ("4.4.0", migrate_4_3_0_to_4_4_0),
}


def migration_path(current: str, target: str) -> list[Migration]:
    current = normalize_version(current)
    target = normalize_version(target)
    path: list[Migration] = []
    seen: set[str] = set()
    while current != target:
        if current in seen:
            raise MigrationError(f"migration loop detected at {current}")
        seen.add(current)
        step = MIGRATIONS.get(current)
        if step is None:
            raise MigrationError(f"no migration path from {current} to {target}")
        next_version, function = step
        if tuple(map(int, next_version.split("."))) > tuple(map(int, target.split("."))):
            raise MigrationError(f"migration from {current} overshoots target {target}")
        path.append((next_version, function))
        current = next_version
    return path


def migrate(db_path: str, target_version: str = __version__, backup: bool = True,
            log=print) -> bool:
    db_path = str(db_path)
    conn = sqlite3.connect(db_path)
    try:
        stored = get_stored_version(conn)
        current = get_database_version(conn)
    finally:
        conn.close()
    target = normalize_version(target_version)
    path = migration_path(current, target)
    if not path:
        if stored == target:
            return False
        conn = sqlite3.connect(db_path)
        try:
            with conn:
                _stamp(conn, target)
        finally:
            conn.close()
        return True
    if backup:
        backup_path = f"{db_path}.bak-{current}"
        shutil.copy2(db_path, backup_path)
        log(f"keprompt: backed up database to {backup_path}")
    conn = sqlite3.connect(db_path)
    try:
        version = current
        for next_version, function in path:
            log(f"keprompt: migrating {db_path}: {version} -> {next_version}")
            with conn:
                function(conn, log)
                _stamp(conn, next_version)
            version = next_version
        if get_database_version(conn) != target:
            raise MigrationError(f"database ended at {version}, expected {target}")
    finally:
        conn.close()
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", nargs="?", default="prompts/chats.db")
    parser.add_argument("--version", default=__version__, dest="target_version")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args(argv)
    try:
        changed = migrate(args.database, args.target_version, not args.no_backup)
    except (MigrationError, sqlite3.Error, OSError) as error:
        print(f"migration failed: {error}", file=sys.stderr)
        return 1
    print("migration complete" if changed else "database already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())