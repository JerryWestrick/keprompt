# Application Shell Contract

Applications normally invoke KePrompt as a subprocess from the application root. Relative workspace paths (`prompts/`, functions, database) are resolved there.

## New request

```bash
keprompt chat create --json --prompt <name> \
  --set key value \
  --set other=value
```

`<name>` resolves to one `.prompt` file under `prompts/`. `--set` values enter the VM variable dictionary and override prompt defaults.

## Continue a chat

```bash
keprompt chat reply --json <chat_id> <message>
```

This restores the VM and messages from `prompts/chats.db`, appends the user message and `.exec`, executes, and saves under the same `chat_id`.

## Inspect history

```bash
keprompt chat get --json --limit 20
keprompt chat get --json <chat_id>
```

## Minimal Python bridge

```python
import json
import subprocess

def ask(question: str) -> tuple[str, str]:
    result = subprocess.run(
        ["keprompt", "chat", "create", "--json", "--prompt", "app",
         "--set", "question", question],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    data = json.loads(result.stdout[result.stdout.find("{"):])
    return data.get("ai_response", ""), data.get("chat_id", "")
```

Use an argument array, not `shell=True`. Check the return code before trusting stdout. Parse the JSON envelope and preserve `chat_id` if the application supports continuation or audit links.

`--pretty` is for humans. `--json` is the stable machine-facing mode.