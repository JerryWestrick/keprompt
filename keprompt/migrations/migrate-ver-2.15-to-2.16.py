#!/usr/bin/env python3
"""Migrate a keprompt database from the 2.15 schema to the 2.16 schema.

2.16 re-cuts cost accounting at the billed unit (DEFECT-001). A `.exec` statement
runs the whole tool-calling loop, which can be dozens of separately billed API
requests; 2.15 recorded one `cost_tracking` row per `.exec`, holding only the last
round trip's tokens next to the whole loop's elapsed time.

What this does:

  chats           + total_round_trips, total_api_time, total_tool_time
  cost_tracking   + round_trip, tool_time
                  primary key (chat_id, msg_no) -> (chat_id, msg_no, round_trip)
  info            created if absent; version set to 2.16

Existing cost rows are preserved verbatim and become round_trip = 1. Their figures
are NOT corrected -- the per-round-trip detail was never recorded and cannot be
recovered from the database. Only calls made after this migration carry true
per-request numbers.

Run standalone:

    python migrate-ver-2.15-to-2.16.py prompts/chats.db
    python migrate-ver-2.15-to-2.16.py prompts/chats.db --no-backup

keprompt also invokes migrate() automatically when it opens a 2.15 database.

The DDL below is written out in full rather than taken from keprompt.database.
A migration has to keep describing the schema as it was at this point in history,
even after the models move on.
"""
import shutil
import sqlite3
import sys
from datetime import datetime

FROM_VERSION = '2.15'
TO_VERSION = '2.16'

COST_TRACKING_DDL = """
CREATE TABLE "cost_tracking" (
  "chat_id" VARCHAR(8) NOT NULL,
  "msg_no" INTEGER NOT NULL,
  "round_trip" INTEGER NOT NULL,
  "call_id" VARCHAR(50) NOT NULL,
  "timestamp" DATETIME NOT NULL,
  "tokens_in" INTEGER NOT NULL,
  "tokens_out" INTEGER NOT NULL,
  "cost_in" DECIMAL(10, 6) NOT NULL,
  "cost_out" DECIMAL(10, 6) NOT NULL,
  "estimated_costs" DECIMAL(10, 6) NOT NULL,
  "elapsed_time" DECIMAL(8, 3) NOT NULL,
  "tool_time" DECIMAL(8, 3) NOT NULL,
  "model" VARCHAR(100) NOT NULL,
  "provider" VARCHAR(50) NOT NULL,
  "success" INTEGER NOT NULL,
  "error_message" TEXT,
  "temperature" DECIMAL(3, 2),
  "max_tokens" INTEGER,
  "context_length" INTEGER,
  "prompt_semantic_name" VARCHAR(255),
  "prompt_version_tracking" VARCHAR(50),
  "expected_params" TEXT,
  "execution_mode" VARCHAR(20) NOT NULL,
  "parameters" TEXT,
  "environment" VARCHAR(20),
  PRIMARY KEY ("chat_id", "msg_no", "round_trip"))
"""

COST_TRACKING_INDEXES = [
    'CREATE INDEX IF NOT EXISTS "costtracking_timestamp" ON "cost_tracking" ("timestamp")',
    'CREATE INDEX IF NOT EXISTS "costtracking_model" ON "cost_tracking" ("model")',
    'CREATE INDEX IF NOT EXISTS "costtracking_chat_id" ON "cost_tracking" ("chat_id")',
]

INFO_DDL = """
CREATE TABLE IF NOT EXISTS "info" (
  "id" INTEGER NOT NULL PRIMARY KEY,
  "version" VARCHAR(20) NOT NULL,
  "updated" DATETIME NOT NULL)
"""

CHATS_COLUMNS = [
    ('total_round_trips', 'INTEGER NOT NULL DEFAULT 0'),
    ('total_api_time', 'DECIMAL(10, 3) NOT NULL DEFAULT 0'),
    ('total_tool_time', 'DECIMAL(10, 3) NOT NULL DEFAULT 0'),
]

