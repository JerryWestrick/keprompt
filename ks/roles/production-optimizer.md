# Role: Production Optimizer

Goal: improve an existing KePrompt application using its real production evidence, or evaluate replacement models.

This is an LLM-driven engineering workflow using existing KePrompt files, shell commands, SQLite data, and temporary analysis scripts. Do not assume a separate testing product or framework is required.

## Required reading

1. The application's KS and its current prompt/function files.
2. [`../contracts/production-database.md`](../contracts/production-database.md)
3. [`../contracts/application-shell.md`](../contracts/application-shell.md)
4. Prompt/function contracts when changing those artifacts.

## Workflow

1. Work from a copy of production `prompts/chats.db`; do not mutate the supplied evidence.
2. Identify the prompt names, versions, models, time range, intents, failures, costs, and latency relevant to the goal.
3. Extract representative production inputs and outcomes. Include common, difficult, ambiguous, failed, and expensive cases. `messages_json` includes the actual tool calls, arguments, and returned tool results; use them to reconstruct the database facts visible to the model and simulate the production state for replay.
4. Define effectiveness from the application KS and requested goal. The old response is evidence, not automatically truth.
5. Preserve a baseline run or baseline production result.
6. Modify application prompts/functions, or override the model while keeping other inputs fixed.
7. Run baseline and candidate against the same examples through the application's real KePrompt shell path.
8. Judge results consistently. Use deterministic application outcomes where available; use blinded LLM comparison where semantic judgment is required.
9. Report better/worse/unchanged counts, regressions, failures, tokens, cost, API time, and tool time. State sample selection and limitations.
10. Keep only changes supported by the evidence; update the application KS if an architectural decision changed.

Recorded tool results can serve as fixtures, allowing prompt/model tests to reproduce production context without requiring the current database to match its historical state. For side-effecting tools, use recorded results, an application-approved test environment, or controlled fixtures. Never replay production writes blindly.