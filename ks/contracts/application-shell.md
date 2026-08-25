# Application Shell Contract

Applications normally invoke KePrompt as a subprocess from the application root. Relative workspace paths (`prompts/`, functions, database) are resolved there.

## New request

```bash
keprompt chat create --json --prompt <name> \
  --set-from-json vars.json
```

`<name>` resolves to one `.prompt` file under `prompts/`. `--set-from-json` reads a JSON object of VM variables from `FILE` (path relative to the application root). Those values enter the VM variable dictionary and override prompt defaults. JSON types are kept (strings, numbers, booleans, null, nested objects and arrays).

`--set key value` remains available for a single override. If both are passed, the JSON file is applied first and `--set` wins on matching keys.

## Continue a chat

```bash
keprompt chat reply --json <chat_id> <message>
```

This restores the VM and messages from `prompts/chats.db`, appends the user message and `.exec`, executes, and saves under the same `chat_id`. `--set-from-json` and `--set` may be used on reply as on create.

## Inspect history

```bash
keprompt chat get --json --limit 20
keprompt chat get --json <chat_id>
```

## Minimal Python bridge

```python
import json
import subprocess
from pathlib import Path

def ask(question: str) -> tuple[str, str]:
    vars_path = Path("vars.json")
    vars_path.write_text(json.dumps({"question": question}), encoding="utf-8")
    result = subprocess.run(
        ["keprompt", "chat", "create", "--json", "--prompt", "app",
         "--set-from-json", str(vars_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    data = json.loads(result.stdout[result.stdout.find("{"):])
    return data.get("ai_response", ""), data.get("chat_id", "")
```

Use an argument array, not `shell=True`. Check the return code before trusting stdout. Parse the JSON envelope and preserve `chat_id` if the application supports continuation or audit links.

`--pretty` is for humans. `--json` is the stable machine-facing mode.
