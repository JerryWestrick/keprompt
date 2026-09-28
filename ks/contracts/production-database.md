# Production Database Contract

Default database: `prompts/chats.db` (current KePrompt/database version 4.4.0). It is operational production evidence. Analyze a copy or use read-only SQLite access. Older databases migrate when opened by current KePrompt; inspect `info.version` before assuming columns exist.

## `chats`

One row per persisted chat.

- Identity: `chat_id`, `created_timestamp`.
- Prompt: `prompt_name`, `prompt_version`, `prompt_filename`. From 4.3.0 `prompt_name` is the prompt file's basename; rows written before hold the `.prompt` line's `"name"`, so the same prompt can appear under two names across that boundary.
- Evidence JSON: `messages_json`, `statements_json`, `variables_json`, `vm_state_json`.
- Provenance: `keprompt_version`, `hostname`, `git_commit`.
- Aggregates: `total_api_calls`, `total_round_trips`, `total_tokens_in`, `total_tokens_out`, `total_cost`, `total_api_time`, `total_tool_time`.

`total_api_calls` counts executed `.exec` and `.evaluate` statements. `total_round_trips` counts billed model requests, including requests inside tool loops.

## `cost_tracking`

One row per billed model request — LLM (`.exec`) and LDM (`.evaluate`) alike; an LDM call is one round trip, told apart by `provider`/`model`. Composite key: `(chat_id, msg_no, round_trip)`.

Important fields:

- `model`, `provider`, `timestamp`, `success`, `error_message`.
- `provider_selected_model`: the model that answered — the model asked for, unless the provider identified another (e.g. `gpt-4o` answered by `gpt-4o-2024-08-06`). Null on rows written before 4.3.0.
- `tokens_in`, `tokens_out`, `cost_in`, `cost_out`, `estimated_costs`.
- `elapsed_time`: API response time for this request.
- `tool_time`: execution time of functions requested by this response.
- `prompt_semantic_name`, `prompt_version_tracking`, `parameters`, `expected_params`, `environment`. `prompt_semantic_name` is the same value as `chats.prompt_name`, with the same 4.3.0 change.

Join to `chats` on `chat_id`. `parameters` is normally populated only on the first round trip of an `.exec`.

The table also carries `temperature` and `max_tokens` columns that nothing has written since 3.0.0, when those options moved into `llm_options`. Rows recorded by 3.0.0 or later are always NULL. Earlier rows are NULL too unless the prompt happened to set those options — in the reference 832-row workspace they are NULL throughout. Do not read them as the settings a request ran under; the request options of record are in `parameters`.

## Interpretation

- `statements_json` records what the VM executed.
- `messages_json` records the actual universal conversation, including model replies, tool calls, and tool results. Each LDM call is a message with role `ldm` and one part of type `ldm`: `set`, `questions`, `state`, `model` (asked for), `answers` (null if the call failed), `provider_selected_model`, `usage`. That part plus its `cost_tracking` row is the whole call. Each guard execution is a message with role `guard` and one part of type `guard`: the `ldm` part's fields — `set` names the guard, `state` is the text judged — plus `channel` (`_cmdargs`, `_userinput`, `_include` or the function name), `fail` (the condition) and `failed` (its result). It is never sent to an LLM, and is written whether the guard passed or failed. All guard executions: `SELECT ... FROM chats c, json_each(c.messages_json) m WHERE json_extract(m.value, '$.role') = 'guard'`.
- `variables_json` and `vm_state_json` provide inputs and resumable execution state.
- Aggregate quality cannot be inferred from cost fields. Read the application KS and actual outcomes.
- Production responses are observations, not guaranteed correct labels.
- Cached-input token classes are not represented separately; cached-token cost analysis may be inaccurate.

## Safe starting queries

```sql
SELECT prompt_name, prompt_version, COUNT(*) AS chats,
       SUM(total_cost) AS cost, AVG(total_api_time) AS avg_api_time
FROM chats
GROUP BY prompt_name, prompt_version;

SELECT c.chat_id, c.created_timestamp, c.messages_json, c.variables_json,
       c.total_cost, c.total_api_time, c.total_tool_time
FROM chats c
WHERE c.prompt_name = ?
ORDER BY c.created_timestamp;
```

Do not replay side-effecting production interactions without an application-approved test environment or fixtures.