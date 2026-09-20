# TODO

Decided work, not yet done. Findings live in `DEFECTS.md`; an item only moves here once
it is something we intend to change.

---

## Drop the dead `temperature` / `max_tokens` columns from `cost_tracking`

v3.0.0 moved those options into `llm_options` and removed the writes in
`StmtExec._record_round_trips`, but the columns remain in the Peewee model
(`database.CostTracking`) and in every existing database. They are NULL on every row
recorded by 3.0.0 or later, and NULL throughout the reference 832-row workspace.

Documented as dead in `ks/contracts/production-database.md` (commit cd38f06) so nobody
reads them as real settings in the meantime.

To do it:

1. Remove the two fields from `database.CostTracking`.
2. Add a real transition to `MIGRATIONS` in `keprompt/migrations/migrate_sqlite.py` — SQLite
   needs the table rebuilt (`ALTER TABLE ... RENAME`, recreate, copy, drop), the same shape as
   `migrate_2_15_0_to_2_16_0`. Preserve row count and the `(chat_id, msg_no, round_trip)` key.
3. Bump the version; the migration and the version bump ship together.
4. Update the `cost_tracking` section of `ks/contracts/production-database.md` to drop the
   dead-column note.
5. Test against a copy of a real workspace database: row count preserved, migration idempotent,
   chained migration from an older version still lands on the new version.

Not urgent: two NULL columns cost nothing but confusion, and the confusion is now documented.
