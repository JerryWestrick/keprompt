# KePrompt LLM Reference

Concise reference for generating keprompt `.prompt` files and custom functions.

## .prompt File Syntax

Line-based DSL. Statements start with `.` prefix. Lines without `.` continue the previous statement. Variable substitution: `<<variable>>`.

### Statements

| Statement | Syntax | Purpose |
|-----------|--------|---------|
| `.prompt` | `.prompt "name":"N", "version":"V", "params":{...}` | **Required first line.** Declares prompt name, version, default params |
| `.system` | `.system <text>` | System message (multi-line) |
| `.user` | `.user <text>` | User message (multi-line) |
| `.assistant` | `.assistant <text>` | Assistant message for few-shot examples |
| `.exec` | `.exec` / `.exec {"model":"..."}` / `.exec modelname` | Execute LLM call. Model override is **permanent** |
| `.functions` | `.functions func1, func2, ...` | Declare which functions the model can use. **No `.functions` = no functions** |
| `.set` | `.set variable value` | Set variable in VM dict |
| `.print` | `.print <text>` | Print to stdout (supports `<<var>>`) |
| `.cmd` | `.cmd func(arg=val)` / `.cmd func(arg=val) as varname` | Call function. Without `as`: appends to message. With `as`: stores in variable only |
| `.include` | `.include <filename>` | Append file contents to current message |
| `.image` | `.image <filename>` | Add image to message (vision models) |
| `.tool_call` | `.tool_call func(arg=val) id=call_id` | Manual assistant tool-call message |
| `.tool_result` | `.tool_result id=call_id name=func` | Manual tool result message (multi-line body) |
| `.text` | `.text <text>` | Continue current message explicitly |
| `.debug` | `.debug ["all"]` | Show VM state |
| `.clear` | `.clear ["*.tmp"]` | Delete files by glob |
| `.exit` | `.exit` | Terminate execution |
| `.#` | `.# comment` | Comment (ignored) |

### Auto-completion

If the file doesn't end with `.exit`, the VM appends missing steps:
- Ends with `.exec` → adds `.print <<last_response>>` + `.exit`
- Ends with anything else → adds `.exec` + `.print <<last_response>>` + `.exit`

### Variables

- **Set**: `.set name value` or via `.prompt` params or CLI `--set name value`
- **Use**: `<<name>>` anywhere in text
- **Dict access**: `<<dict.key>>`
- **VM properties** (read-only): `<<VM.chat_id>>`, `<<VM.model_name>>`, `<<VM.provider>>`, `<<VM.total_cost>>`, `<<VM.toks_in>>`, `<<VM.toks_out>>`, `<<VM.interaction_no>>`
- **Special**: `<<last_response>>` — last LLM or .cmd output

### Model Names

Format: `provider/model-name`. Providers: `openai`, `anthropic`, `gemini`, `deepseek`, `mistral`, `xai`, `cerebras`, `openrouter`.

Examples: `openai/gpt-4o`, `anthropic/claude-sonnet-4-20250514`, `gemini/gemini-2.0-flash`, `deepseek-chat`, `mistral/mistral-large-latest`, `xai/grok-2`, `cerebras/llama-3.3-70b`

## Built-in Functions

Available in `.cmd` and as LLM tool calls:

| Function | Signature | Description |
|----------|-----------|-------------|
| `readfile` | `readfile(filename, offset=None, length=None)` | Read file (optional byte range) |
| `writefile` | `writefile(filename, content)` | Write file (auto-backup if exists) |
| `write_base64_file` | `write_base64_file(filename, base64_str)` | Write binary file from base64 |
| `execcmd` | `execcmd(cmd)` | Execute shell command |
| `wwwget` | `wwwget(url)` | Fetch URL as text |

## Custom Functions

Place executable files in `prompts/functions/`. Any language. Must support:

### Discovery Protocol
```bash
./your_function --list-functions   # Return JSON array of OpenAI function schemas
./your_function --version          # Return version string
```

### Execution Protocol
```bash
echo '{"arg1":"val1"}' | ./your_function function_name
# stdout = result string, stderr = errors, exit 0 = success
```

### Function Schema (OpenAI format)
```json
[{
  "name": "my_function",
  "description": "What it does",
  "parameters": {
    "type": "object",
    "properties": {
      "arg1": {"type": "string", "description": "..."}
    },
    "required": ["arg1"]
  }
}]
```

### Python Template
```python
#!/usr/bin/env python3
import json, sys

def my_function(arg1: str) -> str:
    return f"Result: {arg1}"

FUNCTIONS = {"my_function": my_function}
DEFINITIONS = [{
    "name": "my_function",
    "description": "Does something useful",
    "parameters": {
        "type": "object",
        "properties": {"arg1": {"type": "string", "description": "Input"}},
        "required": ["arg1"]
    }
}]

if __name__ == "__main__":
    if "--list-functions" in sys.argv:
        print(json.dumps(DEFINITIONS))
    elif "--version" in sys.argv:
        print("1.0.0")
    elif len(sys.argv) > 1:
        args = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
        print(FUNCTIONS[sys.argv[1]](**args))
```

**Working directory**: `--list-functions` runs from `prompts/functions/`; actual execution runs from project root.

**Timeouts**: Discovery = 10s, execution = 30s.

## Patterns

### Basic prompt
```
.prompt "name":"Greet", "version":"1.0", "params":{"model":"openai/gpt-4o"}
.system You are a helpful assistant.
.user Hello, <<name>>!
```

### Multi-turn
```
.prompt "name":"Research", "version":"1.0", "params":{"model":"anthropic/claude-sonnet-4-20250514"}
.user Summarize this topic: <<topic>>
.exec
.user Now give me 3 key takeaways from your summary.
```

### File analysis
```
.prompt "name":"Analyze", "version":"1.0", "params":{"model":"openai/gpt-4o"}
.system You are a code reviewer.
.user Review this file:
.cmd readfile(filename="<<filepath>>")
```

### Multi-model comparison
```
.prompt "name":"Compare", "version":"1.0", "params":{"model":"openai/gpt-4o"}
.user <<question>>
.exec
.set gpt4_answer <<last_response>>
.exec anthropic/claude-sonnet-4-20250514
.set claude_answer <<last_response>>
.user Compare these answers:
GPT-4o: <<gpt4_answer>>
Claude: <<claude_answer>>
Which is better and why?
```

### Few-shot with tool calls
```
.prompt "name":"FileHelper", "version":"1.0", "params":{"model":"openai/gpt-4o"}
.system You help users with files. Use readfile to read files when asked.
.user What's in config.json?
.tool_call readfile(filename="config.json") id=ex1
.tool_result id=ex1 name=readfile
{"key": "value", "debug": false}
.assistant The config.json contains a JSON object with two keys: "key" set to "value" and "debug" set to false.
.user Now read <<target_file>>
```

### Variable-driven template
```
.prompt "name":"Email", "version":"1.0", "params":{"model":"openai/gpt-4o", "tone":"professional", "language":"English"}
.system Write emails in <<language>> with a <<tone>> tone.
.user Write an email to <<recipient>> about <<subject>>.
```

## CLI Usage

```bash
# Run a prompt
keprompt chat new --prompt myfile.prompt --set name "World" --set model "openai/gpt-4o"

# Continue a conversation
keprompt chat reply --chat-id abc12345 --answer "follow up question"

# List models/prompts
keprompt models get --name gpt
keprompt prompt get
```
