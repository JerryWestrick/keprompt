# Production Database Contract

Default database: `prompts/chats.db` (current KePrompt/database version 2.16.1). It is operational production evidence. Analyze a copy or use read-only SQLite access. Older databases migrate when opened by current KePrompt; inspect `info.version` before assuming columns exist.

## `chats`

One row per persisted chat.

- Identity: `chat_id`, `created_timestamp`.
- Prompt: `prompt_name`, `prompt_version`, `prompt_filename`.
- Evidence JSON: `messages_json`, `statements_json`, `variables_json`, `vm_state_json`.
- Provenance: `keprompt_version`, `hostname`, `git_commit`.
- Aggregates: `total_api_calls`, `total_round_trips`, `total_tokens_in`, `total_tokens_out`, `total_cost`, `total_api_time`, `total_tool_time`.

`total_api_calls` counts executed `.exec` statements. `total_round_trips` counts billed model requests, including requests inside tool loops.

## `cost_tracking`

One row per billed model request. Composite key: `(chat_id, msg_no, round_trip)`.

Important fields:

- `model`, `provider`, `timestamp`, `success`, `error_message`.
- `tokens_in`, `tokens_out`, `cost_in`, `cost_out`, `estimated_costs`.
- `elapsed_time`: API response time for this request.
- `tool_time`: execution time of functions requested by this response.
- `prompt_semantic_name`, `prompt_version_tracking`, `parameters`, `expected_params`, `environment`.

Join to `chats` on `chat_id`. `parameters` is normally populated only on the first round trip of an `.exec`.

## Interpretation

- `statements_json` records what the VM executed.
- `messages_json` records the actual universal conversation, including model replies, tool calls, and tool results.
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