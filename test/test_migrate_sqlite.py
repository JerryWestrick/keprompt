"""Schema migrations, driven through the migration script's own command line.

`python -m keprompt.migrations.migrate_sqlite <db> --version X` is how a migration is actually
run, so that is what these tests invoke. Assertions look only at the database file afterwards --
the durable result a user is left with.
"""

import sqlite3
import subprocess
import sys

import pytest

LEGACY_SCHEMA = """
    CREATE TABLE chats (
        chat_id TEXT PRIMARY KEY,
        messages_json TEXT NOT NULL
    );
    CREATE TABLE cost_tracking (
        chat_id TEXT NOT NULL, msg_no INTEGER NOT NULL,
        call_id TEXT NOT NULL, timestamp TEXT NOT NULL,
        tokens_in INTEGER NOT NULL, tokens_out INTEGER NOT NULL,
        cost_in NUMERIC NOT NULL, cost_out NUMERIC NOT NULL,
        estimated_costs NUMERIC NOT NULL, elapsed_time NUMERIC NOT NULL,
        model TEXT NOT NULL, provider TEXT NOT NULL, success INTEGER NOT NULL,
        error_message TEXT, temperature NUMERIC, max_tokens INTEGER,
        context_length INTEGER, prompt_semantic_name TEXT,
        prompt_version_tracking TEXT, expected_params TEXT,
        execution_mode TEXT NOT NULL, parameters TEXT, environment TEXT,
        PRIMARY KEY (chat_id, msg_no)
    );
    CREATE TABLE server_registry (id INTEGER PRIMARY KEY);
    INSERT INTO chats VALUES ('abc12345', '[]');
    INSERT INTO cost_tracking VALUES (
        'abc12345', 7, 'call-1', '2026-01-01', 10, 5,
        0.1, 0.2, 0.3, 1.5, 'model', 'provider', 1,
        NULL, NULL, NULL, NULL, 'prompt', '1.0', NULL,
        'production', NULL, 'test'
    );
"""


def build(path, script: str):
    conn = sqlite3.connect(path)
    conn.executescript(script)
    conn.commit()
    conn.close()
    return path


def stamped(path, version: str):
    return build(path, f"""
        CREATE TABLE info (id INTEGER PRIMARY KEY, version TEXT, updated TEXT);
        INSERT INTO info (version, updated) VALUES ('{version}', 'now');
    """)


def migrate(path, version: str, expect_ok: bool = True):
    """Run the migration the way an operator does."""
    result = subprocess.run(
        [sys.executable, "-m", "keprompt.migrations.migrate_sqlite",
         str(path), "--version", version, "--no-backup"],
        capture_output=True, text=True, timeout=120,
    )
    if expect_ok:
        assert result.returncode == 0, f"migration failed:\n{result.stdout}\n{result.stderr}"
    return result


def query(path, sql: str):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def version_of(path) -> str:
    return query(path, "SELECT version FROM info")[0][0]


def tables(path) -> set:
    return {r[0] for r in query(path, "SELECT name FROM sqlite_master WHERE type='table'")}


# --- the 2.15 -> 2.16 rebuild ----------------------------------------------------------------

def test_legacy_database_migrates_and_preserves_rows(tmp_path):
    path = build(tmp_path / "chats.db", LEGACY_SCHEMA)
    migrate(path, "2.16.0")

    assert version_of(path) == "2.16.0"
    assert "server_registry" not in tables(path)
    columns = {r[1] for r in query(path, "PRAGMA table_info(chats)")}
    assert {"total_round_trips", "total_api_time", "total_tool_time"} <= columns

    row = query(path, "SELECT chat_id, msg_no, round_trip, tool_time, tokens_in FROM cost_tracking")
    assert row == [("abc12345", 7, 1, 0, 10)], "existing cost rows must carry over as round_trip 1"


def test_migrating_twice_changes_nothing(tmp_path):
    path = build(tmp_path / "chats.db", LEGACY_SCHEMA)
    migrate(path, "2.16.0")
    before = query(path, "SELECT * FROM cost_tracking")
    migrate(path, "2.16.0")
    assert query(path, "SELECT * FROM cost_tracking") == before


def test_already_current_database_is_left_alone(tmp_path):
    path = stamped(tmp_path / "chats.db", "2.16.0")
    migrate(path, "2.16.0")
    assert version_of(path) == "2.16.0"


def test_two_part_version_is_normalized(tmp_path):
    path = stamped(tmp_path / "chats.db", "2.16")
    migrate(path, "2.16.0")
    assert version_of(path) == "2.16.0"


# --- the release chain -------------------------------------------------------------------------

@pytest.mark.parametrize("target", ["2.16.1", "2.16.2", "3.0.0", "3.0.1", "3.1.0", "4.0.0"])
def test_each_release_step_stamps_its_version(tmp_path, target):
    path = stamped(tmp_path / "chats.db", "2.16.0")
    migrate(path, target)
    assert version_of(path) == target


def test_full_chain_from_legacy_to_current(tmp_path):
    path = build(tmp_path / "chats.db", LEGACY_SCHEMA)
    migrate(path, "4.1.0")
    assert version_of(path) == "4.1.0"
    assert query(path, "SELECT count(*) FROM chats") == [(1,)]
    assert query(path, "SELECT count(*) FROM cost_tracking") == [(1,)]


# --- 4.1.0 and 4.2.0: no separate LDM table ---------------------------------------------------

def test_no_ldm_table_is_created(tmp_path):
    """An LDM call is an execute: billed in cost_tracking, content in messages_json."""
    path = build(tmp_path / "chats.db", LEGACY_SCHEMA)
    migrate(path, "4.2.0")
    assert version_of(path) == "4.2.0"
    assert not {t for t in tables(path) if "ldm" in t or "system_one" in t}
    assert query(path, "SELECT count(*) FROM cost_tracking") == [(1,)]


# --- refusals ------------------------------------------------------------------------------

def test_downgrade_is_refused(tmp_path):
    """A newer database must not be silently rewritten by an older keprompt."""
    path = stamped(tmp_path / "chats.db", "4.1.0")
    result = migrate(path, "3.0.1", expect_ok=False)
    assert result.returncode != 0
    # Either refusal is correct: no path backwards, or the only step available overshoots.
    detail = result.stdout + result.stderr
    assert "no migration path" in detail or "overshoots" in detail, detail
    assert version_of(path) == "4.1.0", "a refused migration must not change the database"
