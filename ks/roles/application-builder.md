# Role: Application Builder

Goal: use KePrompt as an external AI runtime behind an application.

## Required reading

1. [`../contracts/application-shell.md`](../contracts/application-shell.md)
2. [`../contracts/json-envelope.md`](../contracts/json-envelope.md)
3. [`../contracts/prompt-language.md`](../contracts/prompt-language.md)
4. [`../contracts/external-functions.md`](../contracts/external-functions.md)

## Architecture

```text
application/channel adapter
  -> keprompt chat create|reply --json
  -> application .prompt
  -> LLM <-> application function executable
  -> JSON answer to application
```

The shell command is the application boundary, not merely an interactive convenience. Keep provider logic and prompting logic out of host code.

## Build workflow

1. Install KePrompt and run `keprompt init` from the application root.
2. Create `prompts/<application>.prompt` for model behavior.
3. Create executable providers in `prompts/functions/` for application capabilities.
4. Invoke `keprompt chat create --json`; pass inputs with `--set`.
5. Check exit status and parse stdout JSON. Treat stderr as diagnostics.
6. Return `ai_response` to the caller and retain `chat_id` when continuation is needed.
7. Continue with `keprompt chat reply --json <chat_id> <message>`.
8. Preserve `prompts/chats.db`; it is production evidence for later optimization.
9. Create an application KS for business intent, architecture, invariants, and the division of responsibility between LLM, tools, and application data.

Keep channel adapters thin. Prefer one prompt/tool core with channel-specific inputs or included instructions over separate behavior paths.