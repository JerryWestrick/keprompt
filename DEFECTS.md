# Discovered defects

Defects found in keprompt, recorded when discovered. Each entry states what was observed and
where in the code it comes from. Fixes are decided separately — an entry here is a finding,
not a plan.

---

## DEFECT-001 — token/cost accounting drops all but the last round trip of a tool loop

- **Status:** fixed 2026-08-18 (see *Fix* below); not yet released
- **Discovered:** 2026-08-08, while deriving a workload profile from `Epicure-prod` for the
  `~/system/inference-hardware` sizing work
- **Found in:** keprompt 2.15.0 (`main` @ f1c8912)
- **Severity:** high — `total_cost` under-reports real spend, by ~2.5× on average and ~17× on
  tool-heavy chats in the Epicure production corpus

### Summary

A single `.exec` statement runs the *entire* tool-calling loop — potentially dozens of HTTP
round trips — inside one call to `vm.prompt.ask()`. When it returns, the VM adds only the
**last** round trip's token usage to the running totals. Every earlier round trip is discarded,
even though it was a separately billed API request.

The correctly accumulated total is already computed and available on the same object.

### Code path

| Location | What happens |
|---|---|
| `keprompt/AiProvider.py:401-402` | each round trip **overwrites** `prompt.last_tokens_in` / `last_tokens_out` with that round trip's usage |
| `keprompt/AiProvider.py:414-415` | each round trip **also accumulates** `prompt.toks_in += tokens_in` — this is the correct per-statement total |
| `keprompt/keprompt_vm.py:1210` | `responses = vm.prompt.ask(...)` runs the whole tool loop and returns a *list* of responses |
| `keprompt/keprompt_vm.py:1226-1227` | reads `vm.prompt.last_tokens_in` / `last_tokens_out` into locals |
| `keprompt/keprompt_vm.py:1232-1233` | `vm.toks_in += tokens_in` — adds only the final round trip |
| `keprompt/keprompt_vm.py:1270-1280` | reuses those same locals to build `cost_data`, so the `cost_tracking` DB row inherits the same undercount |
| `keprompt/chat_manager.py:225` | `total_tokens_in: vm.toks_in` — undercount reaches `chats.total_tokens_in` |

So for a statement making N round trips, N−1 are missing from `vm.toks_in`, `vm.cost_in`,
the `cost_tracking` row, `chats.total_tokens_in/out`, and `total_cost`.

`vm.prompt.toks_in` holds the right number at line 1226.

### Evidence — `~/Epicure-prod/prompts/chats.db`

2,328 production chats, 2026-02-06 → 2026-08-08. Round trips counted structurally as assistant
turns in `messages_json`; recorded tokens read from `chats` / `cost_tracking`.

| chat | assistant turns (real round trips) | `cost_tracking` rows | recorded `tokens_in` | est. tokens actually sent across all round trips |
|---|---|---|---|---|
| `98e86488` | 41 | 1 | 10,023 | ~172,900 |
| `93b7600d` | 41 | 1 | 8,545 | ~154,500 |
| `99593781` | 53 | 26 | 457,538 | ~680,500 |

Corpus-wide: **2,410 `cost_tracking` rows against ~6,100 actual round trips.** Mean round trips
per query 2.63, median 2, p90 5, max 58.

The "est. tokens sent" column is a chars/4 approximation over `messages_json` and is rough; the
17× gap on `98e86488` is far outside that error. `total_api_calls` counts `.exec` statements,
not round trips — it reads 1.04 per chat corpus-wide.

### Not a defect

`keprompt_vm.py:1241-1248` (`context_usage`) legitimately wants `last_tokens_in` — current
context occupancy *is* the last round trip. The problem is that one variable serves two
different quantities: "how full is the context right now" and "what did this statement consume
in total."

### Related observation

The `cost_tracking` row mixes scopes: `elapsed_time` is measured around the whole
`ask()` call (`keprompt_vm.py:1201`, `1211`) so it covers the entire loop, while `tokens_in` /
`tokens_out` on the same row cover one round trip. Any derived rate (tokens/second) from that
row is therefore wrong in both directions at once.

### Historical data

Per-round-trip usage *is* written to `llm.log` by `AiProvider.py:410-411`, but `Epicure-prod`
retains no `llm.log` files — so the six months already on disk cannot be recovered from logs.
`messages_json` holds the full conversation, so historical figures can be reconstructed by
re-tokenizing, approximately.

### Fix

The record was re-cut at the billed unit. `cost_tracking` now holds **one row per API round
trip** rather than one per `.exec`, and every row describes exactly one request.

| Change | Where |
|---|---|
| Providers append a per-round-trip ledger entry (tokens, cost, `response.elapsed`) | `AiProvider.make_api_request` |
| Function execution time is attributed to the round trip that requested it | `AiProvider.call_functions` |
| Ledger is reset per statement | `AiPrompt.ask` |
| `StmtExec` sums the ledger into the VM totals and emits one cost row per round trip | `keprompt_vm.StmtExec._record_round_trips` |
| `cost_tracking` PK is now `(chat_id, msg_no, round_trip)`; added `round_trip`, `tool_time` | `database.CostTracking` |
| `chats` gained `total_round_trips`, `total_api_time`, `total_tool_time` | `database.Chat` |
| Existing databases migrate in place on open; old rows become `round_trip = 1` | `database._migrate_schema` |

Consequences:

- `vm.toks_in/out`, `vm.cost_in/out`, `chats.total_*`, `total_cost` and `<<VM.total_tokens>>`
  now cover every round trip, so the ~2.5× mean / ~17× tool-heavy undercount is gone.
- The scope mismatch is resolved: `elapsed_time` is now that one request's elapsed, alongside
  that one request's tokens, so tokens/second off a row is meaningful. Time spent in functions
  is separated into `tool_time` rather than being folded into the API figure.
- `total_api_calls` still counts `.exec` statements; `total_round_trips` counts billed requests.
- Cost now comes from the provider's own `calculate_costs()` instead of being recomputed in
  `StmtExec` as `tokens × model.input_cost`. Identical arithmetic today (pricing is linear),
  but it removes the second, divergent cost path.
- Round trips completed before a mid-loop API failure are recorded rather than discarded, with
  `success = 0` and the error message.
- `parameters` (a dump of the whole `vdict`, including `last_response`) is written once per
  `.exec` instead of once per round trip, so per-row granularity doesn't multiply the blob.

Verified against a copy of a real 832-row workspace database: row count preserved, all
migrated rows land at `round_trip = 1`, migration is idempotent.

### Still open

- **Cached input is invisible.** `extract_token_usage()` returns a 2-tuple in every provider,
  which cannot represent Anthropic's `cache_creation_input_tokens` / `cache_read_input_tokens`.
  `AiModel.cache_cost` is loaded from the registry (`ModelManager.py:134`) and never read. Cost
  will be overstated on any cached prompt.
- **Historical reconstruction.** The six months already in `Epicure-prod` are unchanged; those
  rows still carry last-round-trip figures. Only approximately recoverable by re-tokenizing
  `messages_json`.
- **`parameters` blob.** Still embeds `last_response` and `model_info` in every `.exec`'s first
  cost row.
