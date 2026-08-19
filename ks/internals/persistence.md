# Persistence and Migrations

`database.py` defines Peewee models behind a `DatabaseProxy`. SQLite is default; PostgreSQL and MySQL URLs are accepted, but automatic migrations are SQLite-only.

Tables:

- `info`: schema version.
- `chats`: serialized conversation/VM plus aggregate execution metrics.
- `cost_tracking`: one billed request per `(chat_id, msg_no, round_trip)`.

## SQLite migration contract

1. `keprompt --version` defines the schema version expected by the running KePrompt release.
2. On opening SQLite, compare that expected version with `info.version`.
3. If they differ, run:

```bash
python -m keprompt.migrations.migrate_sqlite --version <keprompt-version> [database]
```

4. The runner uses an explicit transition registry and one function per version boundary. The historical standalone entry point remains available for direct recovery:

```text
keprompt/migrations/migrate-ver-2.15-to-2.16.py
```

5. Each migration function upgrades one version boundary. Releases without database changes use explicit no-op transitions so `info.version` still tracks the KePrompt version.
6. Migration succeeds only when `info.version` equals the version expected by KePrompt.

Use the semantic version value, such as `2.16.0`, rather than the display prefix from `keprompt --version`.

The runner resolves the complete path before modifying the database, backs up once, executes and stamps each step transactionally, and refuses unsupported paths or downgrades.

## Schema change procedure

Schema changes require:

1. Update Peewee models and the KePrompt version.
2. Add one transition function and registry entry to `migrate_sqlite.py`; use a no-op function when the release has no schema change.
3. Add or retain a standalone compatibility entry point when direct recovery requires it.
4. Make migration idempotence and existing-data preservation explicit.
5. Test direct execution, chained migration, fresh database creation, and migration from a copied old database.
6. Update `contracts/production-database.md`.

Never infer that a database with historical rows has current metric semantics merely because it was migrated. Migration can reshape old rows but cannot recover usage that was never recorded.