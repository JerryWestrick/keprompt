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

---

## Cached input tokens: invisible in cost, unreachable as a feature

Two separable problems that share one cause — nothing in KePrompt knows cached tokens exist.
Grep confirms no `cache_control`, `cached_tokens`, or `cache_creation` anywhere in the package.
Recorded as still-open under DEFECT-001 in `DEFECTS.md`.

**Approach is undecided.** The notes below are the established facts, not a chosen design.

### 1. Cost is overstated where providers cache automatically

OpenAI and DeepSeek cache server-side without being asked and return the cached counts
(`prompt_tokens_details.cached_tokens`, `prompt_cache_hit_tokens`). All eight adapters drop them:
`extract_token_usage()` returns a bare `(tokens_in, tokens_out)` 2-tuple
(`AiProvider.py:70` and each adapter). Cost is then computed as `tokens_in x input_cost`, so a
discounted cache hit is billed at full rate in our records.

`AiModel.cache_cost` is already loaded from the registry's `cache_read_input_token_cost`
(`ModelManager.py:153`) and read nowhere.

Touches: the `extract_token_usage` contract across all eight adapters, `calculate_costs`, the
round-trip ledger in `AiProvider.make_api_request`, and `cost_tracking` — new columns mean a
version bump plus a transition, per `ks/internals/persistence.md`.

### 2. Anthropic caching cannot be turned on at all

Anthropic requires `cache_control` inside message content blocks. `llm_options` merges only into
the top level of the request dict (`AiProvider.py:182`), so it cannot place anything inside
`messages`. Verified: setting `cache_control` via `llm_options` lands it as a sibling of `model`
and `messages`, where the API does not read it.

Deciding this is deciding how far the `.prompt` language should reach into provider-specific
request shape — i.e. whether cache placement is an assembler-tier concern at all.

### Also

`ks/internals/providers-and-models.md` and `ks/contracts/production-database.md` both carry a
known-limitation line about cache token classes. Update them with whatever gets built.

---

## `.question` — System One calls from a prompt

Designed 2026-09-20, not built. Full design in [`design/question.md`](design/question.md).

Adds a non-message statement that sends state plus named typed questions to a System One model
(TypeSafe's Jev) and lands the answers in a variable, so a prompt can classify intent cheaply and
then load only what the classification selected — `.include <<intent.action.value>>-<<intent.object.value>>.md`.
Motivated by Epicure: thirty similar routines in one context degrade gpt-oss-120b's selection.

Dispatch works without control flow, so this is not blocked on conditionals.

Two things must change before it can work, both covered in the design doc:

1. **Parser.** `.question` needs adding to the continuation list at `keprompt_vm.py:461`, or its
   indented body becomes standalone `.text` statements and gets sent to the LLM as message content.
2. **Model registry.** `_load_all_models()` reads only the LiteLLM dump, which `models update`
   overwrites and which will never carry TypeSafe. Needs a local overlay applied after update, plus
   an `AiTypeSafe` handler declaring `litellm_provider` or the entry is filtered out. Not
   TypeSafe-specific — any provider outside LiteLLM hits this.

The design doc also records two adjacent designs settled in the same session and not yet written up
properly: the prompt-injection guard (`safe=` / `[safe]`, checked at acquisition in `FunctionSpace`)
and conditionals (`.then`/`.else`/`.end-if`, forward jumps only).
