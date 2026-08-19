# KePrompt Implementation Map

```text
shell CLI -> command router -> managers -> VM -> provider / functions -> SQLite
                                      -> JSON or Rich output
```

| Area | Source |
|---|---|
| Entry point and JSON envelope | `keprompt/keprompt.py`, `keprompt/__main__.py` |
| Manager routing | `keprompt/api.py` |
| Chat create/reply/save/restore | `keprompt/chat_manager.py` |
| DSL parser, VM, statements | `keprompt/keprompt_vm.py` |
| Universal messages | `keprompt/AiPrompt.py` |
| Provider request loop | `keprompt/AiProvider.py` |
| Provider adapters | `keprompt/Ai*.py` |
| Model registry and routing | `keprompt/ModelManager.py`, `model_updater.py` |
| Function discovery/execution | `keprompt/keprompt_function_space.py` |
| Persistence and migrations | `keprompt/database.py`, `keprompt/migrations/` |
| Prompt discovery | `keprompt/Prompt.py` |
| Output | `keprompt/output_formatter.py`, `terminal_output.py` |
| Configuration | `keprompt/config.py` |
| Workspace initialization | `keprompt/workspace_manager.py` |
| Tests | `test/` |

## Load-bearing contracts

- Applications call the shell command and consume `--json`.
- Prompt and function paths are workspace-relative.
- Universal messages and VM state must survive chat save/restore.
- Function access is deny-by-default for model calls.
- Costs are recorded per billed round trip; chats hold aggregates.
- Manager responses feed both machine JSON and human formatting.

Read the relevant internal document before changing these paths.