# Columns carried over from the 2.15 cost_tracking table. Anything not listed here
# is new in 2.16 and gets its default.
CARRIED = [
    'chat_id', 'msg_no', 'call_id', 'timestamp', 'tokens_in', 'tokens_out',
    'cost_in', 'cost_out', 'estimated_costs', 'elapsed_time', 'model', 'provider',
    'success', 'error_message', 'temperature', 'max_tokens', 'context_length',
    'prompt_semantic_name', 'prompt_version_tracking', 'expected_params',
    'execution_mode', 'parameters', 'environment',
]


def _tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _columns(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]


def migrate(db_path: str, backup: bool = True, log=print) -> bool:
    """Migrate the database at db_path in place. Returns True if anything changed."""
    conn = sqlite3.connect(db_path)
    try:
        tables = _tables(conn)
        needs_cost_rebuild = 'cost_tracking' in tables and 'round_trip' not in _columns(conn, 'cost_tracking')
        needs_chat_cols = 'chats' in tables and any(
            name not in _columns(conn, 'chats') for name, _ in CHATS_COLUMNS)

        if not (needs_cost_rebuild or needs_chat_cols):
            _stamp(conn, log)
            conn.commit()
            return False
    finally:
        conn.close()

    if backup:
        dest = f"{db_path}.bak-{FROM_VERSION}"
        shutil.copy2(db_path, dest)
        log(f"  backed up to {dest}")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN")

        # --- chats: additive columns ------------------------------------------
        if needs_chat_cols:
            existing = set(_columns(conn, 'chats'))
            for name, ddl in CHATS_COLUMNS:
                if name not in existing:
                    conn.execute(f"ALTER TABLE chats ADD COLUMN {name} {ddl}")
            log(f"  chats: added {', '.join(n for n, _ in CHATS_COLUMNS)}")

        # --- cost_tracking: the primary key changes, so the table is rebuilt ---
        if needs_cost_rebuild:
            carried = [c for c in CARRIED if c in _columns(conn, 'cost_tracking')]
            cols = ', '.join(f'"{c}"' for c in carried)
            rows = conn.execute("SELECT count(*) FROM cost_tracking").fetchone()[0]

            conn.execute("ALTER TABLE cost_tracking RENAME TO cost_tracking_legacy")
            # Indexes follow the rename in SQLite and would collide with the new ones.
            for (idx,) in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND tbl_name = 'cost_tracking_legacy' AND sql IS NOT NULL").fetchall():
                conn.execute(f'DROP INDEX IF EXISTS "{idx}"')

            conn.execute(COST_TRACKING_DDL)
            for stmt in COST_TRACKING_INDEXES:
                conn.execute(stmt)
            conn.execute(
                f'INSERT INTO cost_tracking ({cols}, round_trip, tool_time) '
                f'SELECT {cols}, 1, 0 FROM cost_tracking_legacy')
            conn.execute("DROP TABLE cost_tracking_legacy")
            log(f"  cost_tracking: rebuilt, {rows} row(s) carried over as round_trip = 1")

        _stamp(conn, log)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return True


def _stamp(conn, log=print):
    conn.execute(INFO_DDL)
    conn.execute("DELETE FROM info")
    conn.execute("INSERT INTO info (version, updated) VALUES (?, ?)",
                 (TO_VERSION, datetime.now().isoformat(sep=' ', timespec='seconds')))
    log(f"  info.version = {TO_VERSION}")


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('-')]
    if len(args) != 1:
        print(__doc__)
        print(f"usage: {argv[0]} <path/to/chats.db> [--no-backup]")
        return 2

    db_path = args[0]
    print(f"migrating {db_path}: {FROM_VERSION} -> {TO_VERSION}")
    changed = migrate(db_path, backup='--no-backup' not in argv[1:])
    print("done" if changed else "already at 2.16 schema; nothing to do")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
