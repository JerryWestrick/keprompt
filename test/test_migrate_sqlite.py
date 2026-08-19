import sqlite3

import pytest

from keprompt.migrations import migrate_sqlite


def _legacy_database(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
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
    """)
    conn.commit()
    conn.close()


def test_migrates_legacy_database_and_preserves_rows(tmp_path):
    path = tmp_path / "chats.db"
    _legacy_database(path)

    assert migrate_sqlite.migrate(path, "2.16.0", backup=False, log=lambda _: None)

    conn = sqlite3.connect(path)
    assert conn.execute("SELECT version FROM info").fetchone()[0] == "2.16.0"
    assert "server_registry" not in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"total_round_trips", "total_api_time", "total_tool_time"} <= {
        row[1] for row in conn.execute("PRAGMA table_info(chats)")
    }
    row = conn.execute(
        "SELECT chat_id, msg_no, round_trip, tool_time, tokens_in "
        "FROM cost_tracking"
    ).fetchone()
    assert row == ("abc12345", 7, 1, 0, 10)
    conn.close()


def test_current_database_is_noop(tmp_path):
    path = tmp_path / "chats.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE info (id INTEGER PRIMARY KEY, version TEXT, updated TEXT);
        INSERT INTO info (version, updated) VALUES ('2.16.0', 'now');
    """)
    conn.commit()
    conn.close()

    assert not migrate_sqlite.migrate(path, "2.16.0", backup=False)


def test_legacy_two_part_version_is_normalized(tmp_path):
    path = tmp_path / "chats.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE info (id INTEGER PRIMARY KEY, version TEXT, updated TEXT);
        INSERT INTO info (version, updated) VALUES ('2.16', 'now');
    """)
    conn.commit()
    conn.close()

    assert migrate_sqlite.migrate(path, "2.16.0", backup=False)
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT version FROM info").fetchone()[0] == "2.16.0"
    conn.close()


def test_unsupported_path_fails_before_backup(tmp_path):
    path = tmp_path / "chats.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE info (id INTEGER PRIMARY KEY, version TEXT, updated TEXT);
        INSERT INTO info (version, updated) VALUES ('2.14.0', 'now');
    """)
    conn.commit()
    conn.close()

    with pytest.raises(migrate_sqlite.MigrationError, match="no migration path"):
        migrate_sqlite.migrate(path, "2.16.0", backup=True)
    assert not list(tmp_path.glob("*.bak-*"))


def test_backup_is_created_once_before_migration(tmp_path):
    path = tmp_path / "chats.db"
    _legacy_database(path)

    migrate_sqlite.migrate(path, "2.16.0", backup=True, log=lambda _: None)

    assert (tmp_path / "chats.db.bak-2.15.0").exists()


def test_database_initialization_runs_migration(tmp_path):
    from keprompt import database

    path = tmp_path / "chats.db"
    _legacy_database(path)
    db = database.initialize_database(f"sqlite:///{path}")
    db.close()

    conn = sqlite3.connect(path)
    assert conn.execute("SELECT version FROM info").fetchone()[0] == "2.16.1"
    assert "round_trip" in {
        row[1] for row in conn.execute("PRAGMA table_info(cost_tracking)")
    }
    conn.close()


def test_noop_release_transition_stamps_new_version(tmp_path):
    path = tmp_path / "chats.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE info (id INTEGER PRIMARY KEY, version TEXT, updated TEXT);
        INSERT INTO info (version, updated) VALUES ('2.16.0', 'now');
    """)
    conn.commit()
    conn.close()

    assert migrate_sqlite.migrate(path, "2.16.1", backup=False)
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT version FROM info").fetchone()[0] == "2.16.1"
    conn.close()